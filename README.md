# TTB Label Verification

TTB Label Verification is a proof-of-concept application for checking beverage alcohol labels against structured compliance requirements. Phase 0 establishes the deployable foundation: a FastAPI backend health endpoint and a Vite React frontend that verifies connectivity to that backend.

## Status

Phase 0 is complete.

- Backend health endpoint is implemented at `GET /health`.
- Frontend is deployed and displays backend connectivity status.
- Backend and frontend are deployed separately to match the planned proof-of-concept architecture.

## Deployed URLs

- Frontend: https://ttd-label-verification.vercel.app/
- Backend: https://bruno-rebaza-ttd-label-verification.onrender.com
- Backend health: https://bruno-rebaza-ttd-label-verification.onrender.com/health

## Tech Stack

- Backend: Python 3.12, FastAPI, Uvicorn
- Frontend: React, Vite
- Package management: uv for Python, npm for frontend assets
- Deployment: Render for backend, Vercel for frontend
- Data storage: none for Phase 0

## Local Development

Run the backend from the repo root:

```bash
uv sync --python 3.12
uv run uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000
```

Open `http://localhost:8000/health`.

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

Build the frontend from `frontend`:

```bash
npm run build
```

## Environment Variables

Backend:

```text
APP_ENV=production
CORS_ALLOWED_ORIGINS=https://ttd-label-verification.vercel.app
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
