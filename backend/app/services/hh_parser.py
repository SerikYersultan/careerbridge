import asyncio
import logging
from collections.abc import Iterable
from typing import Any, Dict, List, Optional, Sequence

import httpx

from app.database import SessionLocal
from app.services.hybrid_nlp import extract_skills_hybrid
from app.services.shared_ingestion import persist_vacancies

HH_VACANCIES_URL = "https://api.hh.ru/vacancies"
KAZAKHSTAN_AREA_ID = 40
DEFAULT_IT_ROLES: tuple[str, ...] = (
    "Backend Developer",
    "Python Developer",
    "Data Analyst",
    "Data Scientist",
    "DevOps Engineer",
    "QA Engineer",
)
DEFAULT_PER_PAGE = 50
DEFAULT_PAGES_PER_ROLE = 2
DEFAULT_RATE_LIMIT_RPS = 3.0
DEFAULT_TIMEOUT_SECONDS = 20.0
DEFAULT_MAX_RETRIES = 3

def _coalesce_text(*parts: Optional[str]) -> str:
    values = [p.strip() for p in parts if p and p.strip()]
    return "\n\n".join(values)


def _extract_seniority(vacancy: Dict[str, Any]) -> Optional[str]:
    experience = vacancy.get("experience") or {}
    exp_name = (experience.get("name") or "").lower()
    title = (vacancy.get("name") or "").lower()
    text = f"{exp_name} {title}"

    if "junior" in text or "стажер" in text or "intern" in text:
        return "junior"
    if "middle" in text or "mid" in text:
        return "middle"
    if "senior" in text or "lead" in text:
        return "senior"
    return None


def normalize_hh_vacancy(vacancy: Dict[str, Any]) -> Dict[str, Any]:
    """Map an HH vacancy payload to the internal ingestion format."""
    employer = vacancy.get("employer") or {}
    area = vacancy.get("area") or {}
    salary = vacancy.get("salary") or {}
    snippet = vacancy.get("snippet") or {}

    return {
        "hh_id": str(vacancy.get("id") or ""),
        "title": (vacancy.get("name") or "").strip(),
        "company": (employer.get("name") or "").strip(),
        "location": (area.get("name") or "").strip() or None,
        "seniority": _extract_seniority(vacancy),
        "description": _coalesce_text(
            vacancy.get("description"),
            snippet.get("requirement"),
            snippet.get("responsibility"),
        ),
        "salary_min": salary.get("from"),
        "salary_max": salary.get("to"),
        "currency": salary.get("currency") or "KZT",
        "source_url": vacancy.get("alternate_url"),
        "source": "hh.kz",
        "raw": vacancy,
    }


