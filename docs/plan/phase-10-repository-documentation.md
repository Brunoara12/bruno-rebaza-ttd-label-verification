# Phase 10: Repository Organization, Deployment Configuration, and Documentation Evidence

## Summary

Organize architecture and planning records under `docs/`, add reproducible Render and Vercel configuration, and make the submission documentation verifiable from a fresh clone without committing credentials.

## Key Changes

- Move the architecture record to `docs/architecture.md` and remove the duplicated root implementation roadmap; phase documents remain the authoritative implementation history.
- Commit `render.yaml` for the root FastAPI service and `frontend/vercel.json` for the Vite project rooted at `frontend`.
- Add a fictional, deterministic label fixture under `samples/`; use it in the README curl examples and sample extraction command.
- Document every backend setting, secret handling, documented model, AI-assisted workflow, assumptions, limitations, tradeoffs, and performance-evidence procedure.

## Verification

- Run backend tests, frontend production build, JSON/YAML configuration checks, documentation-reference searches, and fresh-clone-style single and batch curl requests against local mock mode.
- Run the deployed benchmark and provider model-list verification only when the hosted service and authorized provider credentials are available. Record observed values and dates; do not infer them from source or prior phase records.

## Execution Evidence

- 2026-07-12: `gpt-5.4-mini` was listed and retrievable through the configured OpenAI account.
- 2026-07-12: deployed benchmark with `--repeats 3` returned `all_passed: true`; nine single-label checklist samples measured p50 3313 ms, p95 4800 ms, and max 4800 ms.

## Risks

- Render and Vercel dashboard settings, the OpenAI credential, live model availability, and deployed latency require external access.
- Vercel's Root Directory is an external project setting and must be `frontend` for `frontend/vercel.json` to apply.
