# Phase 8: Backend Configuration and API Refactor

## Summary

This phase hardens runtime configuration and decomposes the backend API without changing the public verification contract.

## Key Changes

- Use `pydantic-settings` for environment and dotenv configuration with positive limits, bounded JPEG quality, CSV CORS validation, and conditional OpenAI credentials.
- Validate `VISION_MODEL` with OpenAI once at worker startup; mock mode remains network-free.
- Make extraction confidence nullable, derive the provider response schema from `ExtractedLabel`, and remove the duplicate extraction payload model.
- Split API composition, routes, errors, validation, verification, and batch orchestration into focused modules with shared exceptions.

## Verification

- Configuration tests cover invalid ranges, malformed values, non-finite timeout values, provider normalization, CORS parsing, and OpenAI key requirements.
- Startup tests cover mock isolation, one OpenAI model lookup, and startup failure on model validation errors.
- Existing endpoint, timeout, batch, CORS, and image-preprocessing tests remain regression coverage for the preserved API contract.

## Risks

- An OpenAI outage, authentication failure, or inaccessible model prevents an OpenAI-configured worker from starting by design.
- Model lookup occurs once per worker startup and is not part of the five-second request SLA.
