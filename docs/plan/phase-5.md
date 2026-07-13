# Phase 5: Batch Verification

## Summary

Add end-to-end batch verification for multiple label image plus application-data pairs. Phase 5 keeps the existing single-label flow intact, adds `POST /verify/batch`, processes items concurrently with a bounded async worker pool, returns a batch summary, and adds a frontend batch view with clear progress, summary counts, and drill-down into each individual result.

## Public Interface

- `POST /verify/batch`
  - Request: `multipart/form-data`
  - Form field: `items_json`
    - JSON array of item objects.
    - Each item includes `client_id` plus the seven `ApplicationData` text fields: `brand_name`, `class_type`, `abv`, `net_contents`, `producer`, `country_of_origin`, `government_warning`.
  - File field: `images`
    - Repeated file field, one image per `items_json` item, matched by array order.
    - Accepted image types: JPEG, PNG, WEBP.
  - Limits:
    - Per-image upload limit remains `MAX_UPLOAD_BYTES`.
    - Add `BATCH_MAX_ITEMS`, default `10`.
    - Add `BATCH_WORKER_CONCURRENCY`, default `3`.

- Response: `200`
  - `items: list[BatchItemResult]`
    - `client_id`
    - `index`
    - `filename`
    - `status: "COMPLETED" | "ERROR"`
    - `result: VerificationResult | null`
    - `error: { code, message, fields? } | null`
  - `summary: { passed: int, needs_review: int, total: int }`
  - `latency_ms: int`
  - Header: `X-Batch-Verification-Latency-ms`

## Backend Behavior

- Keep `/verify` behavior unchanged.
- Refactor the single-label orchestration into a shared internal helper so `/verify` and `/verify/batch` use the same validation, preprocessing, model extraction, timeout handling, comparison, latency, and reason-code rules.
- Validate the batch envelope before item processing:
  - Missing or invalid `items_json`: whole request `422`.
  - No items: whole request `422`.
  - More than `BATCH_MAX_ITEMS`: whole request `422`.
  - Image count does not match item count: whole request `422`.
- Process item-specific failures without aborting the batch:
  - Blank fields, unsupported image type, oversized file, empty file, corrupt image, model timeout, parse failure, and provider failure become item-level `ERROR` or `NEEDS_REVIEW` results.
  - Item-level errors count as `needs_review` in the summary.
  - No stack traces, raw exception messages, or provider details are returned.
- Preserve government warning behavior exactly:
  - Case-sensitive exact match after whitespace collapse only.
  - Failed warning fields include the extracted warning text when available.

## Concurrency and 5-Second Budget

- The single-label SLA remains under 5 seconds per label.
- Batch total latency is not guaranteed under 5 seconds for arbitrary batch sizes; it should scale with `ceil(total / BATCH_WORKER_CONCURRENCY)` while each item keeps the existing per-label timeout behavior.
- Use `asyncio.gather` plus an `asyncio.Semaphore` to run multiple item verifications concurrently without unbounded model calls.
- Because the current vision adapter is synchronous, run blocking extraction work in `asyncio.to_thread` so the FastAPI event loop is not blocked.
- Keep model timeout behavior consistent with Phase 3:
  - Model timeouts return item-level `NEEDS_REVIEW` results with field-level `MODEL_TIMEOUT`, not `504`.
- Log batch latency, item count, summary counts, worker concurrency, and whether any individual item exceeded the 5-second SLA.

## Frontend Behavior

- Add a batch view alongside the existing single-label view.
- Use large, plain controls suitable for a non-technical older user:
  - Clear tabs or segmented control: `One Label` and `Batch`.
  - Batch starts with one item and an obvious `Add Label` button.
  - Each item has image picker, filename/preview, the same seven expected fields, and a remove control when more than one item exists.
  - Government Warning is prefilled per item with the canonical warning and remains editable.
- Validate before submit:
  - Every item needs an image.
  - Every item needs all seven text fields.
  - Show field-level errors inside the affected item.
