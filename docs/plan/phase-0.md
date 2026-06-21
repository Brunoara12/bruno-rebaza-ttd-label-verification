# Phase 0: React + FastAPI Deploy Skeleton

## Summary

Build the smallest deployable proof point: a React frontend on Vercel calls a FastAPI backend on Render. No verification features yet. Success means the production frontend URL loads, calls production `/health`, and shows the health response.

## Key Changes

- Backend: Python 3.12, FastAPI, `uv`, `GET /health`.
- Frontend: Vite + React page that calls the backend health endpoint.
- Plans live under `docs/plan/`.
- Secrets are never committed. Only `.env.example` files are tracked.
- CORS is configured by `CORS_ALLOWED_ORIGINS`.

## Public Interface

- `GET /health`
  - Returns `200`.
  - Body: `{"status":"ok","service":"ttb-label-verification-api"}`.

## Deploy Path

- Render hosts the backend from repo root.
- Vercel hosts the frontend from `frontend/`.
- Render must include the exact Vercel production URL in `CORS_ALLOWED_ORIGINS`.
- Vercel must set `VITE_API_BASE_URL` to the Render backend URL.

## Exit Check

- Render `/health` returns the expected JSON.
- Vercel frontend loads and displays that health JSON.

