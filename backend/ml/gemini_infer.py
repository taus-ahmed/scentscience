"""
AI-powered note inference for perfumes not in the database.
Primary: Gemini (google-generativeai). Fallback: Groq (openai-compatible).
Both require the relevant API key to be set in settings.
"""

import asyncio
import json
import logging
import re
from typing import Optional

logger = logging.getLogger(__name__)

_INFER_PROMPT = (
    'You are a fragrance expert. For the perfume "{name}" by "{brand}", '
    "return a JSON object with exactly these keys:\n"
    '{{\n'
    '  "top_notes": ["list of 3-5 note names"],\n'
    '  "middle_notes": ["list of 3-6 note names"],\n'
    '  "base_notes": ["list of 2-4 note names"],\n'
    '  "concentration": "EDT|EDP|Parfum|EDC",\n'
    '  "family": "floral|woody|oriental|fresh|citrus|aquatic|fougere|chypre|gourmand|aromatic",\n'
    '  "confidence": "high|medium|low"\n'
    "}}\n"
    "Use only common, well-known fragrance notes. Return only the JSON, nothing else."
)


def _extract_json(text: str) -> dict:
    """Strip markdown fences and parse JSON from LLM response."""
    text = text.strip()
    # Remove ```json ... ``` or ``` ... ``` fences
    text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.MULTILINE)
    text = re.sub(r"\s*```\s*$", "", text, flags=re.MULTILINE)
    return json.loads(text.strip())


async def _infer_via_gemini(name: str, brand: str, api_key: str) -> dict:
    try:
        import google.generativeai as genai
    except ImportError:
        raise RuntimeError("google-generativeai not installed (pip install google-generativeai)")

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-1.5-flash")
    prompt = _INFER_PROMPT.format(name=name, brand=brand)

    # google-generativeai is sync — run in thread to avoid blocking the event loop
    response = await asyncio.to_thread(model.generate_content, prompt)
    return _extract_json(response.text)


async def _infer_via_groq(name: str, brand: str, api_key: str) -> dict:
    try:
        from groq import AsyncGroq
    except ImportError:
        raise RuntimeError("groq not installed (pip install groq)")

    client = AsyncGroq(api_key=api_key)
    prompt = _INFER_PROMPT.format(name=name, brand=brand)
    response = await client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
        max_tokens=512,
    )
    return _extract_json(response.choices[0].message.content)


async def infer_notes(
    name: str,
    brand: str,
    gemini_api_key: str = "",
    groq_api_key: str = "",
) -> dict:
    """
    Infer note pyramid for an unknown perfume using Gemini or Groq.

    Returns a dict with keys:
        top_notes, middle_notes, base_notes, concentration, family, confidence

    Raises RuntimeError if no API keys are configured or both calls fail.
    """
    last_error: Optional[Exception] = None

    if gemini_api_key:
        try:
            data = await _infer_via_gemini(name, brand, gemini_api_key)
            logger.info("Gemini inferred notes for '%s' by '%s'", name, brand)
            return _validate_inferred(data)
        except Exception as exc:
            logger.warning("Gemini inference failed (%s), trying Groq next", exc)
            last_error = exc

    if groq_api_key:
        try:
            data = await _infer_via_groq(name, brand, groq_api_key)
            logger.info("Groq inferred notes for '%s' by '%s'", name, brand)
            return _validate_inferred(data)
        except Exception as exc:
            logger.warning("Groq inference failed: %s", exc)
            last_error = exc

    if last_error:
        raise RuntimeError(f"All inference backends failed: {last_error}")
    raise RuntimeError("No AI inference API keys configured (set GEMINI_API_KEY or GROQ_API_KEY)")


def _validate_inferred(data: dict) -> dict:
    """Ensure required keys are present and types are correct."""
    def _listify(v):
        if isinstance(v, list):
            return [str(x).strip() for x in v if str(x).strip()]
        return []

    return {
        "top_notes":    _listify(data.get("top_notes", [])),
        "middle_notes": _listify(data.get("middle_notes", [])),
        "base_notes":   _listify(data.get("base_notes", [])),
        "concentration": str(data.get("concentration", "EDT")),
        "family":       str(data.get("family", "")).lower().strip() or "oriental",
        "confidence":   str(data.get("confidence", "low")).lower().strip(),
    }
