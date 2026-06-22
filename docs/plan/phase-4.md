# Phase 4: Frontend Single-Label Flow

## Summary

Build the single-label verification screen for a non-technical user who should be able to upload one label image, enter the expected label information, and understand the verdict without instructions. The page posts to the deployed `/verify` endpoint and renders a prominent verdict plus per-field PASS/FAIL results.

## Public Interface

- Frontend environment:
  - `VITE_API_BASE_URL` points to the backend base URL.
  - If unset, the frontend defaults to the deployed Render backend.
- API call:
  - `POST /verify`
  - Request type: `multipart/form-data`
  - File field: `image`
  - Text fields: `brand_name`, `class_type`, `abv`, `net_contents`, `producer`, `country_of_origin`, `government_warning`
  - Browser sets the multipart `Content-Type`; the frontend does not set it manually.

## Behavior

- The first screen is the working flow, not a landing page or health check.
- The image picker accepts JPEG, PNG, and WEBP and shows the selected filename plus an image preview.
- The seven expected fields use plain labels:
  - Brand Name
  - Type of Product
  - Alcohol %
  - Bottle Size
  - Producer
  - Country
  - Government Warning
- The Government Warning field is prefilled with the canonical warning and remains editable.
- The primary action is a large `Check Label` button, with a sticky mobile action for long forms.
- While submitting, the UI disables duplicate submits and shows `Checking...`.
- Successful responses show a large `APPROVED` or `NEEDS REVIEW` verdict.
- Failed fields are summarized immediately as a compact list of field names.
- All seven field results are displayed with text PASS/FAIL badges, plain-English reasons, and expected-vs-found values for failures.

## Error Handling

- Client-side missing image and missing field errors are shown before the API call.
- Backend error envelopes render as plain-English top-level and field-level messages.
- Raw JSON, stack traces, backend codes, and technical exception text are not shown to the user.
- Network/backend availability failures show: `The label checker is not available right now. Please try again.`

## Exit Check

- `npm run build` passes from `frontend`.
- Existing backend tests still pass with `uv run pytest`.
- On the live frontend URL, a user can upload an image plus expected data, submit it to the deployed backend, and see the verdict plus per-field results.
