from __future__ import annotations

from app.core.config import settings
from .openai_compatible import OpenAICompatibleTranslator


def get_translator():
    mode = settings.translator_mode.lower()
    if mode in {"openai", "openai_compatible"}:
        return OpenAICompatibleTranslator()
    raise ValueError(f"Unsupported translator mode: {settings.translator_mode}")
