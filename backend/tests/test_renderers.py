from app.core.models import BlockKind, DocumentBlock, ParsedDocument
from app.renderers.common import html_for_bilingual_document, html_for_document


def test_bilingual_output_contains_source_and_translation():
    block = DocumentBlock(id="b1", kind=BlockKind.TEXT, text="Wave function ψ = 1")
    block.translated_text = "Hàm sóng ψ = 1"
    doc = ParsedDocument(source_path="paper.pdf", blocks=[block], parser="test")

    html = html_for_bilingual_document(doc)
    assert "Wave function" in html
    assert "Hàm sóng" in html
    assert "ψ" in html


def test_plain_table_text_is_escaped_in_html_renderer():
    block = DocumentBlock(id="b1", kind=BlockKind.TABLE, text="A < B | 42")
    doc = ParsedDocument(source_path="paper.docx", blocks=[block], parser="test")

    html = html_for_document(doc)
    assert "A &lt; B" in html
    assert "A < B" not in html


def test_table_html_sanitizer_removes_scripts_and_event_handlers():
    block = DocumentBlock(
        id="b1",
        kind=BlockKind.TABLE,
        text='<table onclick="alert(1)"><tr><td rowspan="2">Safe</td><td><script>alert(2)</script>42</td></tr></table>',
    )
    doc = ParsedDocument(source_path="paper.pdf", blocks=[block], parser="test")

    rendered = html_for_document(doc)
    assert '<script' not in rendered
    assert 'onclick=' not in rendered
    assert 'rowspan="2"' in rendered
    assert '>42<' in rendered
