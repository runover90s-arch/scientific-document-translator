import asyncio

from app.core.models import BlockKind, DocumentBlock, ParsedDocument
from app.services import pipeline


class FakeTranslator:
    async def translate(self, text, source_language, target_language, context=""):
        return text.replace("Algorithm", "Thuật toán")


def test_code_body_is_immutable_but_caption_is_translated(monkeypatch):
    monkeypatch.setattr(pipeline, "get_translator", lambda: FakeTranslator())
    block = DocumentBlock(
        id="b1",
        kind=BlockKind.CODE,
        text="for i in range(10):\n    print(i)",
        translatable=False,
        metadata={"caption": "Algorithm 1"},
    )
    doc = ParsedDocument(source_path="paper.pdf", blocks=[block], parser="test")

    translated, report = asyncio.run(pipeline.translate_document(doc, "en", "vi"))
    assert translated.blocks[0].translated_text == block.text
    assert translated.blocks[0].metadata["translated_caption"] == "Thuật toán 1"
    assert report["ok"] is True
