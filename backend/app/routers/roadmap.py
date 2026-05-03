from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app import models
from app.database import get_db
from app.auth import get_current_user
from app.services.gap import compute_gap
from app.services.roadmap import generate_roadmap_async
from app.schemas.roadmap import GapResponse, RoadmapResponse

router = APIRouter(prefix="/roadmap", tags=["roadmap"])


def _user_skill_names(db: Session, user_id: int) -> list[str]:
    rows = (
        db.query(models.Skill.name)
        .join(models.UserSkill, models.UserSkill.skill_id == models.Skill.id)
        .filter(models.UserSkill.user_id == user_id)
        .all()
    )
    return [r[0] for r in rows]


@router.get("/gap", response_model=GapResponse)
def get_gap(
    target_role: str = Query(..., min_length=2),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    user_skills = _user_skill_names(db, current_user.id)
    return compute_gap(db, user_skills, target_role)


@router.post("/generate", response_model=RoadmapResponse)
async def post_generate_roadmap(
    target_role: str = Query(..., min_length=2),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    user_skills = _user_skill_names(db, current_user.id)
    gap = compute_gap(db, user_skills, target_role)
    if gap["jobs_analyzed"] == 0:
        raise HTTPException(404, f"No jobs found for role '{target_role}'")

    try:
        roadmap = await generate_roadmap_async(
            target_role=target_role,
            have_skills=[h["name"] for h in gap["have"]],
            missing_skills=gap["missing"],
        )
    except Exception as e:
        raise HTTPException(502, str(e))

    rec = models.Roadmap(
        user_id=current_user.id,
        target_role=target_role,
        data=roadmap,
    )
    db.add(rec)
    db.commit()

    return RoadmapResponse(
        target_role=target_role,
        nodes=roadmap.get("nodes", []),
        edges=roadmap.get("edges", []),
    )


@router.get("/last", response_model=RoadmapResponse | None)
def get_last_roadmap(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    rec = (
        db.query(models.Roadmap)
        .filter(models.Roadmap.user_id == current_user.id)
        .order_by(models.Roadmap.created_at.desc())
        .first()
    )
    if not rec:
        return None
    return RoadmapResponse(
        target_role=rec.target_role,
        nodes=rec.data.get("nodes", []),
        edges=rec.data.get("edges", []),
    )
