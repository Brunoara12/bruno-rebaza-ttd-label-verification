# Phase 6: Hardening, Performance, and Accessibility

## Summary

Phase 6 hardens the existing proof-of-concept without adding product features. It focuses on the full brief checklist, the single-label 5-second SLA, poor-image graceful degradation, plain validation errors, and accessibility for a non-technical older user.

## Key Changes

- Tune default preprocessing to `VISION_MAX_IMAGE_EDGE_PX=1280` and `VISION_JPEG_QUALITY=76` to reduce model payload while preserving label readability.
- Keep `VISION_TIMEOUT_SECONDS=4`, and add an endpoint-level timeout guard so `/verify` can still return `200 NEEDS_REVIEW` with `MODEL_TIMEOUT` before the 5-second SLA wall.
- Compact the extraction prompt and reduce maximum output tokens while preserving the no-guessing, partial-image, non-label, and exact government-warning instructions.
- Add `scripts/benchmark_verification.py` to run the Phase 6 checklist and latency benchmark against local or deployed backend URLs.
- Strengthen frontend validation and accessibility: file-size validation, invalid state on image inputs, busy state on forms, focusable result panels, large interactive targets, and reduced-motion progress behavior.

## Checklist Coverage

- Valid label: endpoint returns `APPROVED`, all fields `PASS`, and latency body/header is present.
- Mismatches: changed expected fields return `NEEDS_REVIEW` with field-level failures.
- Case-only: fuzzy fields remain case-insensitive while government warning remains case-sensitive.
- ABV and units: comparison tests cover percent/proof and mL/L/cL/fl oz normalization.
- Government warning: correct warning passes; missing warning and wrong-caps warning fail and surface the extracted value when present.
- Imperfect image: poor but decodable images return a normal verification result instead of an unhandled error.
- Wrong file type and empty submit: readable validation errors, no stack traces.
- Batch summary: mixed batch results preserve item order and return correct summary counts.
- Single-label speed: deployed benchmark reports p50, p95, max, and all samples must stay under 5000 ms.

## Measurement Targets

- Single-label deployed `/verify`: p50 <= 3000 ms, p95 <= 4500 ms, max < 5000 ms.
- Non-model overhead: p95 <= 350 ms in local benchmark observations.
- Preprocessed sample payloads: max target <= 250 KB unless extraction quality regresses.
- Timeout path: simulated model timeout returns `200 NEEDS_REVIEW` with field-level `MODEL_TIMEOUT`.
- Accessibility: WCAG AA text contrast, visible focus, >= 44px touch targets, and no clipped text at 320px width.

## Tests

- `uv run pytest`
- `npm run build` from `frontend`
- `python scripts/benchmark_verification.py --base-url https://bruno-rebaza-ttd-label-verification.onrender.com --repeats 3`

## Risks

- Real-model benchmarks depend on provider and network latency, so report local/deployed numbers separately.
- Faster image compression or prompt changes must not create false approvals, especially for the government warning.
- Live deployment must use environment variables only; no real API keys should be committed or printed.
