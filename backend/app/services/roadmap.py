import json
from typing import List, Dict, Any

from app.services.gemini_client import generate_json
from google.genai import errors as genai_errors

ROADMAP_SCHEMA = {
    "type": "object",
    "properties": {
        "nodes": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "title": {"type": "string"},
                    "skill": {"type": "string"},
                    "level": {
                        "type": "string",
                        "enum": ["beginner", "intermediate", "advanced"],
                    },
                    "estimated_hours": {"type": "integer"},
                    "resource_url": {"type": "string"},
                    "resource_title": {"type": "string"},
                    "description": {"type": "string"},
                },
                "required": ["id", "title", "skill", "level", "estimated_hours"],
            },
        },
        "edges": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "from": {"type": "string"},
                    "to": {"type": "string"},
                },
                "required": ["from", "to"],
            },
        },
    },
    "required": ["nodes", "edges"],
}

SYSTEM_PROMPT = (
    "You are a senior IT mentor for students in Kazakhstan. "
    "Build a practical, minimal learning roadmap that closes the skill gap "
    "for the target role. Prefer free, well-known resources (official docs, "
    "freeCodeCamp, MDN, roadmap.sh, Coursera free tracks). "
    "Order steps by prerequisites. 6-12 nodes total."
)


class RoadmapGenerationError(Exception):
    pass


def generate_roadmap(
    target_role: str,
    have_skills: List[str],
    missing_skills: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Sync wrapper kept for backward compatibility with existing router calls.
    Internally delegates to the async generate_roadmap_async via asyncio.
    """
    import asyncio
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # Inside an async context (e.g. called from a sync route in FastAPI)
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                future = pool.submit(asyncio.run, generate_roadmap_async(target_role, have_skills, missing_skills))
                return future.result()
        else:
            return loop.run_until_complete(
                generate_roadmap_async(target_role, have_skills, missing_skills)
            )
    except RoadmapGenerationError:
        raise
    except RuntimeError as e:
        raise RoadmapGenerationError(str(e))


async def generate_roadmap_async(
    target_role: str,
    have_skills: List[str],
    missing_skills: List[Dict[str, Any]],
) -> Dict[str, Any]:
    prompt = (
        f"{SYSTEM_PROMPT}\n\n"
        f"Target role: {target_role}\n"
        f"Skills the student already has: {', '.join(have_skills) or '(none)'}\n"
        f"Missing skills (ordered by market weight): "
        f"{json.dumps(missing_skills[:10], ensure_ascii=False)}\n\n"
        "Build a roadmap (DAG) that takes the student from current state to "
        "job-ready for this role. Focus on the missing skills. "
        "Each node = one focused learning step (~5-30h). "
        "Edges = prerequisites."
    )

    try:
        # Use gemini-2.5-pro for higher quality roadmap generation
        result = await generate_json(prompt, schema=ROADMAP_SCHEMA, model="gemini-2.5-flash")
    except genai_errors.ClientError as e:
        if e.code == 429:
            raise RoadmapGenerationError("AI rate limit exceeded, try later")
        raise RoadmapGenerationError(f"Gemini error: {e.message}")
    except Exception as e:
        raise RoadmapGenerationError(f"Unexpected AI error: {e}")

    return result  # {"nodes": [...], "edges": [...]}