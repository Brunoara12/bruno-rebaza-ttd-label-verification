# Phase 2: Vision Service

## Summary

Build the image-extraction layer as an isolated, mockable backend service. Phase 2 adds image preprocessing, an OpenAI vision adapter with strict structured output, defensive response validation, and a deterministic mock service for tests and local development.

## Key Changes

- Vision code lives in `backend/app/vision_service.py`.
- Image preprocessing lives in `backend/app/image_preprocess.py`.
- The real adapter uses OpenAI Responses API with `VISION_MODEL=gpt-5.4-mini` by default.
- The default local provider is `VISION_PROVIDER=mock`, so tests and Phase 3 endpoint wiring do not need `OPENAI_API_KEY`.
- The sample runner lives at `scripts/extract_label_sample.py` and calls the real OpenAI adapter against one local image path.

## Behavior

- Preprocess valid images by applying EXIF orientation, converting to RGB, downscaling the longest edge, and JPEG re-encoding before model submission.
- Request strict JSON Schema output for the existing `ExtractedLabel` shape: seven nullable label fields, nullable `raw_text`, and bounded `extraction_confidence`.
- The extraction prompt tells the model to leave unknown values null, return partial data for blurry/angled/glare images, and copy government-warning text verbatim without correction or canonical substitution.
- Valid non-label images return null label fields, optional visible `raw_text`, and `extraction_confidence=0.0`.
- Provider timeouts raise `VisionTimeoutError`; malformed JSON, refusal, incomplete output, or schema-invalid output raises `VisionParseError`.

## Exit Check

- Unit tests use generated images, fake OpenAI clients, and `MockVisionService`; they do not hit the network or require an API key.
- A readable real sample can be checked manually with:

```bash
uv run python scripts/extract_label_sample.py samples/acme-reserve-bourbon-label.jpg
```

Set `OPENAI_API_KEY` and optionally `VISION_PROVIDER=openai` before running the script.
