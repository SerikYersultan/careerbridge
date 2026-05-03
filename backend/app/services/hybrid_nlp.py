import logging
from typing import Any, Dict, List

import spacy
from spacy.language import Language
from spacy.matcher import PhraseMatcher

from app.services.ai import AIServiceError, extract_skills_from_resume

logger = logging.getLogger(__name__)

SPACY_MODEL = "en_core_web_sm"
SPACY_MIN_HITS = 4

SKILL_LEXICON: Dict[str, str] = {
    "python": "language",
    "java": "language",
    "javascript": "language",
    "typescript": "language",
    "go": "language",
    "sql": "language",
    "fastapi": "framework",
    "django": "framework",
    "flask": "framework",
    "react": "framework",
    "next.js": "framework",
    "node.js": "framework",
    "docker": "tool",
    "kubernetes": "tool",
    "git": "tool",
    "postgresql": "db",
    "mysql": "db",
    "mongodb": "db",
    "redis": "db",
    "aws": "cloud",
    "gcp": "cloud",
    "azure": "cloud",
}

_NLP: Language | None = None
_MATCHER: PhraseMatcher | None = None


def _load_spacy_pipeline() -> tuple[Language, PhraseMatcher]:
    global _NLP, _MATCHER
    if _NLP is not None and _MATCHER is not None:
        return _NLP, _MATCHER

    try:
        nlp = spacy.load(SPACY_MODEL)
    except Exception:
        logger.warning(
            "spaCy model '%s' is not available. Falling back to blank 'en'. "
            "Install model with: python -m spacy download %s",
            SPACY_MODEL,
            SPACY_MODEL,
        )
        nlp = spacy.blank("en")

    matcher = PhraseMatcher(nlp.vocab, attr="LOWER")
    patterns = [nlp.make_doc(skill) for skill in SKILL_LEXICON.keys()]
    matcher.add("HARD_SKILLS", patterns)

    _NLP = nlp
    _MATCHER = matcher
    return nlp, matcher


def extract_skills_spacy(text: str) -> List[Dict[str, str]]:
    """Extract skills with a local PhraseMatcher against a fixed lexicon."""
    content = (text or "").strip()
    if not content:
        return []

    nlp, matcher = _load_spacy_pipeline()
    doc = nlp(content[:30000])

    found: List[Dict[str, str]] = []
    seen: set[str] = set()
    for _, start, end in matcher(doc):
        candidate = doc[start:end].text.strip()
        key = candidate.lower()
        if key not in SKILL_LEXICON:
            continue
        if key in seen:
            continue
        seen.add(key)
        found.append({"display_name": candidate, "category": SKILL_LEXICON[key]})

    return found


async def extract_skills_hybrid(
    text: str,
    *,
    min_spacy_hits: int = SPACY_MIN_HITS,
) -> Dict[str, Any]:
    """Use spaCy first and fallback to Gemini when signal is weak."""
    spacy_skills = extract_skills_spacy(text)
    if len(spacy_skills) >= min_spacy_hits:
        logger.info(
            "[NLP] Fast-path triggered: Extracted %s skills using spaCy local model.",
            len(spacy_skills),
        )
        return {
            "skills": spacy_skills,
            "extraction_source": "spacy",
        }

    # Fallback to Gemini for sparse or noisy text.
    logger.info("[NLP] Complexity threshold not met. Fallback to LLM (Gemini) triggered.")
    try:
        llm_skills = await extract_skills_from_resume(text)
        return {
            "skills": llm_skills,
            "extraction_source": "gemini",
        }
    except AIServiceError:
        raise
