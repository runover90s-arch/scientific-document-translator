from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

from app.core.config import settings
from app.core.models import ParsedDocument
from .common import html_for_bilingual_document, html_for_document, markdown_for_document


def _write_pdf(html_path: Path, pdf_path: Path, output_dir: Path) -> bool:
    """Best-effort PDF export. Failure must not fail the translation job."""
    try:
        from weasyprint import HTML

        HTML(filename=str(html_path), base_url=str(output_dir)).write_pdf(str(pdf_path))
        if pdf_path.is_file() and pdf_path.stat().st_size > 0:
            return True
    except Exception:
        pass

    chromium = shutil.which(settings.chromium_command)
    if not chromium:
        return False
    cmd = [
        chromium,
        "--headless",
        "--no-sandbox",
        "--disable-gpu",
        "--disable-dev-shm-usage",
        "--no-pdf-header-footer",
        f"--print-to-pdf={pdf_path}",
        html_path.resolve().as_uri(),
    ]
    try:
        completed = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=20)
        return completed.returncode == 0 and pdf_path.is_file() and pdf_path.stat().st_size > 0
    except subprocess.TimeoutExpired:
        return False


def render_all(doc: ParsedDocument, output_dir: Path, validation: dict) -> dict[str, str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    md_path = output_dir / "translated.md"
    html_path = output_dir / "translated.html"
    bilingual_path = output_dir / "translated-bilingual.html"
    json_path = output_dir / "translated.json"

    md_path.write_text(markdown_for_document(doc), encoding="utf-8")
    html_path.write_text(html_for_document(doc), encoding="utf-8")
    bilingual_path.write_text(html_for_bilingual_document(doc), encoding="utf-8")
    json_path.write_text(
        json.dumps({"document": doc.to_dict(), "validation": validation}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    outputs = {
        "md": str(md_path),
        "html": str(html_path),
        "bilingual": str(bilingual_path),
        "json": str(json_path),
    }

    pdf_path = output_dir / "translated.pdf"
    if _write_pdf(html_path, pdf_path, output_dir):
        outputs["pdf"] = str(pdf_path)

    bilingual_pdf_path = output_dir / "translated-bilingual.pdf"
    if _write_pdf(bilingual_path, bilingual_pdf_path, output_dir):
        outputs["bilingual_pdf"] = str(bilingual_pdf_path)

    return outputs
