# IMPLEMENTATION Plan (Build Order)

This file captures the phased execution plan that implements the architecture. Follow this order; each phase is small, testable, and verifiable before moving to the next.

0. Scaffold + secrets + deploy skeleton
- Create repository layout: `backend/`, `frontend/`, `tests/`, `docs/`.
- Add `pyproject.toml` / `requirements.txt` placeholder for FastAPI (Python 3.12).
- Add environment variables template `.env.example` (do NOT check in secrets).
- Deploy a minimal health-check endpoint to chosen host (deploy early to validate CI/deploy).

1. Data models + Comparison Engine (TDD-first)
- Implement Pydantic models in `backend/app/schemas.py`.
- Implement `comparison` module as pure functions with unit tests. Cover fuzzy, numeric, and unit-normalize logic.

2. Vision Service
- Implement `VisionService` interface, OpenAI Responses adapter, and local/mock adapter for development and tests.
- Add image preprocess functions: EXIF orientation, RGB conversion, downscale, JPEG re-encode, and corrupt-image handling.
- Use strict structured JSON output for `ExtractedLabel`; malformed, refused, or incomplete model output maps to typed vision errors.

3. `POST /verify` endpoint
- Wire validation, preprocess, call to vision adapter, and comparison engine. Return `VerificationResult`, including the agreed timeout behavior: model timeouts return `NEEDS_REVIEW` with field-level `MODEL_TIMEOUT` reason codes, not `504`.
- Add request-level latency instrumentation and structured logging. Return `latency_ms` in the body and `X-Verification-Latency-ms` in the response header. Shape validation and server errors with readable messages and no stack traces.

4. Frontend single-label flow
- Build minimal form (React or plain HTML/JS) that posts `multipart/form-data` to `/verify` and shows per-field PASS/FAIL.

5. Batch support
- Backend: accept multi-pair uploads; process items concurrently with a bounded worker pool.
- Frontend: batch upload UI and summary table.
- Acceptance note: MVP is not complete until batch upload works end-to-end with item-level results and summary counts.

6. Robustness & performance
- Add retries, model fallback, deeper monitoring, accessibility improvements.

7. Deploy verify end-to-end + README
- Deploy frontend and backend; run end-to-end verification against production model endpoint.
- Update `README.md` with run and deploy instructions.

---

Each phase should include unit tests for the comparison logic and a small integration test for the endpoint once wired. Keep vision calls mockable to avoid incurring provider costs during CI.


