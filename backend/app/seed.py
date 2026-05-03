import json
from pathlib import Path
from sqlalchemy.orm import Session

from .database import Base, engine, SessionLocal
from .models import Skill, Job, JobSkill


SEED_FILE = Path(__file__).parent / "seed_data.json"


def _normalize(name: str) -> str:
    return name.strip().lower()


def get_or_create_skill(db: Session, raw_name: str) -> Skill:
    norm = _normalize(raw_name)
    skill = db.query(Skill).filter(Skill.name == norm).first()
    if skill:
        return skill
    skill = Skill(name=norm, display_name=raw_name.strip())
    db.add(skill)
    db.flush()
    return skill


def seed_jobs(db: Session) -> int:
    if db.query(Job).count() > 0:
        return 0

    with SEED_FILE.open("r", encoding="utf-8") as f:
        payload = json.load(f)

    inserted = 0
    for item in payload:
        job = Job(
            title=item["title"],
            company=item["company"],
            location=item.get("location"),
            seniority=item.get("seniority"),
            description=item.get("description"),
            salary_min=item.get("salary_min"),
            salary_max=item.get("salary_max"),
            currency=item.get("currency", "KZT"),
            source_url=item.get("source_url"),
        )
        db.add(job)
        db.flush()

        for raw_skill in item.get("skills", []):
            skill = get_or_create_skill(db, raw_skill)
            db.add(JobSkill(job_id=job.id, skill_id=skill.id))

        inserted += 1

    db.commit()
    return inserted


def init_db_and_seed() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        count = seed_jobs(db)
        print(f"[seed] Inserted {count} jobs")
    finally:
        db.close()


if __name__ == "__main__":
    init_db_and_seed()
