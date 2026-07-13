# Phase 9: Frontend Form Validation and Upload UX

## Summary

This phase improves verification-form guidance and safeguards without changing the verification API or backend MIME rules.

## Key Changes

- Add clear government-warning guidance that punctuation and spacing must match exactly.
- Constrain ABV to a 0–100 numeric input with 0.1 increments and validate net contents as a positive numeric quantity plus a supported unit.
- Let the file picker select any image type while retaining backend MIME validation as the source of truth.
- Show cold-start reassurance after five seconds for single and batch requests, with cleaned-up timers.
- Confirm removal only for batch items with an image or user-entered values; empty items remove immediately.

## Verification

- Frontend unit and component tests cover validation, image-picker acceptance, delayed guidance, and dialog keyboard behavior.
- Run `npm.cmd run test`, `npm.cmd run lint`, `npm.cmd run build`, and `uv run pytest`.

## Limitations

- The guidance describes literal warning matching, but existing frontend and backend submission normalization trims leading and trailing whitespace. Changing that comparison contract is outside this frontend phase.
- A free-tier cold start can exceed the five-second warmed-request target; the message explains that exceptional wait rather than changing backend latency behavior.
