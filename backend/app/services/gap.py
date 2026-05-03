from collections import Counter
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from app import models


CATEGORY_WEIGHT = {
    "language": 1.0,
    "framework": 0.9,
    "database": 0.8,
    "tool": 0.6,
    "cloud": 0.7,
    "soft": 0.3,
    "other": 0.4,
}


def _normalize(name: str) -> str:
    return name.strip().lower()


def compute_gap(
    db: Session,
    user_skills: List[str],
    target_role: str,
    top_n_jobs: int = 50,
) -> Dict[str, Any]:
    """Compute market skill coverage and return have/missing skill sets."""
    user_set = {_normalize(s) for s in user_skills}

    q = (
        db.query(models.Job)
        .filter(models.Job.title.ilike(f"%{target_role}%"))
        .order_by(models.Job.created_at.desc())
        .limit(top_n_jobs)
    )
    jobs = q.all()
    if not jobs:
        return {
            "target_role": target_role,
            "jobs_analyzed": 0,
            "have": [],
            "missing": [],
            "market_top": [],
        }

    counter: Counter = Counter()
    skill_meta: Dict[str, str] = {}

    for job in jobs:
        for js in job.skill_links:
            name = _normalize(js.skill.name)
            counter[name] += 1
            skill_meta[name] = js.skill.category or "other"

    n = len(jobs)
    threshold = max(1, int(n * 0.2))

    market = [
        {
            "name": name,
            "category": skill_meta[name],
            "frequency": cnt,
            "coverage": round(cnt / n, 2),
            "weight": round(
                (cnt / n) * CATEGORY_WEIGHT.get(skill_meta[name], 0.4), 3
            ),
        }
        for name, cnt in counter.items()
        if cnt >= threshold
    ]
    market.sort(key=lambda x: x["weight"], reverse=True)

    have = [m for m in market if m["name"] in user_set]
    missing = [m for m in market if m["name"] not in user_set]

    return {
        "target_role": target_role,
        "jobs_analyzed": n,
        "have": have,
        "missing": missing,
        "market_top": market[:15],
    }
