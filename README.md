# Scientific Document Translator

A GitHub-ready MVP for translating scientific and technical documents while preserving equations, figures, symbols, numbers, units, citations, URLs, and structured tables.

The core rule is **parse -> protect -> translate -> validate -> reconstruct**. High-risk scientific content is never treated as ordinary prose.

## Current capabilities

- FastAPI upload/job/download API.
- Web UI + installable PWA for desktop, Android, and iOS browsers.
- Flutter client source for native Android/iOS.
- MinerU adapter for PDF, images, DOCX, PPTX, and XLSX.
- Fallback parsing for TXT/Markdown, PDF text layers, and DOCX.
- Immutable equation blocks with reuse of MinerU formula crops when available.
- Exact placeholder protection for inline/display LaTeX, Greek/math symbols, scientific numbers, units, DOI values, URLs, and numeric citations.
- Fail-closed validation: if a protected token is changed, duplicated, or lost, that translated block is rejected and the source block is restored.
- HTML table translation without destroying nested `<sup>`, `<sub>`, `<em>`, and similar markup.
- Figure/table captions and footnotes retained; code/algorithm bodies stay immutable while captions can be translated.
- Optional per-document terminology glossary.
- Standard translated output plus bilingual source/target output.
- HTML, bilingual HTML, Markdown, JSON, PDF, and bilingual PDF export.
- API responses expose download URLs, not private server filesystem paths.

## Important limitation

The implemented layout mode is **Scientific Preserve**: it reconstructs a clean translated document in reading order. Pixel-identical placement over the original PDF page is not implemented yet. That is planned as `Original Layout` mode because translation expansion makes exact page geometry a separate layout problem.

When MinerU is unavailable, fallback PDF/DOCX parsing is deliberately marked as degraded because equations, drawings, and rich layout may not be reconstructed reliably.

## 1. Backend quick start

Python 3.10-3.12 is recommended when MinerU is also installed.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
cp .env.example .env
```

Edit `.env` and configure an OpenAI-compatible Chat Completions translation endpoint:

```env
TRANSLATOR_MODE=openai_compatible
LLM_BASE_URL=https://your-provider.example/v1
LLM_API_KEY=YOUR_KEY
LLM_MODEL=YOUR_TRANSLATION_MODEL
ALLOW_PASSTHROUGH_WITHOUT_KEY=false
```

`.env` is loaded automatically by the backend.

Start the application:

```bash
make dev
```

Open:

```text
http://localhost:8000
```

Health/capability check:

```text
GET /api/v1/health
```

## 2. MinerU (strongly recommended for scientific PDF)

MinerU is intentionally separate from the base requirements because it is large and hardware-dependent.

```bash
pip install -r backend/requirements-mineru.txt
```

The adapter calls:

```bash
mineru -p INPUT -o OUTPUT -b pipeline
```

`pipeline` is the CPU-compatible backend. Change `MINERU_BACKEND` in `.env` if your deployment uses another supported MinerU backend.

## 3. Create a translation job

```bash
curl -X POST http://localhost:8000/api/v1/jobs \
  -F "file=@paper.pdf" \
  -F "source_language=auto" \
  -F "target_language=vi" \
  -F 'glossary_json={"wave function":"hàm sóng","eigenvalue":"trị riêng"}'
```

Poll status:

```bash
curl http://localhost:8000/api/v1/jobs/JOB_ID
```

A completed job returns output URLs such as:

```json
{
  "outputs": {
    "pdf": "/api/v1/jobs/JOB_ID/download/pdf",
    "bilingual_pdf": "/api/v1/jobs/JOB_ID/download/bilingual_pdf",
    "html": "/api/v1/jobs/JOB_ID/download/html",
    "bilingual": "/api/v1/jobs/JOB_ID/download/bilingual",
    "md": "/api/v1/jobs/JOB_ID/download/md",
    "json": "/api/v1/jobs/JOB_ID/download/json"
  }
}
```

Language values accept common BCP-47-style codes such as `en`, `vi`, `ja`, `de`, `zh-Hant`, etc. `source_language=auto` enables source auto-detection at the translation-provider level.

## 4. Android / iOS

### Fastest option: PWA

Run/deploy the backend and open it in Chrome/Safari. The web interface is installable to the home screen and uses the same API.

### Native Flutter client

`mobile/lib/main.dart` contains the Android/iOS client. On a machine with Flutter installed:

```bash
./scripts/bootstrap_mobile.sh
cd mobile
flutter run
```

The bootstrap script generates the Android and iOS platform shells while retaining the repository's Dart client and package manifest.

Android emulator default API address:

```text
http://10.0.2.2:8000
```

For physical Android/iOS devices, use a reachable LAN address during development or an HTTPS deployment in production.

## 5. Tests

```bash
make test
```

The test suite covers scientific placeholder protection, tamper rejection, numeric/symbol validation, nested scientific table markup, public job URLs, and bilingual rendering.

## 6. Docker

```bash
cp .env.example .env
# configure LLM_* values
docker compose up --build
```

The base image is intentionally lean and does not bundle MinerU models. For serious scientific PDF use, install/run MinerU in the deployment environment or point the project at a dedicated parsing service in a later production architecture.

## Privacy and deployment note

Uploaded documents may contain unpublished research or confidential material. Text sent for translation is transmitted to the configured LLM provider. Before public deployment, add authentication, user isolation, retention/cleanup rules, malware scanning, encrypted/object storage, and a durable task queue. Do not expose this MVP directly to the public internet as a multi-user service without those controls.

## Roadmap

- Original Layout mode using MinerU page geometry/bounding boxes.
- Persistent Redis/PostgreSQL job queue instead of in-memory jobs.
- Translation memory and persisted glossary management.
- Rich DOCX reconstruction with styles and embedded media.
- Chemical-formula-specific protection/validation.
- Native Share Extension / Android share-target integration.
- Authentication, quotas, encrypted temporary storage, and automatic retention cleanup.
- Parser sandboxing and production object storage.
