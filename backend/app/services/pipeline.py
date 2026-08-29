from __future__ import annotations

import asyncio
import re
from pathlib import Path

from bs4 import BeautifulSoup, NavigableString

from app.core.jobs import job_store
from app.core.models import BlockKind, ParsedDocument
from app.parsers.factory import parse_document
from app.protection.guard import protect, restore
from app.protection.validators import ValidationReport, validate_text
from app.renderers.output import render_all
from app.translation.factory import get_translator


TRANSLATABLE_KINDS = {BlockKind.TITLE, BlockKind.TEXT, BlockKind.LIST, BlockKind.CAPTION, BlockKind.TABLE}


def _document_context(doc: ParsedDocument, glossary: dict[str, str] | None = None) -> str:
    titles = [b.text for b in doc.blocks if b.kind == BlockKind.TITLE and b.text.strip()]
    intro = [b.text for b in doc.blocks if b.kind == BlockKind.TEXT and b.text.strip()][:3]
    context = "\n".join((titles + intro))[:3500]
    if glossary:
        terms = "\n".join(f"- {src} => {dst}" for src, dst in list(glossary.items())[:100])
        context += f"\n\nMANDATORY TERMINOLOGY GLOSSARY:\n{terms}"
    return context[:6000]


async def _translate_plain_text(text: str, translator, source_language: str, target_language: str, context: str) -> str:
    guarded = protect(text)
    translated = await translator.translate(guarded.protected, source_language, target_language, context)
    return restore(translated, guarded.mapping, strict=True)


async def _translate_html_table(text: str, translator, source_language: str, target_language: str, context: str) -> str:
    """Translate visible table/caption/footnote text while preserving nested markup."""
    if "<table" not in text.lower():
        return await _translate_plain_text(text, translator, source_language, target_language, context)

    # MinerU may embed <html><body> around table_body. Strip only those wrappers so
    # caption/footnote text before or after the table remains part of the fragment.
    fragment = re.sub(r"</?(?:html|body)\b[^>]*>", "", text, flags=re.IGNORECASE)
    soup = BeautifulSoup(fragment, "html.parser")

    for node in list(soup.find_all(string=True)):
        if node.parent and node.parent.name in {"script", "style"}:
            continue
        raw = str(node)
        core = raw.strip()
        if not core:
            continue
        leading = raw[: len(raw) - len(raw.lstrip())]
        trailing = raw[len(raw.rstrip()):]
        translated = await _translate_plain_text(core, translator, source_language, target_language, context)
        node.replace_with(NavigableString(leading + translated + trailing))

    return str(soup).strip()


async def translate_document(
    doc: ParsedDocument,
    source_language: str,
    target_language: str,
    glossary: dict[str, str] | None = None,
    job_id: str | None = None,
) -> tuple[ParsedDocument, dict]:
    translator = get_translator()
    context = _document_context(doc, glossary)
    all_numeric_ok = True
    all_symbol_ok = True
    equation_ok = True
    details: list[str] = []

    candidates = [
        b for b in doc.blocks
        if b.translatable and b.kind in TRANSLATABLE_KINDS and b.text.strip()
    ]
    total = len(candidates)
    translated_count = 0

    for block in doc.blocks:
        if block.kind == BlockKind.CODE:
            # Code/algorithm body is immutable; only its natural-language caption is translated.
            block.translated_text = block.text
            caption = str(block.metadata.get("caption", "")).strip()
            if caption:
                try:
                    translated_caption = await _translate_plain_text(
                        caption, translator, source_language, target_language, context
                    )
                    block.metadata["translated_caption"] = translated_caption
                    numeric_ok, symbol_ok, block_details = validate_text(caption, translated_caption)
                    all_numeric_ok &= numeric_ok
                    all_symbol_ok &= symbol_ok
                    if block_details:
                        details.extend([f"{block.id}:caption: {d}" for d in block_details])
                except Exception as exc:
                    block.metadata["translated_caption"] = caption
                    all_numeric_ok = False
                    details.append(f"{block.id}: caption translation rejected and source restored: {exc}")
            continue
        if block.kind == BlockKind.EQUATION:
            # Equation blocks are immutable; original crop/LaTeX is reused.
            block.translated_text = block.text
            continue
        if not block.translatable or block.kind not in TRANSLATABLE_KINDS or not block.text.strip():
            block.translated_text = block.text
            continue

        try:
            if block.kind == BlockKind.TABLE:
                translated = await _translate_html_table(block.text, translator, source_language, target_language, context)
            else:
                translated = await _translate_plain_text(block.text, translator, source_language, target_language, context)
            block.translated_text = translated
            numeric_ok, symbol_ok, block_details = validate_text(block.text, translated)
            all_numeric_ok &= numeric_ok
            all_symbol_ok &= symbol_ok
            if block_details:
                details.extend([f"{block.id}: {d}" for d in block_details])
        except Exception as exc:
            # Fail closed: never emit a silently corrupted scientific block.
            block.translated_text = block.text
            all_numeric_ok = False
            details.append(f"{block.id}: translation rejected and source restored: {exc}")

        translated_count += 1
        if job_id and total:
            progress = 35 + int((translated_count / total) * 40)
            job_store.update(
                job_id,
                progress=min(progress, 75),
                message=f"Translating block {translated_count}/{total}",
            )

    report = ValidationReport(
        ok=all_numeric_ok and all_symbol_ok and equation_ok,
        numeric_integrity=all_numeric_ok,
        symbol_integrity=all_symbol_ok,
        equation_integrity=equation_ok,
        details=details,
    )
    return doc, report.to_dict()


async def run_job(
    job_id: str,
    input_path: Path,
    job_dir: Path,
    source_language: str,
    target_language: str,
    glossary: dict[str, str] | None = None,
) -> None:
    try:
        job_store.update(job_id, status="parsing", progress=10, message="Parsing document")
        doc = await asyncio.to_thread(parse_document, input_path, job_dir)
        if doc.warnings:
            job_store.update(job_id, warnings=doc.warnings)

        job_store.update(job_id, status="translating", progress=35, message="Translating protected text blocks")
        translated_doc, validation = await translate_document(
            doc,
            source_language,
            target_language,
            glossary=glossary,
            job_id=job_id,
        )

        job_store.update(job_id, status="rendering", progress=80, message="Rendering outputs", validation=validation)
        outputs = await asyncio.to_thread(render_all, translated_doc, job_dir / "output", validation)
        job_store.update(job_id, status="completed", progress=100, message="Completed", outputs=outputs, validation=validation)
    except Exception as exc:
        job_store.update(job_id, status="failed", progress=100, message="Failed", error=str(exc))
