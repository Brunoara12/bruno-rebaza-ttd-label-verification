# Phase 3: POST /verify Endpoint

## Summary

Build the single-label verification endpoint. Phase 3 accepts an image plus application data as multipart form data, validates the request, preprocesses the image, calls the mockable vision service, compares extracted fields against the application fields, and returns a full `VerificationResult`.

## Public Interface

- `POST /verify`
  - Request: `multipart/form-data`
  - File field: `image`
  - Text fields: `brand_name`, `class_type`, `abv`, `net_contents`, `producer`, `country_of_origin`, `government_warning`
  - Accepted image types: JPEG, PNG, WEBP
  - Upload limit: `MAX_UPLOAD_BYTES`, default `10485760`

## Behavior

- Valid requests return `200` with the existing `VerificationResult` shape: ordered per-field results, expected/found values, field status, field reason code, `overall_verdict`, and `latency_ms`.
- Failed government-warning matches preserve the extracted warning text in `found` for human review.
- Request latency is measured from endpoint entry through validation, preprocessing, extraction, comparison, and response shaping.
- `latency_ms` is returned in the response body and `X-Verification-Latency-ms` header.
- Verification completion is logged with latency, verdict, failed fields, and whether the 5-second single-label SLA was exceeded.
- Model timeouts return `200 NEEDS_REVIEW` with all fields failed using `MODEL_TIMEOUT`, not `504`.
- Model parse failures return `200 NEEDS_REVIEW` with all fields failed using `PARSE_ERROR`.

## Error Handling

- Missing image or required field: `422` with a readable validation envelope.
- Blank required text field: `422`.
- Unsupported file type: `422`.
- Oversized upload: `413`.
- Empty image file: `400`.
- Corrupt or unreadable image: `400`.
- Vision provider failure: `502`.
- Unexpected server failure: `500`.
- Error responses use `error.code`, `error.message`, and optional `error.fields`; stack traces and raw exception details are not returned to the client.

## Exit Check

- Endpoint tests use mocked `VisionService`; no network or API key is required.
- Tests cover success, expected/found values, warning text surfacing, validation errors, bad file input, timeout/parse result shaping, provider/unexpected failures, CORS, latency header, and SLA logging.
- Full backend test suite passes with `uv run pytest`.
