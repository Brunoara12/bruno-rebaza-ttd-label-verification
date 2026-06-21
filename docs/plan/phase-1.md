# Phase 1: Data Models + Comparison Engine

## Summary

Build the comparison layer with no AI and no I/O. Phase 1 is pure Python over typed data so every rule is unit-testable without the vision model, frontend, API endpoint wiring, or database.

## Key Changes

- Backend models live in `backend/app/schemas.py`.
- Comparison rules live in `backend/app/comparison.py`.
- Tests live in `tests/test_comparison.py`.
- Fuzzy comparisons use RapidFuzz when installed, with a local no-network fallback for bare development environments.
- No API keys, model calls, image processing, frontend changes, or persistence are included in this phase.

## Public Interface

- `ApplicationData`: required application fields for brand name, class/type, ABV, net contents, producer, country of origin, and government warning.
- `ExtractedLabel`: nullable extracted label fields plus optional raw text and bounded extraction confidence.
- `FieldResult`: per-field PASS/FAIL result with match type, expected value, found value, and reason code.
- `VerificationResult`: ordered field results, overall verdict, and latency.
- `compare_label(application, extracted, latency_ms=0)`: returns `APPROVED` only when every field passes; any failed field returns `NEEDS_REVIEW`.

## Comparison Rules

- Brand name, class/type, and producer: normalized fuzzy match using lowercase, punctuation removal, whitespace collapse, and token-sort ratio threshold of 90.
- Country of origin: normalize known synonyms such as `USA` and `United States` before fuzzy comparison with threshold of 95.
- ABV: parse numeric percentage from formats such as `45%`, `45`, and `45% Alc./Vol. (90 Proof)`; pass within 0.1 percentage points.
- Net contents: parse compact or spaced units such as `750 mL` and `750ml`; convert supported units to mL and pass within 1 mL.
- Government warning: collapse whitespace only, preserve case and punctuation, and compare exactly. Failed warning comparisons must return the extracted text in `found`.

## Exit Check

- `tests/test_comparison.py` covers the requested scenarios:
  - case-only brand difference passes
  - `45%` vs `45% Alc./Vol. (90 Proof)` passes
  - `750 mL` vs `750ml` passes
  - `USA` vs `United States` passes
  - title-case government warning fails
  - warning missing the colon fails
  - correct all-caps warning passes
  - misread warning returns extracted text
- `python -m compileall backend tests` passes.
- Full pytest verification should be run with the project environment once `uv` and test dependencies are available.
