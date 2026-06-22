# TTB Label Verification

TTB Label Verification is a proof-of-concept application for checking beverage alcohol labels against structured compliance requirements. A user uploads a label image, enters the expected application data, and receives field-level PASS/FAIL results plus an overall `APPROVED` or `NEEDS_REVIEW` verdict.

## Final Submission Links

- Public repo: https://github.com/AI-Native-2026-06-22-FedStack/bruno-rebaza-ttd-label-verification
- Live frontend: https://ttd-label-verification.vercel.app/
- Backend API: https://bruno-rebaza-ttd-label-verification.onrender.com
- Backend health: https://bruno-rebaza-ttd-label-verification.onrender.com/health

## What It Does

- Verifies a single label image against seven expected fields.
- Supports batch upload with item-level results and summary counts.
- Shows per-field expected-vs-found details so a human can resolve `NEEDS_REVIEW` cases.
- Treats the government warning as an exact, case-sensitive match after whitespace collapse.
- Uses fuzzy, normalized, numeric, and unit-aware comparison for all other fields.
- Runs statelessly with no database or persisted user data.

## Approach

The React frontend posts `multipart/form-data` to a FastAPI backend. The backend validates the request, preprocesses the image, calls a mockable vision-model adapter for structured extraction, then compares extracted fields against the submitted application data.

The comparison engine is isolated as pure Python logic so matching rules can be tested without model calls. The vision service is also isolated so local tests can use a mock provider while deployed verification uses the real model through environment-only credentials.

## Tech Stack

- Backend: Python 3.12, FastAPI, Uvicorn, Pydantic, RapidFuzz, Pillow, OpenAI SDK
- Frontend: React, Vite
- Package management: uv for Python, npm for frontend assets
- Deployment: Render for backend, Vercel for frontend
- Storage: none; the app is stateless / in-memory

## Local Setup

Run the backend from the repo root:

```bash
uv sync --python 3.12
uv run uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000
```

Open `http://localhost:8000/health`.

The backend loads the repo-root `.env` file automatically for local development. Start from `.env.example`; to use the real vision model locally, set `VISION_PROVIDER=openai` and `OPENAI_API_KEY` in your local `.env`, then restart the backend.

Run the frontend from `frontend`:

```bash
npm install
npm run dev -- --host 0.0.0.0 --port 5173 --strictPort
```

Open `http://localhost:5173`.

Set `VITE_API_BASE_URL=http://localhost:8000` in `frontend/.env` to point the local frontend at your local backend. If the variable is not set, the frontend defaults to the deployed Render backend.

## API Examples

Submit one label verification request:

```bash
curl -X POST http://localhost:8000/verify \
  -F "image=@labels/Clover-Hill-wine-back-label.png;type=image/png" \
  -F "brand_name=Acme Reserve" \
  -F "class_type=Straight Bourbon Whiskey" \
  -F "abv=45%" \
  -F "net_contents=750 mL" \
  -F "producer=Acme Distilling Co." \
  -F "country_of_origin=United States" \
  -F "government_warning=GOVERNMENT WARNING: (1) ACCORDING TO THE SURGEON GENERAL, WOMEN SHOULD NOT DRINK ALCOHOLIC BEVERAGES DURING PREGNANCY BECAUSE OF THE RISK OF BIRTH DEFECTS. (2) CONSUMPTION OF ALCOHOLIC BEVERAGES IMPAIRS YOUR ABILITY TO DRIVE A CAR OR OPERATE MACHINERY, AND MAY CAUSE HEALTH PROBLEMS."
```

The response is a `VerificationResult` with `results`, `overall_verdict`, and `latency_ms`. The same latency is also returned in `X-Verification-Latency-ms`.

Submit a batch verification request with one `items_json` array and repeated `images` file fields:

```bash
curl -X POST http://localhost:8000/verify/batch \
  -F 'items_json=[{"client_id":"label-1","brand_name":"Acme Reserve","class_type":"Straight Bourbon Whiskey","abv":"45%","net_contents":"750 mL","producer":"Acme Distilling Co.","country_of_origin":"United States","government_warning":"GOVERNMENT WARNING: (1) ACCORDING TO THE SURGEON GENERAL, WOMEN SHOULD NOT DRINK ALCOHOLIC BEVERAGES DURING PREGNANCY BECAUSE OF THE RISK OF BIRTH DEFECTS. (2) CONSUMPTION OF ALCOHOLIC BEVERAGES IMPAIRS YOUR ABILITY TO DRIVE A CAR OR OPERATE MACHINERY, AND MAY CAUSE HEALTH PROBLEMS."}]' \
  -F "images=@labels/Clover-Hill-wine-back-label.png;type=image/png"
```

