from __future__ import annotations

import json
import re
import shutil
import uuid
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse

from app.core.config import settings
from app.core.jobs import JobRecord, job_store
from app.parsers.mineru import MinerUParser
from app.services.pipeline import run_job


router = APIRouter(prefix="/api/v1")
ALLOWED = {".pdf", ".docx", ".txt", ".md", ".png", ".jpg", ".jpeg", ".pptx", ".xlsx"}

LANGUAGES = [
    {"code": "auto", "name": "Auto detect"},
    {"code": "vi", "name": "Tiếng Việt"},
    {"code": "en", "name": "English"},
    {"code": "zh", "name": "中文"},
    {"code": "ja", "name": "日本語"},
    {"code": "ko", "name": "한국어"},
    {"code": "de", "name": "Deutsch"},
    {"code": "fr", "name": "Français"},
    {"code": "es", "name": "Español"},
    {"code": "ru", "name": "Русский"},
    {"code": "pt", "name": "Português"},
    {"code": "it", "name": "Italiano"},
    {"code": "ar", "name": "العربية"},
]


@router.get("/health")
def health():
    return {
        "ok": True,
        "app": settings.app_name,
        "mineru_available": MinerUParser().available(),
        "translator_configured": bool(settings.llm_api_key and settings.llm_model),
        "max_upload_mb": settings.max_upload_mb,
    }


@router.get("/languages")
def languages():
    return {"languages": LANGUAGES}


@router.post("/jobs")
async def create_job(
    background_tasks: BackgroundTasks,
    file: Annotated[UploadFile, File()],
    target_language: Annotated[str, Form()] = "vi",
    source_language: Annotated[str, Form()] = "auto",
    output_format: Annotated[str, Form()] = "html",
    glossary_json: Annotated[str, Form()] = "",
):
    suffix = Path(file.filename or "document").suffix.lower()
    if suffix not in ALLOWED:
        raise HTTPException(400, f"Unsupported file type: {suffix}")

    language_code = re.compile(r"^[A-Za-z]{2,3}(?:-[A-Za-z0-9]{2,8}){0,3}$")
    if source_language != "auto" and not language_code.fullmatch(source_language):
        raise HTTPException(400, "source_language must be 'auto' or a BCP-47-like language code, e.g. en, vi, zh-Hant")
    if not language_code.fullmatch(target_language):
        raise HTTPException(400, "target_language must be a BCP-47-like language code, e.g. en, vi, zh-Hant")

    glossary: dict[str, str] = {}
    if glossary_json.strip():
        try:
            parsed = json.loads(glossary_json)
            if not isinstance(parsed, dict) or not all(isinstance(k, str) and isinstance(v, str) for k, v in parsed.items()):
                raise ValueError
            glossary = parsed
        except (json.JSONDecodeError, ValueError):
            raise HTTPException(400, "glossary_json must be a JSON object of source-term to target-term strings")

    job_id = uuid.uuid4().hex
    job_dir = settings.storage_dir / "jobs" / job_id
    input_dir = job_dir / "input"
    input_dir.mkdir(parents=True, exist_ok=True)
    safe_name = Path(file.filename or f"document{suffix}").name
    input_path = input_dir / safe_name

    size = 0
    with input_path.open("wb") as out:
        while True:
            chunk = await file.read(1024 * 1024)
            if not chunk:
                break
            size += len(chunk)
            if size > settings.max_upload_mb * 1024 * 1024:
                out.close()
                shutil.rmtree(job_dir, ignore_errors=True)
                raise HTTPException(413, f"File exceeds {settings.max_upload_mb} MB limit")
            out.write(chunk)

    record = JobRecord(
        id=job_id,
        filename=safe_name,
        source_language=source_language,
        target_language=target_language,
        output_format=output_format,
    )
    job_store.create(record)
    background_tasks.add_task(
        run_job,
        job_id,
        input_path,
        job_dir,
        source_language,
        target_language,
        glossary,
    )
    return record.to_public_dict()


@router.get("/jobs/{job_id}")
def get_job(job_id: str):
    job = job_store.get(job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    return job.to_public_dict()


@router.get("/jobs/{job_id}/download/{fmt}")
def download(job_id: str, fmt: str):
    job = job_store.get(job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    path = job.outputs.get(fmt)
    if not path:
        raise HTTPException(404, f"Output format not available: {fmt}")
    file_path = Path(path)
    if not file_path.is_file():
        raise HTTPException(410, "Output file is no longer available")
    media = {
        "html": "text/html",
        "bilingual": "text/html",
        "md": "text/markdown",
        "json": "application/json",
        "pdf": "application/pdf",
        "bilingual_pdf": "application/pdf",
    }.get(fmt, "application/octet-stream")
    return FileResponse(file_path, media_type=media, filename=file_path.name)
