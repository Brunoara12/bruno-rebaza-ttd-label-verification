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
- Build a high-contrast React form for one label image plus the seven expected fields. Post `multipart/form-data` to `/verify`, show readable loading/errors, and render a prominent `APPROVED` / `NEEDS REVIEW` verdict with per-field PASS/FAIL and expected-vs-found details.

5. Batch support
- Backend: accept multi-pair uploads at `POST /verify/batch`; process items concurrently with a bounded worker pool (`BATCH_WORKER_CONCURRENCY`, default 3) and cap batch size (`BATCH_MAX_ITEMS`, default 10).
- Isolate per-item failures: one bad label/image/model result does not fail the whole batch. Completed items return `VerificationResult`; item errors count as needs review in the batch summary.
- Frontend: batch upload UI, delayed indeterminate progress indicator, summary counts, and drill-down for each individual result.
- Acceptance note: MVP is not complete until batch upload works end-to-end with 3+ labels, correct passed / needs-review / total counts, and individually viewable results.

6. Robustness & performance
- Tune image preprocessing and prompt/output budget only after measuring. Default target: `VISION_MAX_IMAGE_EDGE_PX=1280`, `VISION_JPEG_QUALITY=76`, `VISION_TIMEOUT_SECONDS=4`.
- Keep the single-label endpoint under 5 seconds by returning normal `NEEDS_REVIEW` timeout results before the SLA wall.
- Harden validation and poor-image behavior so user-fixable issues return readable errors and imperfect but readable images return field-level review results.
- Run an accessibility pass on validation, focus, contrast, tap targets, motion, and small-screen layout.
- Acceptance note: Phase 6 is not complete until the deployed checklist runner demonstrates valid label, mismatches, case-only, ABV/units normalization, missing/wrong-caps/correct warning, imperfect image, wrong file type, empty submit, batch summary, and single-label speed under 5 seconds.

7. Deploy verify end-to-end + README
- Deploy frontend and backend; run end-to-end verification against production model endpoint.
- Update `README.md` with setup/run instructions, deployed URLs, public repo, approach, tools, assumptions, limitations, and final verification commands.
- Run the final submission audit: no tracked `.env` files, no obvious hardcoded secrets in current tracked files or git history, backend health passes, live single-label and batch flows work, warning exact-match behavior is verified, imperfect-image behavior returns a normal reviewable result, and the deployed benchmark stays under the 5-second single-label SLA.
- Acceptance note: Phase 7 is not complete until `docs/plan/phase-7.md` records the audit results and live end-to-end evidence.

---

Each phase should include unit tests for the comparison logic and a small integration test for the endpoint once wired. Keep vision calls mockable to avoid incurring provider costs during CI.