The response includes `items`, `summary`, and `latency_ms`. One bad item returns an item-level error or needs-review result without failing the whole batch.

## Environment Variables

Backend:

```text
APP_ENV=production
CORS_ALLOWED_ORIGINS=https://ttd-label-verification.vercel.app
VISION_PROVIDER=openai
VISION_MODEL=gpt-5.4-mini
VISION_TIMEOUT_SECONDS=4
VISION_MAX_IMAGE_EDGE_PX=1280
VISION_JPEG_QUALITY=76
MAX_UPLOAD_BYTES=10485760
BATCH_MAX_ITEMS=10
BATCH_WORKER_CONCURRENCY=3
OPENAI_API_KEY=<set in host environment only>
```

Frontend:

```text
VITE_API_BASE_URL=https://bruno-rebaza-ttd-label-verification.onrender.com
```

Only variable names belong in `.env.example` files. Real keys must stay in local or host environment variables and must never be committed.

## Deployment

The backend is deployed on Render from the repo root.

- Build command: `uv sync --frozen --no-dev && uv cache prune --ci`
- Start command: `uv run --no-sync uvicorn backend.app.main:app --host 0.0.0.0 --port $PORT`

The frontend is deployed on Vercel from the `frontend` project root.

- Build command: `npm run build`
- Output directory: `dist`

## Tests And Final Verification

Run backend tests from the repo root:

```bash
uv run pytest
```

Build the frontend from `frontend`:

```bash
npm run build
```

Run the deployed checklist and latency benchmark:

```bash
uv run python scripts/benchmark_verification.py --base-url https://bruno-rebaza-ttd-label-verification.onrender.com --repeats 3
```

Before submission, also open the live frontend and complete one single-label verification plus one batch verification with at least three items. Confirm the deployed backend health URL returns `{"status":"ok"}` and that the benchmark reports `all_passed: true` with single-label max latency under 5000 ms.

## Secret Audit

The repository is configured so `.env` and `frontend/.env` are ignored. The tracked env files should only be `.env.example` and `frontend/.env.example`.

Final audit commands:

```bash
git ls-files .env frontend/.env
git log --all --oneline -- .env frontend/.env
git check-ignore -v .env frontend/.env
git grep -n -I -E "(sk-[A-Za-z0-9_-]{20,}|OPENAI_API_KEY\s*=\s*[^<[:space:]#][^[:space:]#]+|API_KEY\s*=\s*[^<[:space:]#][^[:space:]#]+|SECRET\s*=\s*[^<[:space:]#][^[:space:]#]+|TOKEN\s*=\s*[^<[:space:]#][^[:space:]#]+|PASSWORD\s*=\s*[^<[:space:]#][^[:space:]#]+)"
git log -p --all -G "(sk-[A-Za-z0-9_-]{20,}|OPENAI_API_KEY\s*=\s*[^<[:space:]#][^[:space:]#]+|API_KEY\s*=\s*[^<[:space:]#][^[:space:]#]+|SECRET\s*=\s*[^<[:space:]#][^[:space:]#]+|TOKEN\s*=\s*[^<[:space:]#][^[:space:]#]+|PASSWORD\s*=\s*[^<[:space:]#][^[:space:]#]+)" -- .
```

## Assumptions

- `NEEDS_REVIEW` means a human reviewer should inspect the field-level details.
- Free-tier deployment may have a cold-start delay on the first request.
- The model is expected to return partial/null fields rather than guess when images are poor or incomplete.
- The proof-of-concept prioritizes readable review results over automatic rejection on uncertain extraction.

## Limitations

- This is not a production compliance system.
- There is no login, persistent audit log, database, manual override workflow, or long-term file storage.
- Vision-model latency and quality depend on the provider, image quality, and network conditions.
- Secret scans catch common key patterns and tracked `.env` mistakes, but they do not replace full organization-level secret scanning.
