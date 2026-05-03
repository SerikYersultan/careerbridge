from typing import Any, Dict, List

from sqlalchemy.orm import Session

from app import models


def _normalize_skill_name(name: str) -> str:
    return name.strip().lower()


async def persist_vacancies(vacancies: List[Dict[str, Any]], db: Session) -> Dict[str, int]:
    """Persist normalized vacancies and skill links into PostgreSQL."""
    report: Dict[str, int] = {
        "jobs_inserted": 0,
        "skills_created": 0,
        "links_created": 0,
        "errors": 0,
        "spacy_hits": 0,
        "gemini_fallbacks": 0,
    }

    for vacancy in vacancies:
        try:
            source_url = vacancy.get("source_url")
            job = None
            if source_url:
                job = db.query(models.Job).filter(models.Job.source_url == source_url).first()

            is_new_job = job is None
            if is_new_job:
                job = models.Job(
                    title=vacancy.get("title") or "Untitled vacancy",
                    company=vacancy.get("company") or "Unknown company",
                    location=vacancy.get("location"),
                    seniority=vacancy.get("seniority"),
                    description=vacancy.get("description"),
                    salary_min=vacancy.get("salary_min"),
                    salary_max=vacancy.get("salary_max"),
                    currency=vacancy.get("currency") or "KZT",
                    source_url=source_url,
                )
                db.add(job)
                db.flush()
                report["jobs_inserted"] += 1
            else:
                job.title = vacancy.get("title") or job.title
                job.company = vacancy.get("company") or job.company
                job.location = vacancy.get("location")
                job.seniority = vacancy.get("seniority")
                job.description = vacancy.get("description")
                job.salary_min = vacancy.get("salary_min")
                job.salary_max = vacancy.get("salary_max")
                job.currency = vacancy.get("currency") or job.currency
                db.flush()

            extracted_skills = vacancy.get("skills") or []
            extraction_source = vacancy.get("extraction_source")
            if extraction_source == "spacy":
                report["spacy_hits"] += 1
            elif extraction_source == "gemini":
                report["gemini_fallbacks"] += 1
            existing_link_rows = (
                db.query(models.JobSkill.skill_id)
                .filter(models.JobSkill.job_id == job.id)
                .all()
            )
            existing_skill_ids = {row[0] for row in existing_link_rows}

            for item in extracted_skills:
                display_name = (item.get("display_name") or "").strip()
                if not display_name:
                    continue
                normalized_name = _normalize_skill_name(display_name)
                category = item.get("category", "other")

                skill = db.query(models.Skill).filter(models.Skill.name == normalized_name).first()
                if skill is None:
                    skill = models.Skill(
                        name=normalized_name,
                        display_name=display_name,
                        category=category,
                    )
                    db.add(skill)
                    db.flush()
                    report["skills_created"] += 1
                elif not skill.category and category:
                    skill.category = category

                if skill.id not in existing_skill_ids:
                    db.add(
                        models.JobSkill(
                            job_id=job.id,
                            skill_id=skill.id,
                            weight=1.0,
                        )
                    )
                    existing_skill_ids.add(skill.id)
                    report["links_created"] += 1

            db.commit()
        except Exception:
            db.rollback()
            report["errors"] += 1

    return report
