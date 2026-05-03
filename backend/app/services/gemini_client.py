import os
import json
from google import genai
from google.genai import types

_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

async def generate_json(prompt: str, schema: dict, model: str | None = None) -> dict:
    resp = await _client.aio.models.generate_content(
        model=model or GEMINI_MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=schema,
            temperature=0.3,
        ),
    )
    return json.loads(resp.text)

async def generate_text(prompt: str, model: str | None = None) -> str:
    resp = await _client.aio.models.generate_content(
        model=model or GEMINI_MODEL,
        contents=prompt,
    )
    return resp.text
