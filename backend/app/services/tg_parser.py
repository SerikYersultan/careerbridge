import asyncio
import logging
import os
from typing import Any, Dict, List, Sequence

from telethon import TelegramClient

from app.database import SessionLocal
from app.services.hh_parser import extract_skills_from_job_description
from app.services.shared_ingestion import persist_vacancies

DEFAULT_POST_LIMIT = 50

VACANCY_KEYWORDS = (
    "вакансия",
    "vacancy",
    "developer",
    "backend",
    "frontend",
    "fullstack",
    "python",
    "java",
    "javascript",
    "react",
    "node",
    "qa",
    "devops",
    "middle",
    "senior",
    "junior",
    "зарплата",
    "salary",
    "kzt",
    "опыт",
)


def _empty_report() -> Dict[str, int]:
    return {
        "fetched": 0,
        "processed": 0,
        "jobs_inserted": 0,
        "skills_created": 0,
        "links_created": 0,
        "errors": 0,
        "spacy_hits": 0,
        "gemini_fallbacks": 0,
    }


def _parse_channels(raw_channels: str | None) -> List[str]:
    if not raw_channels:
        return []
    return [item.strip().lstrip("@") for item in raw_channels.split(",") if item.strip()]


def is_vacancy_like_post(text: str) -> bool:
    normalized = (text or "").strip().lower()
    if len(normalized) < 40:
        return False
    return any(keyword in normalized for keyword in VACANCY_KEYWORDS)


def normalize_tg_post(message: Any, channel_username: str) -> Dict[str, Any]:
    text = (getattr(message, "message", "") or "").strip()
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    title = lines[0][:255] if lines else "Telegram vacancy"

    message_id = getattr(message, "id", None)
    source_url = None
    if channel_username and message_id:
        source_url = f"https://t.me/{channel_username}/{message_id}"

    return {
        "title": title,
        "company": "Unknown company",
        "location": None,
        "seniority": None,
        "description": text,
        "salary_min": None,
        "salary_max": None,
        "currency": "KZT",
        "source_url": source_url,
        "source": "telegram",
        "raw": {
            "channel": channel_username,
            "message_id": message_id,
            "date": str(getattr(message, "date", "")),
        },
    }


def _dedup_by_source_url(vacancies: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    unique: List[Dict[str, Any]] = []
    seen: set[str] = set()

    for item in vacancies:
        source_url = (item.get("source_url") or "").strip()
        if not source_url:
            source_url = f"tg:{item.get('raw', {}).get('channel', '')}:{item.get('raw', {}).get('message_id', '')}"
        if source_url in seen:
            continue
        seen.add(source_url)
        unique.append(item)
    return unique


async def ingest_tg_vacancies(
    *,
    channels: Sequence[str] | None = None,
    post_limit: int = DEFAULT_POST_LIMIT,
) -> Dict[str, int]:
    tg_api_id = os.getenv("TG_API_ID")
    tg_api_hash = os.getenv("TG_API_HASH")

    if not tg_api_id or not tg_api_hash:
        logging.warning("Telegram API keys not configured. Skipping TG parsing.")
        return _empty_report()

    configured_channels = list(channels or _parse_channels(os.getenv("TG_CHANNELS")))
    if not configured_channels:
        logging.warning("No TG channels configured. Skipping TG parsing.")
        return _empty_report()

    report = _empty_report()
    normalized_vacancies: List[Dict[str, Any]] = []

    session_name = os.getenv("TG_SESSION_NAME", "careerbridge_tg")
    client = TelegramClient(session_name, int(tg_api_id), tg_api_hash)

    async with client:
        for channel in configured_channels:
            try:
                async for message in client.iter_messages(channel, limit=post_limit):
                    report["fetched"] += 1
                    text = (getattr(message, "message", "") or "").strip()
                    if not text or not is_vacancy_like_post(text):
                        continue
                    normalized_vacancies.append(normalize_tg_post(message, channel))
            except Exception:
                report["errors"] += 1
                logging.exception("Failed to process channel '%s'", channel)

    unique_vacancies = _dedup_by_source_url(normalized_vacancies)
    report["processed"] = len(unique_vacancies)

    for vacancy in unique_vacancies:
        try:
            extraction = await extract_skills_from_job_description(
                title=vacancy.get("title") or "",
                description=vacancy.get("description") or "",
            )
            vacancy["skills"] = extraction["skills"]
            vacancy["extraction_source"] = extraction["extraction_source"]
            if extraction["extraction_source"] == "spacy":
                report["spacy_hits"] += 1
            elif extraction["extraction_source"] == "gemini":
                report["gemini_fallbacks"] += 1
        except Exception:
            vacancy["skills"] = []
            vacancy["extraction_source"] = "gemini"
            report["errors"] += 1

    db = SessionLocal()
    try:
        persistence_report = await persist_vacancies(unique_vacancies, db)
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
    logger = logging.getLogger("tg_parser")

    logger.info("Starting Telegram vacancies ingestion.")
    try:
        result = asyncio.run(ingest_tg_vacancies())
    except KeyboardInterrupt:
        logger.warning("Ingestion interrupted by user.")
        raise SystemExit(130)
    except Exception as exc:
        logger.exception("Ingestion failed: %s", exc)
        raise SystemExit(1)

    logger.info("Ingestion completed.")
    logger.info("Report:")
    for key, value in result.items():
        logger.info("  %s: %s", key, value)
