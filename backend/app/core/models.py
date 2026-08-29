from __future__ import annotations

from dataclasses import dataclass, field, asdict
from enum import Enum
from pathlib import Path
from typing import Any


class BlockKind(str, Enum):
    TITLE = "title"
    TEXT = "text"
    LIST = "list"
    EQUATION = "equation"
    IMAGE = "image"
    TABLE = "table"
    CAPTION = "caption"
    REFERENCE = "reference"
    CODE = "code"
    AUXILIARY = "auxiliary"
    UNKNOWN = "unknown"


@dataclass
class DocumentBlock:
    id: str
    kind: BlockKind
    text: str = ""
    page: int = 0
    bbox: list[float] | None = None
    translatable: bool = True
    level: int | None = None
    asset_path: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    translated_text: str | None = None

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["kind"] = self.kind.value
        return data


@dataclass
class ParsedDocument:
    source_path: str
    blocks: list[DocumentBlock]
    parser: str
    warnings: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_path": Path(self.source_path).name,
            "parser": self.parser,
            "warnings": self.warnings,
            "metadata": self.metadata,
            "blocks": [b.to_dict() for b in self.blocks],
        }
