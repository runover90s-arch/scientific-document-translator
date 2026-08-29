# Architecture

## Pipeline

```text
Upload
  -> parser selection
     -> MinerU structured content (preferred)
     -> safe fallback parser
  -> classify blocks
  -> scientific protection layer
  -> translation provider + document context + optional glossary
  -> integrity validation
  -> structured reconstruction
  -> translated + bilingual outputs
  -> HTML / Markdown / JSON / PDF
```

## Scientific integrity strategy

Natural-language text is translated. High-risk scientific content is either immutable or replaced by exact placeholders before a translation request.

Protected content includes:

- display and inline LaTeX delimiters;
- Greek-variable tokens and mathematical operators;
- Unicode superscript/subscript math tokens;
- scientific numbers and common units;
- DOI values and URLs;
- numeric citations.

Equation blocks emitted by MinerU are immutable. If an equation crop is available, reconstruction reuses the image asset rather than asking the language model to regenerate the formula.

After translation, every placeholder must still occur exactly once. Numeric and mathematical-symbol multisets are compared between source and restored target. A failed block is rejected and restored to the original source text.

## Tables

MinerU tables contain HTML. Translation walks visible text nodes rather than replacing the entire cell string. This preserves nested scientific markup such as `<sup>`, `<sub>`, emphasis, row/column spans, and formula-related structure.

Captions and footnotes surrounding a table are included in the translation fragment so they are not silently dropped.

## Code and algorithms

Code/algorithm bodies are immutable. Natural-language captions are translated independently and validated before reconstruction.

## MinerU adapter

The preferred parser invokes the MinerU CLI and consumes `*_content_list.json` because its current stable schema directly exposes readable blocks, page indices, 0-1000 bounding boxes, image/formula paths, captions, footnotes, and table HTML.

The adapter also records `*_content_list_v2.json` when present. V2 is useful for future page-oriented layout work, but is currently documented as a development structure, so the MVP does not make it a hard dependency.

## Output modes

### Scientific Preserve (implemented)

Reconstructs a clean document in reading order while preserving protected scientific content and available visual assets.

### Bilingual (implemented)

Creates a source/translation comparison view. Equations and figures are shared instead of duplicated where appropriate. On narrow mobile screens the two columns stack vertically.

### Original Layout (planned)

Will use page geometry and bounding boxes to position translated text over/near the original page. Translation expansion means pixel-identical layout cannot be guaranteed for every language pair without font scaling, overflow rules, or reflow.

## Mobile

The web UI is a PWA and works on Android/iOS immediately through a browser/home-screen installation. The `mobile/` client is Flutter so Android and iOS share one codebase and one backend protocol.

Heavy parsing/OCR/translation/rendering remains server-side. Mobile is responsible for file selection, upload, status polling, preview/download, and eventually platform share extensions.

## Current MVP constraints

- Job state is in memory and does not survive server restarts.
- Background work runs in the application process rather than a durable worker queue.
- The fallback PDF parser reads the text layer but is not a replacement for MinerU on complex STEM documents.
- The project currently uses an OpenAI-compatible Chat Completions provider interface rather than a provider-agnostic production gateway.

## Production hardening roadmap

- Redis-backed queue and durable PostgreSQL job state.
- Object storage with expiring signed downloads.
- Authentication, quotas, per-user isolation, and audit logging.
- Encrypted temporary files and automatic retention cleanup.
- Translation-memory persistence and glossary versioning.
- Parser sandboxing and malware scanning for uploads.
- Chemical formula and domain-specific validators.
