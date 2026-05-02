import os
import json
import httpx
from typing import List, Dict, Any

LOVABLE_API_URL = "https://ai.gateway.lovable.dev/v1/chat/completions"
LOVABLE_API_KEY = os.getenv("LOVABLE_API_KEY")
LOVABLE_AI_MODEL = os.getenv("LOVABLE_AI_MODEL", "google/gemini-2.5-flash")

SYSTEM_PROMPT = (
    "You are a precise IT skill extractor. Given a candidate's resume text, "
    "return ONLY hard technical skills relevant for software engineering jobs "
    "(programming languages, frameworks, libraries, databases, cloud platforms, "
    "DevOps tools, methodologies). Do NOT include soft skills, languages spoken, "
    "company names, or job titles. Deduplicate. Use canonical names "
    "(e.g. 'PostgreSQL' not 'Postgres', 'JavaScript' not 'JS')."
)

EXTRACT_TOOL = {
    "type": "function",
    "function": {
        "name": "return_skills",
        "description": "Return a deduplicated list of hard IT skills found in the resume.",
        "parameters": {
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
                        "additionalProperties": False,
                    },
                }
            },
            "required": ["skills"],
            "additionalProperties": False,
        },
    },
}


class AIServiceError(Exception):
    pass


async def extract_skills_from_resume(resume_text: str) -> List[Dict[str, Any]]:
    if not LOVABLE_API_KEY:
        raise AIServiceError("LOVABLE_API_KEY is not configured")

    # Обрезаем длинные резюме, чтобы не упереться в лимит контекста
    snippet = resume_text[:15000]

    payload = {
        "model": LOVABLE_AI_MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Resume text:\n\n{snippet}"},
        ],
        "tools": [EXTRACT_TOOL],
        "tool_choice": {"type": "function", "function": {"name": "return_skills"}},
    }

    headers = {
        "Authorization": f"Bearer {LOVABLE_API_KEY}",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(LOVABLE_API_URL, json=payload, headers=headers)

    if resp.status_code == 429:
        raise AIServiceError("AI rate limit exceeded, try again later")
    if resp.status_code == 402:
        raise AIServiceError("AI credits exhausted, top up workspace")
    if resp.status_code >= 400:
        raise AIServiceError(f"AI gateway error {resp.status_code}: {resp.text[:200]}")

    data = resp.json()
    try:
        tool_call = data["choices"][0]["message"]["tool_calls"][0]
        args = json.loads(tool_call["function"]["arguments"])
        skills = args.get("skills", [])
    except (KeyError, IndexError, json.JSONDecodeError) as e:
        raise AIServiceError(f"Malformed AI response: {e}")

    # дедуп по нормализованному имени
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
