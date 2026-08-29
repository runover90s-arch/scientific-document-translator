from __future__ import annotations

import html
import re
from pathlib import Path

from bs4 import BeautifulSoup

from app.core.models import BlockKind, DocumentBlock, ParsedDocument


INLINE_MATH = re.compile(r"\$(?!\$)(.+?)(?<!\$)\$", re.DOTALL)
DISPLAY_MATH = re.compile(r"\$\$(.+?)\$\$", re.DOTALL)


def text_of(block: DocumentBlock) -> str:
    return block.translated_text if block.translated_text is not None else block.text


def markdown_for_document(doc: ParsedDocument) -> str:
    out: list[str] = []
    for block in doc.blocks:
        text = text_of(block).strip()
        if block.kind == BlockKind.TITLE:
            level = max(1, min(6, int(block.level or 1)))
            out.append(f"{'#' * level} {text}")
        elif block.kind == BlockKind.EQUATION:
            if block.asset_path:
                out.append(f"![equation]({block.asset_path})")
            else:
                out.append(text)
        elif block.kind == BlockKind.IMAGE:
            if block.asset_path:
                out.append(f"![figure]({block.asset_path})")
            if text:
                out.append(text)
        elif block.kind == BlockKind.TABLE:
            # If the body is HTML, Markdown allows raw HTML passthrough.
            out.append(text)
        elif block.kind == BlockKind.CODE:
            caption = block.metadata.get("translated_caption", block.metadata.get("caption"))
            if caption:
                out.append(str(caption))
            out.append(f"```\n{text}\n```")
        elif block.kind == BlockKind.LIST:
            for line in text.splitlines():
                out.append(f"- {line}")
        elif block.kind in {BlockKind.REFERENCE, BlockKind.AUXILIARY}:
            out.append(text)
        elif text:
            out.append(text)
    return "\n\n".join(x for x in out if x.strip()) + "\n"


def _math_html(text: str) -> str:
    # Escape natural language while keeping LaTeX segments visibly intact. Formula blocks
    # prefer original MinerU crops, so this is mainly for inline equations.
    tokens: dict[str, str] = {}
    counter = 0

    def keep(match: re.Match[str], display: bool) -> str:
        nonlocal counter
        token = f"SDTMATHPLACEHOLDER{counter}X"
        counter += 1
        body = match.group(1).strip()
        tag = "div" if display else "span"
        cls = "latex" if display else "latex inline"
        tokens[token] = f'<{tag} class="{cls}">{html.escape(body)}</{tag}>'
        return token

    staged = DISPLAY_MATH.sub(lambda m: keep(m, True), text)
    staged = INLINE_MATH.sub(lambda m: keep(m, False), staged)
    escaped = html.escape(staged).replace("\n", "<br>")
    for token, replacement in tokens.items():
        escaped = escaped.replace(token, replacement)
    return escaped


