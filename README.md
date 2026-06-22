# TTB Label Verification

TTB Label Verification is a proof-of-concept application for checking beverage alcohol labels against structured compliance requirements. Phase 0 established the deployable foundation, Phase 1 added the typed data models plus a pure comparison engine, Phase 2 added a mockable vision extraction service, Phase 3 wires the single-label verification API, Phase 4 adds the single-label frontend flow, and Phase 5 adds batch verification.

## Status

| Phase | Status | Notes |
| --- | --- | --- |
| Phase 0 | Done | Repo scaffold, deploy skeleton, and health endpoint. |
| Phase 1 | Done | Typed data models and pure comparison engine. |
| Phase 2 | Done | Mockable vision extraction service and image preprocessing. |
| Phase 3 | Done | `POST /verify` single-label API. |
| Phase 4 | Done | Single-label frontend flow with verdict and per-field results. |
| Phase 5 | Done | Batch endpoint and frontend batch view. |
| Phase 6 | Upcoming | Robustness and performance. |
| Phase 7 | Upcoming | End-to-end deploy verification and README polish. |

Current focus: batch support is implemented locally; the next planned step is robustness, performance, and deployed end-to-end verification.

## Deployed URLs

- Frontend: https://ttd-label-verification.vercel.app/
- Backend: https://bruno-rebaza-ttd-label-verification.onrender.com
- Backend health: https://bruno-rebaza-ttd-label-verification.onrender.com/health

## Tech Stack

- Backend: Python 3.12, FastAPI, Uvicorn, Pydantic, RapidFuzz, Pillow, OpenAI SDK
- Frontend: React, Vite
- Package management: uv for Python, npm for frontend assets
- Deployment: Render for backend, Vercel for frontend
- Data storage: none; the proof-of-concept remains stateless / in-memory

## Local Development

Run the backend from the repo root:

```bash
uv sync --python 3.12
uv run uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000
```

Open `http://localhost:8000/health`.

The backend loads the repo-root `.env` file automatically for local development. To use the real vision model locally, set `VISION_PROVIDER=openai` and `OPENAI_API_KEY` there, then restart the backend.

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

Run the frontend from `frontend`:

```bash
npm install
npm run dev -- --host 0.0.0.0 --port 5173 --strictPort
```

Open `http://localhost:5173`.

Set `VITE_API_BASE_URL=http://localhost:8000` in `frontend/.env` to point the local frontend at your local backend. If the variable is not set, the frontend defaults to the deployed Render backend.

## Tests And Builds

Run backend tests from the repo root:

```bash
uv run pytest
```

Run one real vision extraction sample from the repo root:

```bash
uv run python scripts/extract_label_sample.py labels/Clover-Hill-wine-back-label.png
```

This sample script requires `OPENAI_API_KEY` to be set.

Build the frontend from `frontend`:

```bash
npm run build
```

## Environment Variables

Backend:

```text
APP_ENV=production
CORS_ALLOWED_ORIGINS=https://ttd-label-verification.vercel.app
VISION_PROVIDER=openai
VISION_MODEL=gpt-5.4-mini
VISION_TIMEOUT_SECONDS=4
VISION_MAX_IMAGE_EDGE_PX=1600
VISION_JPEG_QUALITY=82
MAX_UPLOAD_BYTES=10485760
BATCH_MAX_ITEMS=10
BATCH_WORKER_CONCURRENCY=3
OPENAI_API_KEY=<set in host environment only>
```

Frontend:

```text
VITE_API_BASE_URL=https://bruno-rebaza-ttd-label-verification.onrender.com
```

For local development examples, see `.env.example` and `frontend/.env.example`.

## Deployment

The backend is deployed on Render from the repo root.

- Build command: `uv sync --frozen --no-dev && uv cache prune --ci`
- Start command: `uv run --no-sync uvicorn backend.app.main:app --host 0.0.0.0 --port $PORT`

The frontend is deployed on Vercel from the `frontend` project root.

- Build command: `npm run build`
- Output directory: `dist`

## Secrets

Never commit real secrets. Use `.env.example` files for variable names only, and set real values in Render or Vercel environment variables.
