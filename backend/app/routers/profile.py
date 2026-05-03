from typing import List
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import User, Skill, UserSkill
from ..schemas import ResumeExtractResponse, ExtractedSkill, SkillsSaveRequest, SkillOut
from ..auth import get_current_user
from ..services.pdf import extract_text_from_pdf, PDFExtractionError
from ..services.ai import AIServiceError
from ..services.hybrid_nlp import extract_skills_hybrid

router = APIRouter(prefix="/profile", tags=["profile"])

MAX_PDF_BYTES = 10 * 1024 * 1024


@router.post("/upload-resume", response_model=ResumeExtractResponse)
async def upload_resume(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    if file.content_type not in ("application/pdf", "application/x-pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted")

    raw = await file.read()
    if len(raw) > MAX_PDF_BYTES:
        raise HTTPException(status_code=413, detail="PDF too large (max 10 MB)")

    try:
        text = extract_text_from_pdf(raw)
    except PDFExtractionError as e:
        raise HTTPException(status_code=422, detail=str(e))

    try:
        extraction = await extract_skills_hybrid(text)
        skills = extraction["skills"]
    except AIServiceError as e:
        raise HTTPException(status_code=502, detail=str(e))

    current.resume_text = text
    db.commit()

    return ResumeExtractResponse(
        resume_text_preview=text[:500],
        skills=[ExtractedSkill(**s) for s in skills],
    )


def _get_or_create_skill(db: Session, display_name: str, category: str | None) -> Skill:
    norm = display_name.strip().lower()
    skill = db.query(Skill).filter(Skill.name == norm).first()
    if skill:
        return skill
    skill = Skill(name=norm, display_name=display_name.strip(), category=category)
    db.add(skill)
    db.flush()
    return skill


@router.post("/skills", response_model=List[SkillOut])
def save_skills(
    payload: SkillsSaveRequest,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    db.query(UserSkill).filter(UserSkill.user_id == current.id).delete()

    saved: list[Skill] = []
    seen_norm: set[str] = set()
    for item in payload.skills:
        norm = item.display_name.strip().lower()
        if not norm or norm in seen_norm:
            continue
        seen_norm.add(norm)
        skill = _get_or_create_skill(db, item.display_name, item.category)
        db.add(UserSkill(user_id=current.id, skill_id=skill.id, source="manual", confirmed=True))
        saved.append(skill)
    db.commit()
    return saved


@router.get("/skills", response_model=List[SkillOut])
def list_skills(
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    rows = (
        db.query(Skill)
        .join(UserSkill, UserSkill.skill_id == Skill.id)
        .filter(UserSkill.user_id == current.id)
        .all()
    )
    return rows