def html_for_document(doc: ParsedDocument, title: str = "Translated document") -> str:
    chunks: list[str] = []
    for block in doc.blocks:
        text = text_of(block).strip()
        page_attr = f' data-page="{block.page + 1}"'
        if block.kind == BlockKind.TITLE:
            level = max(1, min(6, int(block.level or 1)))
            chunks.append(f"<h{level}{page_attr}>{_math_html(text)}</h{level}>")
        elif block.kind == BlockKind.EQUATION:
            if block.asset_path:
                chunks.append(f'<figure class="equation"{page_attr}><img src="{html.escape(block.asset_path)}" alt="equation"><figcaption class="sr-only">{html.escape(text)}</figcaption></figure>')
            else:
                chunks.append(f'<div class="equation latex"{page_attr}>{html.escape(text)}</div>')
        elif block.kind == BlockKind.IMAGE:
            body = ""
            if block.asset_path:
                body += f'<img src="{html.escape(block.asset_path)}" alt="figure">'
            if text:
                body += f"<figcaption>{_math_html(text)}</figcaption>"
            chunks.append(f"<figure{page_attr}>{body}</figure>")
        elif block.kind == BlockKind.TABLE:
            chunks.append(f'<section class="table-wrap"{page_attr}>{_safe_table_html(text)}</section>')
        elif block.kind == BlockKind.CODE:
            caption = html.escape(str(block.metadata.get("translated_caption", block.metadata.get("caption", ""))))
            chunks.append(f'<section{page_attr}>{f"<p>{caption}</p>" if caption else ""}<pre><code>{html.escape(text)}</code></pre></section>')
        elif block.kind == BlockKind.LIST:
            lis = "".join(f"<li>{_math_html(line)}</li>" for line in text.splitlines() if line.strip())
            chunks.append(f"<ul{page_attr}>{lis}</ul>")
        elif block.kind == BlockKind.REFERENCE:
            chunks.append(f'<p class="reference"{page_attr}>{_math_html(text)}</p>')
        elif block.kind == BlockKind.AUXILIARY:
            if text:
                chunks.append(f'<p class="aux"{page_attr}>{_math_html(text)}</p>')
        elif text:
            chunks.append(f"<p{page_attr}>{_math_html(text)}</p>")

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(title)}</title>
<style>
:root{{font-family:Inter,system-ui,-apple-system,Segoe UI,Roboto,Arial,sans-serif;color:#111827;background:#f3f4f6}}
body{{margin:0}} main{{max-width:920px;margin:24px auto;padding:48px;background:white;box-shadow:0 6px 30px #0001}}
p,li{{font-size:16px;line-height:1.72}} h1,h2,h3{{line-height:1.25}} figure{{margin:28px 0;text-align:center}} img{{max-width:100%;height:auto}}
figcaption{{font-size:14px;color:#4b5563;margin-top:8px}} .equation img{{max-height:180px;object-fit:contain}}
.latex{{font-family:'Times New Roman',serif;white-space:pre-wrap;background:#f9fafb;padding:10px;border-radius:8px}}
.table-wrap{{overflow-x:auto;margin:24px 0}} table{{border-collapse:collapse;width:100%}} td,th{{border:1px solid #d1d5db;padding:7px;vertical-align:top}}
pre{{overflow:auto;background:#111827;color:white;padding:16px;border-radius:10px}} .reference,.aux{{font-size:14px}} .sr-only{{position:absolute;left:-10000px}}
@media(max-width:700px){{main{{margin:0;padding:22px;box-shadow:none}}}}
@media print{{:root{{background:white}} main{{margin:0;max-width:none;padding:0;box-shadow:none}}}}
</style>
</head>
<body><main>{''.join(chunks)}</main></body></html>"""


def _safe_table_html(text: str) -> str:
    """Render parser-produced table HTML with a narrow allowlist."""
    if "<table" not in text.lower():
        return f'<div class="table-text">{_math_html(text)}</div>'

    allowed_tags = {
        "table", "thead", "tbody", "tfoot", "tr", "th", "td", "caption",
        "p", "br", "span", "sup", "sub", "em", "strong", "i", "b",
    }
    allowed_attrs = {
        "td": {"rowspan", "colspan"},
        "th": {"rowspan", "colspan"},
        "p": {"class"},
        "span": {"class"},
        "table": {"class"},
    }
    soup = BeautifulSoup(text, "html.parser")
    for dangerous in soup.find_all(["script", "style", "iframe", "object", "embed", "link", "meta"]):
        dangerous.decompose()
    for tag in list(soup.find_all(True)):
        if tag.name not in allowed_tags:
            tag.unwrap()
            continue
        keep = allowed_attrs.get(tag.name, set())
        tag.attrs = {k: v for k, v in tag.attrs.items() if k in keep}
    return str(soup)


def html_for_bilingual_document(doc: ParsedDocument, title: str = "Bilingual translated document") -> str:
    """Side-by-side source/translation HTML for study and verification."""
    chunks: list[str] = []
    for block in doc.blocks:
        source = block.text.strip()
        target = text_of(block).strip()
        page_attr = f' data-page="{block.page + 1}"'

        if block.kind == BlockKind.EQUATION:
            if block.asset_path:
                chunks.append(
                    f'<figure class="full equation"{page_attr}><img src="{html.escape(block.asset_path)}" alt="equation">'
                    f'<figcaption class="sr-only">{html.escape(source)}</figcaption></figure>'
                )
            elif source:
                chunks.append(f'<div class="full equation latex"{page_attr}>{html.escape(source)}</div>')
            continue

        if block.kind == BlockKind.IMAGE:
            body = ""
            if block.asset_path:
                body += f'<img src="{html.escape(block.asset_path)}" alt="figure">'
            if source or target:
                body += '<div class="bi captions">'
                body += f'<div><strong>Source</strong><div>{_math_html(source)}</div></div>'
                body += f'<div><strong>Translation</strong><div>{_math_html(target)}</div></div>'
                body += '</div>'
            chunks.append(f'<figure class="full"{page_attr}>{body}</figure>')
            continue

        if block.kind == BlockKind.CODE:
            caption = str(block.metadata.get("caption", ""))
            translated_caption = str(block.metadata.get("translated_caption", caption))
            cap = ""
            if caption or translated_caption:
                cap = (
                    '<div class="bi captions">'
                    f'<div><strong>Source</strong><div>{_math_html(caption)}</div></div>'
                    f'<div><strong>Translation</strong><div>{_math_html(translated_caption)}</div></div>'
                    '</div>'
                )
            chunks.append(f'<section class="full"{page_attr}>{cap}<pre><code>{html.escape(source)}</code></pre></section>')
            continue

        if block.kind == BlockKind.TABLE:
            chunks.append(
                f'<section class="bi table-bi"{page_attr}>'
                f'<div><strong>Source</strong>{_safe_table_html(source)}</div>'
                f'<div><strong>Translation</strong>{_safe_table_html(target)}</div>'
                f'</section>'
            )
            continue

        if not source and not target:
            continue

        source_html = _math_html(source)
        target_html = _math_html(target)
        tag = "div"
        cls = "bi"
        if block.kind == BlockKind.TITLE:
            cls += " title-bi"
        elif block.kind == BlockKind.REFERENCE:
            cls += " reference-bi"
        elif block.kind == BlockKind.AUXILIARY:
            cls += " aux-bi"
        chunks.append(
            f'<{tag} class="{cls}"{page_attr}>'
            f'<div><strong>Source</strong><div>{source_html}</div></div>'
            f'<div><strong>Translation</strong><div>{target_html}</div></div>'
            f'</{tag}>'
        )

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(title)}</title>
<style>
:root{{font-family:Inter,system-ui,-apple-system,Segoe UI,Roboto,Arial,sans-serif;color:#111827;background:#f3f4f6}}
body{{margin:0}} main{{max-width:1180px;margin:24px auto;padding:40px;background:white;box-shadow:0 6px 30px #0001}}
.bi{{display:grid;grid-template-columns:1fr 1fr;gap:24px;border-bottom:1px solid #e5e7eb;padding:18px 0}}
.bi>div{{min-width:0}} .bi strong{{display:block;font-size:12px;text-transform:uppercase;letter-spacing:.06em;color:#6b7280;margin-bottom:8px}}
.title-bi{{font-size:1.15em;font-weight:650}} .reference-bi,.aux-bi{{font-size:14px}} .full{{grid-column:1/-1;margin:26px 0}}
p,li,.bi>div>div{{line-height:1.72}} figure{{text-align:center}} img{{max-width:100%;height:auto}} .equation img{{max-height:180px;object-fit:contain}}
.latex{{font-family:'Times New Roman',serif;white-space:pre-wrap;background:#f9fafb;padding:10px;border-radius:8px}}
.table-bi{{align-items:start}} .table-bi table{{border-collapse:collapse;width:100%}} td,th{{border:1px solid #d1d5db;padding:7px;vertical-align:top}}
.table-text{{white-space:normal}} pre{{overflow:auto;background:#111827;color:white;padding:16px;border-radius:10px}} .sr-only{{position:absolute;left:-10000px}}
@media(max-width:760px){{main{{margin:0;padding:18px;box-shadow:none}}.bi{{grid-template-columns:1fr;gap:14px}}}}
@media print{{:root{{background:white}} main{{margin:0;max-width:none;padding:0;box-shadow:none}}}}
</style>
</head>
<body><main>{''.join(chunks)}</main></body></html>"""
