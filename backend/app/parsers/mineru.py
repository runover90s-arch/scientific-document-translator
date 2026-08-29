from __future__ import annotations

import html
import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

from app.core.config import settings
from app.core.models import BlockKind, DocumentBlock, ParsedDocument
from .base import DocumentParser


AUX_TYPES = {"page_header", "page_footer", "page_number", "page_aside_text", "page_footnote", "header", "footer"}


class MinerUParser(DocumentParser):
    def available(self) -> bool:
        return shutil.which(settings.mineru_command) is not None

    def parse(self, source_path: Path, work_dir: Path) -> ParsedDocument:
        parse_dir = work_dir / "mineru"
        parse_dir.mkdir(parents=True, exist_ok=True)
        command = [
            settings.mineru_command,
            "-p", str(source_path),
            "-o", str(parse_dir),
            "-b", settings.mineru_backend,
        ]
        completed = subprocess.run(command, capture_output=True, text=True, timeout=3600)
        if completed.returncode != 0:
            raise RuntimeError(f"MinerU failed: {completed.stderr[-4000:]}")

        # Legacy content_list currently documents image/table/formula fields explicitly,
        # while v2 is retained as metadata when available.
        legacy_files = sorted(parse_dir.rglob("*_content_list.json"))
        if not legacy_files:
            raise RuntimeError("MinerU completed but no *_content_list.json was found")
        content_file = legacy_files[0]
        raw = json.loads(content_file.read_text(encoding="utf-8"))
        if not isinstance(raw, list):
            raise RuntimeError("Unexpected MinerU content_list format")

        blocks: list[DocumentBlock] = []
        for idx, item in enumerate(raw):
            if not isinstance(item, dict):
                continue
            block = self._convert_item(item, idx, content_file.parent, work_dir)
            if block is not None:
                blocks.append(block)

        metadata: dict[str, Any] = {
            "mineru_content_list": content_file.name,
        }
        v2 = sorted(parse_dir.rglob("*_content_list_v2.json"))
        if v2:
            metadata["mineru_content_list_v2"] = v2[0].name
        return ParsedDocument(str(source_path), blocks, parser="mineru", metadata=metadata)

    def _copy_asset(self, asset: str | None, base: Path, work_dir: Path, block_id: str) -> str | None:
        if not asset:
            return None
        candidate = (base / asset).resolve()
        if not candidate.exists():
            # Some MinerU layouts put assets in a sibling nested output directory.
            matches = list(base.rglob(Path(asset).name))
            if not matches:
                return None
            candidate = matches[0]
        out_dir = work_dir / "output" / "assets"
        out_dir.mkdir(parents=True, exist_ok=True)
        target = out_dir / f"{block_id}_{candidate.name}"
        shutil.copy2(candidate, target)
        return f"assets/{target.name}"

    def _convert_item(self, item: dict[str, Any], idx: int, base: Path, work_dir: Path) -> DocumentBlock | None:
        t = str(item.get("type", "unknown"))
        block_id = f"b{idx:05d}"
        page = int(item.get("page_idx", 0) or 0)
        bbox = item.get("bbox")
        asset = self._copy_asset(item.get("img_path"), base, work_dir, block_id)

        if t == "text":
            level = item.get("text_level")
            kind = BlockKind.TITLE if level not in {None, 0} else BlockKind.TEXT
            return DocumentBlock(block_id, kind, str(item.get("text", "")), page, bbox, True, level=level)
        if t == "equation":
            return DocumentBlock(block_id, BlockKind.EQUATION, str(item.get("text", "")), page, bbox, False, asset_path=asset)
        if t == "image":
            captions = list(item.get("image_caption", []) or [])
            footnotes = list(item.get("image_footnote", []) or [])
            visible_text = "\n".join([*map(str, captions), *map(str, footnotes)]).strip()
            return DocumentBlock(
                block_id, BlockKind.IMAGE, visible_text, page, bbox, bool(visible_text), asset_path=asset,
                metadata={"caption": captions, "footnote": footnotes},
            )
        if t == "table":
            caption = "\n".join(map(str, item.get("table_caption", []) or []))
            body = str(item.get("table_body", ""))
            footnote = "\n".join(map(str, item.get("table_footnote", []) or []))
            parts: list[str] = []
            if caption:
                parts.append(f'<p class="table-caption">{html.escape(caption)}</p>')
            if body:
                parts.append(body)
            if footnote:
                parts.append(f'<p class="table-footnote">{html.escape(footnote)}</p>')
            combined = "\n".join(parts).strip()
            return DocumentBlock(
                block_id, BlockKind.TABLE, combined, page, bbox, True, asset_path=asset,
                metadata={"caption": caption, "table_body": body, "footnote": footnote},
            )
        if t == "chart":
            caption = "\n".join(item.get("chart_caption", []) or [])
            body = str(item.get("content", ""))
            return DocumentBlock(block_id, BlockKind.TABLE, (caption + "\n" + body).strip(), page, bbox, True,
                                 asset_path=asset, metadata={"chart": True})
        if t == "code":
            caption = "\n".join(item.get("code_caption", []) or [])
            code_body = str(item.get("code_body", ""))
            # Keep code immutable; translate caption only in a separate field later.
            return DocumentBlock(block_id, BlockKind.CODE, code_body, page, bbox, False,
                                 metadata={"caption": caption, "sub_type": item.get("sub_type")})
        if t == "list":
            items = item.get("list_items", []) or []
            subtype = item.get("sub_type")
            kind = BlockKind.REFERENCE if subtype == "ref_text" else BlockKind.LIST
            return DocumentBlock(block_id, kind, "\n".join(map(str, items)), page, bbox, kind != BlockKind.REFERENCE)
        if t in AUX_TYPES:
            text = str(item.get("text", ""))
            return DocumentBlock(block_id, BlockKind.AUXILIARY, text, page, bbox, False)
        return DocumentBlock(block_id, BlockKind.UNKNOWN, str(item.get("text", "")), page, bbox, False)
