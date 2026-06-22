# TTB Label Verification

TTB Label Verification is a proof-of-concept application for checking beverage alcohol labels against structured compliance requirements. Phase 0 established the deployable foundation, Phase 1 added the typed data models plus a pure comparison engine, Phase 2 added a mockable vision extraction service, and Phase 3 wires the single-label verification API.

## Status

Phase 0, Phase 1, Phase 2, and Phase 3 are complete.

- Backend health endpoint is implemented at `GET /health`.
- Frontend is deployed and displays backend connectivity status.
- Backend and frontend are deployed separately to match the planned proof-of-concept architecture.
- Pydantic models define the application data, extracted label, field result, and verification result contracts.
- The comparison engine is pure Python: fuzzy brand/class/producer matching, country synonyms, ABV normalization, net-content unit normalization, and exact case-sensitive government-warning comparison.
- The VisionService adds image preprocessing, strict structured extraction, defensive parsing, and a mock provider for tests and local development.
- `POST /verify` accepts a label image plus application data as multipart form data and returns a full `VerificationResult` with per-field expected/found values, verdict, latency, and readable errors.

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

Submit one label verification request:

```bash
curl -X POST http://localhost:8000/verify \
  -F "image=@labels/sample-label.png;type=image/png" \
  -F "brand_name=Acme Reserve" \
  -F "class_type=Straight Bourbon Whiskey" \
  -F "abv=45%" \
  -F "net_contents=750 mL" \
  -F "producer=Acme Distilling Co." \
  -F "country_of_origin=United States" \
  -F "government_warning=GOVERNMENT WARNING: (1) ACCORDING TO THE SURGEON GENERAL, WOMEN SHOULD NOT DRINK ALCOHOLIC BEVERAGES DURING PREGNANCY BECAUSE OF THE RISK OF BIRTH DEFECTS. (2) CONSUMPTION OF ALCOHOLIC BEVERAGES IMPAIRS YOUR ABILITY TO DRIVE A CAR OR OPERATE MACHINERY, AND MAY CAUSE HEALTH PROBLEMS."
```

The response is a `VerificationResult` with `results`, `overall_verdict`, and `latency_ms`. The same latency is also returned in `X-Verification-Latency-ms`.

Run the frontend from `frontend`:

```bash
npm install
npm run dev -- --host 0.0.0.0 --port 5173 --strictPort
```

Open `http://localhost:5173`.

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
