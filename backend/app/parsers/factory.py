from __future__ import annotations

from pathlib import Path

from .fallback import FallbackParser
from .mineru import MinerUParser


def parse_document(source_path: Path, work_dir: Path):
    mineru = MinerUParser()
    if mineru.available() and source_path.suffix.lower() not in {".txt", ".md"}:
        try:
            return mineru.parse(source_path, work_dir)
        except Exception as exc:
            fallback = FallbackParser()
            parsed = fallback.parse(source_path, work_dir)
            parsed.warnings.insert(0, f"MinerU failed, fallback parser used: {exc}")
            return parsed
    return FallbackParser().parse(source_path, work_dir)