- Submit one multipart request to `/verify/batch`.
- If processing takes more than a short moment, show a prominent progress state:
  - Delay showing the progress panel by about 700 ms to avoid flashing on fast requests.
  - Show an indeterminate progress bar/spinner, elapsed time, and the number of labels being checked.
  - Do not show fake per-item completion counts unless the API later supports streaming progress.
- On success:
  - Show summary counts: passed, needs review, total.
  - Show one drill-down row/card per item with filename, verdict, failed field names, latency, and an expand/collapse detail area.
  - Reuse the existing individual result rendering for completed items where practical.
  - For item errors, show a plain-English needs-review message instead of raw JSON.

## Files To Touch During Execute

- Backend:
  - `backend/app/schemas.py`: add batch summary, item wrapper, and batch response models.
  - `backend/app/config.py`: add `BATCH_MAX_ITEMS` and `BATCH_WORKER_CONCURRENCY`.
  - `backend/app/main.py`: extract shared single-item orchestration and add `POST /verify/batch`.
  - `tests/test_verify_batch_endpoint.py`: add batch endpoint coverage.
  - `tests/test_verify_endpoint.py`: adjust only if the shared helper changes test setup.

- Frontend:
  - `frontend/src/App.jsx`: add single/batch view state.
  - `frontend/src/verification/api.js`: add `verifyBatch`.
  - `frontend/src/verification/form.js`: add batch validation and multipart builder.
  - `frontend/src/verification/constants.js`: add batch defaults.
  - `frontend/src/verification/errors.js`: reuse readable backend error handling for batch-level errors.
  - `frontend/src/components/BatchVerificationForm.jsx`: batch item editing UI.
  - `frontend/src/components/BatchResultView.jsx`: summary plus drill-down.
  - `frontend/src/components/ProgressPanel.jsx`: delayed progress state.
  - `frontend/src/styles.css`: batch layout, progress, and drill-down styles.

- Documentation check during Execute:
  - `docs/architecture.md`: update `BatchResult` shape if the item wrapper is accepted.
  - `docs/plan/phase-5.md`: record any accepted Phase 5 documentation changes.
  - `README.md`: update only if the user-facing run/verification steps change.

## Tests

- Backend tests:
  - Success with multiple valid items returns `200`, ordered `items`, correct `client_id`, and correct summary counts.
  - Mixed approved and needs-review results produce correct summary counts.
  - One corrupt or invalid item does not abort the whole batch.
  - Model timeout for one item returns item-level `NEEDS_REVIEW` with `MODEL_TIMEOUT`.
  - Invalid batch envelope returns readable `422`.
  - Concurrency is bounded by `BATCH_WORKER_CONCURRENCY`.
  - Batch latency header is present.

- Frontend verification:
  - `npm run build` passes.
  - Manual local check can add multiple labels, submit them, see delayed progress on slower mock responses, then see summary and drill-down.
  - Existing single-label flow still works.

## Risks and Decisions

- Matching images to data by array order is simple and reliable for the React client, but API clients must preserve order. The response returns `client_id` and `index` to make mismatches easy to diagnose.
- A single final JSON response cannot provide true per-item live progress. The MVP uses a delayed indeterminate progress indicator. True completed-count progress would require streaming or a job/polling design, which is larger and less aligned with the current stateless proof-of-concept.
- Running the synchronous vision adapter concurrently requires `asyncio.to_thread`. If the adapter or provider client is not thread-safe, the Execute phase should instantiate per worker or add a small adapter-level guard.
- Batch size and concurrency must stay conservative for free-tier hosting and provider rate limits.
- Item-level provider failures may make every item needs-review, but the frontend will still receive a usable summary and drill-down instead of a raw server failure.

## Exit Check

- `uv run pytest` passes.
- `npm run build` passes from `frontend`.
- A user can open the frontend, choose `Batch`, add at least two image/data pairs, submit them, see progress if the request takes more than a moment, and receive passed / needs-review / total summary plus drill-down for each item.
