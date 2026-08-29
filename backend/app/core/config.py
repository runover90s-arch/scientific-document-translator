from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


load_dotenv()


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    app_name: str = os.getenv("APP_NAME", "Scientific Document Translator")
    storage_dir: Path = Path(os.getenv("STORAGE_DIR", "./storage")).resolve()
    translator_mode: str = os.getenv("TRANSLATOR_MODE", "openai_compatible")
    llm_base_url: str = os.getenv("LLM_BASE_URL", "https://api.openai.com/v1").rstrip("/")
    llm_api_key: str = os.getenv("LLM_API_KEY", "")
    llm_model: str = os.getenv("LLM_MODEL", "")
    mineru_command: str = os.getenv("MINERU_COMMAND", "mineru")
    mineru_backend: str = os.getenv("MINERU_BACKEND", "pipeline")
    chromium_command: str = os.getenv("CHROMIUM_COMMAND", "chromium")
    max_upload_mb: int = int(os.getenv("MAX_UPLOAD_MB", "100"))
    allow_passthrough_without_key: bool = _env_bool("ALLOW_PASSTHROUGH_WITHOUT_KEY", False)


settings = Settings()
settings.storage_dir.mkdir(parents=True, exist_ok=True)
(settings.storage_dir / "jobs").mkdir(parents=True, exist_ok=True)