def _dedup_batch(vacancies: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    unique: List[Dict[str, Any]] = []
    seen: set[str] = set()

    for item in vacancies:
        source_url = (item.get("source_url") or "").strip()
        hh_id = (item.get("hh_id") or "").strip()
        dedup_key = source_url or f"hh:{hh_id}"
        if not dedup_key:
            # Fallback for malformed records without stable IDs.
            title = (item.get("title") or "").strip().lower()
            company = (item.get("company") or "").strip().lower()
            dedup_key = f"title:{title}|company:{company}"
        if dedup_key in seen:
            continue
        seen.add(dedup_key)
        unique.append(item)

    return unique


async def extract_skills_from_job_description(
    title: str,
    description: str,
) -> Dict[str, Any]:
    merged_text = f"{title.strip()}\n\n{(description or '').strip()}".strip()
    if not merged_text:
        return {"skills": [], "extraction_source": "spacy"}
    return await extract_skills_hybrid(merged_text)


async def _request_with_retries(
    client: httpx.AsyncClient,
    params: Dict[str, Any],
    *,
    max_retries: int = DEFAULT_MAX_RETRIES,
) -> Dict[str, Any]:
    attempt = 0
    while True:
        try:
            response = await client.get(HH_VACANCIES_URL, params=params)
            if response.status_code in (429, 500, 502, 503, 504):
                raise httpx.HTTPStatusError(
                    f"Retryable HH status: {response.status_code}",
                    request=response.request,
                    response=response,
                )
            response.raise_for_status()
            return response.json()
        except (httpx.TimeoutException, httpx.NetworkError, httpx.HTTPStatusError):
            attempt += 1
            if attempt > max_retries:
                raise
            await asyncio.sleep(min(2**attempt, 8))


async def fetch_vacancies(
    roles: Sequence[str] = DEFAULT_IT_ROLES,
    *,
    pages_per_role: int = DEFAULT_PAGES_PER_ROLE,
    per_page: int = DEFAULT_PER_PAGE,
    area: int = KAZAKHSTAN_AREA_ID,
    period: Optional[int] = None,
    rate_limit_rps: float = DEFAULT_RATE_LIMIT_RPS,
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
) -> List[Dict[str, Any]]:
    """Fetch and normalize HH vacancies for the configured role queries."""
    if pages_per_role < 1:
        raise ValueError("pages_per_role must be >= 1")
    if per_page < 1:
        raise ValueError("per_page must be >= 1")
    if rate_limit_rps <= 0:
        raise ValueError("rate_limit_rps must be > 0")

    delay_between_requests = 1.0 / rate_limit_rps
    normalized: List[Dict[str, Any]] = []

    headers = {
        "User-Agent": "CareerBridge-HH-Parser/1.0",
        "Accept": "application/json",
    }
    timeout = httpx.Timeout(timeout_seconds)

    async with httpx.AsyncClient(headers=headers, timeout=timeout) as client:
        for role in roles:
            for page in range(pages_per_role):
                params: Dict[str, Any] = {
                    "text": role,
                    "area": area,
                    "page": page,
                    "per_page": per_page,
                }
                if period is not None:
                    params["period"] = period

                payload = await _request_with_retries(client, params=params)
                items = payload.get("items", [])
                if not items:
                    break

                for item in items:
                    normalized.append(normalize_hh_vacancy(item))

                total_pages = payload.get("pages")
                if isinstance(total_pages, int) and page >= total_pages - 1:
                    break

                await asyncio.sleep(delay_between_requests)

    return normalized


async def ingest_hh_vacancies(
    roles: Sequence[str] = DEFAULT_IT_ROLES,
    *,
    pages_per_role: int = DEFAULT_PAGES_PER_ROLE,
    per_page: int = DEFAULT_PER_PAGE,
    area: int = KAZAKHSTAN_AREA_ID,
    period: Optional[int] = None,
    rate_limit_rps: float = DEFAULT_RATE_LIMIT_RPS,
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
) -> Dict[str, int]:
    fetched_vacancies = await fetch_vacancies(
        roles=roles,
        pages_per_role=pages_per_role,
        per_page=per_page,
        area=area,
        period=period,
        rate_limit_rps=rate_limit_rps,
        timeout_seconds=timeout_seconds,
    )
    unique_vacancies = _dedup_batch(fetched_vacancies)

    report: Dict[str, int] = {
        "fetched": len(fetched_vacancies),
        "processed": len(unique_vacancies),
        "jobs_inserted": 0,
        "skills_created": 0,
        "links_created": 0,
        "errors": 0,
        "spacy_hits": 0,
        "gemini_fallbacks": 0,
    }

    vacancies_with_skills: List[Dict[str, Any]] = []
    for vacancy in unique_vacancies:
        enriched = dict(vacancy)
        try:
            extraction = await extract_skills_from_job_description(
                title=vacancy.get("title") or "",
                description=vacancy.get("description") or "",
            )
            enriched["skills"] = extraction["skills"]
            enriched["extraction_source"] = extraction["extraction_source"]
            if extraction["extraction_source"] == "spacy":
                report["spacy_hits"] += 1
            elif extraction["extraction_source"] == "gemini":
                report["gemini_fallbacks"] += 1
        except Exception:
            enriched["skills"] = []
            enriched["extraction_source"] = "gemini"
            report["errors"] += 1
        vacancies_with_skills.append(enriched)

    db = SessionLocal()
    try:
        persistence_report = await persist_vacancies(vacancies_with_skills, db)
    finally:
        db.close()

    report["jobs_inserted"] = persistence_report["jobs_inserted"]
    report["skills_created"] = persistence_report["skills_created"]
    report["links_created"] = persistence_report["links_created"]
    report["errors"] += persistence_report["errors"]
    report["spacy_hits"] = persistence_report["spacy_hits"]
    report["gemini_fallbacks"] = persistence_report["gemini_fallbacks"]

    return report


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
    )
    logger = logging.getLogger("hh_parser")

    logger.info("Starting HH vacancies ingestion (dry-run defaults enabled).")

    try:
        ingestion_report = asyncio.run(
            ingest_hh_vacancies(
                pages_per_role=1,
            )
        )
    except KeyboardInterrupt:
        logger.warning("Ingestion interrupted by user.")
        raise SystemExit(130)
    except Exception as exc:
        logger.exception("Ingestion failed: %s", exc)
        raise SystemExit(1)

    logger.info("Ingestion completed successfully.")
    logger.info("Report:")
    for key, value in ingestion_report.items():
        logger.info("  %s: %s", key, value)
