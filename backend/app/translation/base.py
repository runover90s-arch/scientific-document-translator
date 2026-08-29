from __future__ import annotations

from abc import ABC, abstractmethod


class Translator(ABC):
    @abstractmethod
    async def translate(self, text: str, source_language: str, target_language: str, context: str = "") -> str:
        raise NotImplementedError
