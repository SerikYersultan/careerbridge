import json
from typing import List, Dict, Any

from app.services.gemini_client import generate_json
from google.genai import errors as genai_errors

SYSTEM_PROMPT = (
    "You are a precise IT skill extractor. Given a candidate's resume text, "
    "return ONLY hard technical skills relevant for software engineering jobs "
    "(programming languages, frameworks, libraries, databases, cloud platforms, "
    "DevOps tools, methodologies). Do NOT include soft skills, languages spoken, "
    "company names, or job titles. Deduplicate. Use canonical names "
    "(e.g. 'PostgreSQL' not 'Postgres', 'JavaScript' not 'JS')."
)

SKILLS_SCHEMA = {
    "type": "object",
    "properties": {
        "skills": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "display_name": {"type": "string"},
                    "category": {
                        "type": "string",
                        "enum": ["language", "framework", "db", "cloud", "tool", "other"],
                    },
                },
                "required": ["display_name", "category"],
            },
        }
    },
    "required": ["skills"],
}


class AIServiceError(Exception):
    pass


async def extract_skills_from_resume(resume_text: str) -> List[Dict[str, Any]]:
    snippet = resume_text[:15000]

    prompt = (
        f"{SYSTEM_PROMPT}\n\n"
        f"Resume text:\n\n{snippet}"
    )

    try:
        result = await generate_json(prompt, schema=SKILLS_SCHEMA)
    except genai_errors.ClientError as e:
        if e.code == 429:
            raise AIServiceError("AI rate limit exceeded, try again later")
        raise AIServiceError(f"Gemini error: {e.message}")
    except Exception as e:
        raise AIServiceError(f"Unexpected AI error: {e}")

    skills = result.get("skills", [])

    # Dedup by normalized name
    seen = set()
    unique = []
    for s in skills:
        name = (s.get("display_name") or "").strip()
        if not name:
            continue
        key = name.lower()
        if key in seen:
            continue
        seen.add(key)
        unique.append({"display_name": name, "category": s.get("category", "other")})

    return unique