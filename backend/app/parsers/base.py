from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from app.core.models import ParsedDocument


class DocumentParser(ABC):
    @abstractmethod
    def parse(self, source_path: Path, work_dir: Path) -> ParsedDocument:
        raise NotImplementedError
