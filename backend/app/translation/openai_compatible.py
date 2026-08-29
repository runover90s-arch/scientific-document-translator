from __future__ import annotations

import httpx

from app.core.config import settings
from .base import Translator


SYSTEM_PROMPT = """You are a scientific and technical translator.
Translate only natural-language content into the requested target language.
Rules:
1. Preserve every token matching __SDT_KEEP_XXXXXX__ exactly, including underscores and capitalization.
2. Do not alter equations, variables, numbers, units, DOI values, URLs, citations, or reference identifiers.
3. Preserve paragraph structure and Markdown/HTML structure when present.
4. Use academically standard terminology for mathematics, physics, chemistry, engineering and scholarly writing.
5. Do not summarize, omit, explain, add commentary, or change factual meaning.
6. Return only the translated content.
"""


class OpenAICompatibleTranslator(Translator):
    async def translate(self, text: str, source_language: str, target_language: str, context: str = "") -> str:
        if not settings.llm_api_key or not settings.llm_model:
            if settings.allow_passthrough_without_key:
                return text
            raise RuntimeError("LLM_API_KEY and LLM_MODEL must be configured")

        source = "auto-detected source language" if source_language == "auto" else source_language
        user_prompt = (
            f"Source language: {source}\n"
            f"Target language: {target_language}\n"
            f"Document context: {context[:2500] if context else 'none'}\n\n"
            f"Translate this content:\n{text}"
        )
        headers = {
            "Authorization": f"Bearer {settings.llm_api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": settings.llm_model,
            "temperature": 0,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
        }
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(f"{settings.llm_base_url}/chat/completions", headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
        return data["choices"][0]["message"]["content"].strip()
