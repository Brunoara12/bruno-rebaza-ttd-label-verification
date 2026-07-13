# TTB Label Verification

TTB Label Verification is a proof-of-concept for checking beverage-alcohol label images against structured compliance requirements. A user uploads a label image, enters expected application data, and receives field-level PASS/FAIL results plus an overall `APPROVED` or `NEEDS_REVIEW` verdict.

## Final Submission Links

- Public repo: https://github.com/Brunoara12/bruno-rebaza-ttd-label-verification
- Live frontend: https://bruno-rebaza-ttd-label-verification.vercel.app
- Backend API: https://bruno-rebaza-ttd-label-verification-ej1c.onrender.com/
- Backend health: https://bruno-rebaza-ttd-label-verification-ej1c.onrender.com/health

## What It Does

- Verifies one label against seven expected fields.
- Supports batch upload with item-level results and summary counts.
- Shows expected-versus-found details so a human can resolve `NEEDS_REVIEW` cases.
- Compares the government warning exactly and case-sensitively after whitespace collapse; all other fields use normalized or fuzzy comparison.
- Runs statelessly with no database or persisted user data.

## Approach

The React frontend sends `multipart/form-data` to a FastAPI backend. The backend validates input, preprocesses the image, extracts structured label data through a mockable vision-provider adapter, and compares the extraction against submitted application data. The comparison engine is pure Python so its rules can be tested without a model call.

### AI-Assisted Development

Codex was used under human direction to inspect the repository, propose and review phase plans, and draft or modify implementation and documentation work. The human owner supplied project requirements, made product and deployment decisions, controls credentials and host accounts, and performs final acceptance and live verification. This is workflow-level attribution, not a file-by-file authorship audit.

The working cadence is:

1. **PLAN** — Codex proposes an approach, affected files, and risks without writing code.
2. **REVIEW** — the plan is checked against the requirements and edge cases before approval.
3. **EXECUTE** — Codex implements only the approved phase, runs the relevant checks, and reports how to verify it.

## Tech Stack

- Backend: Python 3.12, FastAPI, Uvicorn, Pydantic, RapidFuzz, Pillow, OpenAI SDK
- Frontend: React, Vite
- Package management: uv for Python, npm for frontend assets
- Deployment: Render backend and Vercel static frontend
- Architecture record: [docs/architecture.md](docs/architecture.md)

## Local Setup

Run the backend from the repository root:

```bash
uv sync --python 3.12
uv run uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000
```

Open `http://localhost:8000/health`.

The backend loads the root `.env` file for local development. Start with `.env.example`. The safe default is `VISION_PROVIDER=mock`; to use OpenAI locally, set `VISION_PROVIDER=openai` and `OPENAI_API_KEY` in your untracked `.env`, then restart the backend.

Run the frontend from `frontend`:

```bash
npm ci
npm run dev -- --host 0.0.0.0 --port 5173 --strictPort
```

Open `http://localhost:5173`. Set `VITE_API_BASE_URL=http://localhost:8000` in untracked `frontend/.env` to point at the local backend. If it is absent, the frontend uses the deployed Render backend.

## Fresh-Clone API Examples

The fictional fixture at `samples/acme-reserve-bourbon-label.jpg` is committed to the repository. After starting the local backend in its default mock mode, run these Bash or Git Bash commands from the repository root. They use the same field values as the fixture, benchmark, and mock provider.

Submit one label:

```bash
curl -X POST http://localhost:8000/verify \
  -F "image=@samples/acme-reserve-bourbon-label.jpg;type=image/jpeg" \
  -F "brand_name=Acme Reserve" \
  -F "class_type=Straight Bourbon Whiskey" \
  -F "abv=45%" \
  -F "net_contents=750 mL" \
  -F "producer=Acme Distilling Co." \
  -F "country_of_origin=United States" \
  -F "government_warning=GOVERNMENT WARNING: (1) ACCORDING TO THE SURGEON GENERAL, WOMEN SHOULD NOT DRINK ALCOHOLIC BEVERAGES DURING PREGNANCY BECAUSE OF THE RISK OF BIRTH DEFECTS. (2) CONSUMPTION OF ALCOHOLIC BEVERAGES IMPAIRS YOUR ABILITY TO DRIVE A CAR OR OPERATE MACHINERY, AND MAY CAUSE HEALTH PROBLEMS."
```

Submit two labels as a batch. Repeated `images` fields map to `items_json` entries by array order:

```bash
curl -X POST http://localhost:8000/verify/batch \
  -F 'items_json=[{"client_id":"label-1","brand_name":"Acme Reserve","class_type":"Straight Bourbon Whiskey","abv":"45%","net_contents":"750 mL","producer":"Acme Distilling Co.","country_of_origin":"United States","government_warning":"GOVERNMENT WARNING: (1) ACCORDING TO THE SURGEON GENERAL, WOMEN SHOULD NOT DRINK ALCOHOLIC BEVERAGES DURING PREGNANCY BECAUSE OF THE RISK OF BIRTH DEFECTS. (2) CONSUMPTION OF ALCOHOLIC BEVERAGES IMPAIRS YOUR ABILITY TO DRIVE A CAR OR OPERATE MACHINERY, AND MAY CAUSE HEALTH PROBLEMS."},{"client_id":"label-2","brand_name":"Acme Reserve","class_type":"Straight Bourbon Whiskey","abv":"45%","net_contents":"750 mL","producer":"Acme Distilling Co.","country_of_origin":"United States","government_warning":"GOVERNMENT WARNING: (1) ACCORDING TO THE SURGEON GENERAL, WOMEN SHOULD NOT DRINK ALCOHOLIC BEVERAGES DURING PREGNANCY BECAUSE OF THE RISK OF BIRTH DEFECTS. (2) CONSUMPTION OF ALCOHOLIC BEVERAGES IMPAIRS YOUR ABILITY TO DRIVE A CAR OR OPERATE MACHINERY, AND MAY CAUSE HEALTH PROBLEMS."}]' \
  -F "images=@samples/acme-reserve-bourbon-label.jpg;type=image/jpeg" \
  -F "images=@samples/acme-reserve-bourbon-label.jpg;type=image/jpeg"
```

The single response is a `VerificationResult` with `results`, `overall_verdict`, and `latency_ms`. The batch response contains `items`, `summary`, and `latency_ms`.

## Backend Environment Variables

| Variable | Required | Default | Purpose |
| --- | --- | --- | --- |
| `APP_ENV` | No | `local` | Human-readable runtime environment label. |
| `CORS_ALLOWED_ORIGINS` | No | `http://localhost:5173,http://127.0.0.1:5173` | Comma-separated browser origins permitted to call the API. |
| `VISION_PROVIDER` | No | `mock` | Extraction provider: `mock` for deterministic local use or `openai` for live extraction. |
| `VISION_MODEL` | No | `gpt-5.4-mini` | Model ID passed to the OpenAI Responses API when `VISION_PROVIDER=openai`. |
| `VISION_TIMEOUT_SECONDS` | No | `4` | Per-model-call timeout, kept below the five-second single-label SLA. |
| `VISION_MAX_IMAGE_EDGE_PX` | No | `1280` | Maximum longest image edge after preprocessing. |
| `VISION_JPEG_QUALITY` | No | `76` | JPEG re-encoding quality after preprocessing; valid range is 1–100. |
| `MAX_UPLOAD_BYTES` | No | `10485760` | Maximum size of one uploaded image in bytes. |
| `BATCH_MAX_ITEMS` | No | `10` | Maximum labels accepted in one batch request. |
| `BATCH_WORKER_CONCURRENCY` | No | `3` | Maximum concurrent batch-item verifications. |
| `OPENAI_API_KEY` | Yes when `VISION_PROVIDER=openai`; otherwise no | unset | OpenAI credential used only by the backend. |

Frontend configuration is separate: `VITE_API_BASE_URL` is optional and defaults in code to the deployed Render URL. Render injects `PORT` for the Uvicorn start command; it is not read by the application settings model.

`.env.example` intentionally keeps the safe local provider (`mock`) and the same documented `VISION_MODEL=gpt-5.4-mini`. Production overrides `VISION_PROVIDER=openai` through Render configuration.

## Vision Model Verification

Configured model: `gpt-5.4-mini` (`VISION_MODEL` in backend defaults, `.env.example`, and `render.yaml`).

Provider-list verification: **2026-07-12**. A credentialed OpenAI Models API check confirmed that `gpt-5.4-mini` was listed and retrievable under the configured account. Render startup also retrieves the configured model before an OpenAI-configured worker accepts traffic.

## Deployment

### Render backend

[`render.yaml`](render.yaml) defines the root-based Python service, including:

- Build: `uv sync --frozen --no-dev && uv cache prune --ci`
- Start: `uv run --no-sync uvicorn backend.app.main:app --host 0.0.0.0 --port $PORT`
- Health check: `/health`

The Blueprint declares all non-secret production settings and marks `OPENAI_API_KEY` as a host-supplied value. Set or confirm the secret in Render; never add it to the repository.

### Vercel frontend

[`frontend/vercel.json`](frontend/vercel.json) defines `npm ci`, `npm run build`, and `dist` for the existing Vite project. In the Vercel project settings, set **Root Directory** to `frontend`, set `VITE_API_BASE_URL=https://bruno-rebaza-ttd-label-verification-ej1c.onrender.com`, and redeploy. Vercel serves the static `dist` output; `npm run preview` is local-only and is not a production start command.

## Performance Measurement

Target for deployed single-label checklist latency: p50 ≤ 3000 ms, p95 ≤ 4500 ms, and every sample < 5000 ms.

Measured current-deployment evidence, recorded **2026-07-12**:

| Base URL | Command | Run count | Single-label checklist samples | p50 | p95 | Max | `all_passed` |
| --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| `https://bruno-rebaza-ttd-label-verification-ej1c.onrender.com` | `scripts/benchmark_verification.py --repeats 3 --json` | 3 valid-label repeats | 9 (`repeats + 6` scenarios) | 3313 ms | 4800 ms | 4800 ms | `true` |

Every measured single-label sample met the hard under-five-second requirement. The p50 exceeded the 3000 ms target and the p95 exceeded the 4500 ms target; those softer performance targets remain follow-up work.

To measure the current deployment:

```bash
uv run python scripts/benchmark_verification.py --base-url https://bruno-rebaza-ttd-label-verification-ej1c.onrender.com --repeats 3 --json
```

Record the execution date, base URL, `--repeats` value, total single-label checklist samples (`repeats + 6`), p50, p95, maximum, and `all_passed` result from the JSON output.

## Tests and Verification

```bash
uv run pytest
cd frontend && npm run build
```

The deterministic fixture can be regenerated without a backend call:

```bash
uv run python scripts/benchmark_verification.py --write-sample samples/acme-reserve-bourbon-label.jpg
```

For live acceptance, confirm Render `/health`, use the deployed frontend for one single-label and one multi-item batch verification, run the benchmark above, and perform provider model-list verification.

## Secret Handling

- API keys are environment variables only: `.env` and `frontend/.env` are ignored, while only example files are tracked.
- Keep `OPENAI_API_KEY` in Render or a local untracked `.env`; it must never appear in source, documentation examples, curl commands, build output, or browser-visible `VITE_*` variables.
- Use `.env.example` as a names-and-safe-defaults template, not a source of production values.
- If a credential is exposed, revoke or rotate it in the provider console, replace the host secret, and audit repository history before redeploying.

Audit commands:

```bash
git ls-files .env frontend/.env
git log --all --oneline -- .env frontend/.env
git check-ignore -v .env frontend/.env
git grep -n -I -E "(sk-[A-Za-z0-9_-]{20,}|OPENAI_API_KEY\\s*=\\s*[^<[:space:]#][^[:space:]#]+|API_KEY\\s*=\\s*[^<[:space:]#][^[:space:]#]+|SECRET\\s*=\\s*[^<[:space:]#][^[:space:]#]+|TOKEN\\s*=\\s*[^<[:space:]#][^[:space:]#]+|PASSWORD\\s*=\\s*[^<[:space:]#][^[:space:]#]+)"
```

## Assumptions

- `NEEDS_REVIEW` means a human reviewer inspects field-level details.
- The configured production model returns partial or null fields rather than guessing when an image is poor or incomplete.
- Free-tier services can have a first-request cold start; the under-five-second target applies to measured verification behavior, not an unbounded cold-start delay.

## Limitations

- This is not a production compliance system.
- There is no login, persistent audit trail, database, manual override workflow, or long-term image storage.
- Vision quality and latency depend on provider availability, image quality, and network conditions.
- Repository scans catch common key patterns but are not a replacement for organization-wide secret scanning.

## Tradeoffs

- Stateless, in-memory processing reduces cost and deployment complexity but provides no audit history.
- The government warning favors strict exact comparison to avoid false approvals; other fields use normalization to tolerate ordinary label formatting and OCR variation.
- A four-second provider timeout preserves the five-second response budget but can return `NEEDS_REVIEW` for otherwise readable labels.
- Batch work is concurrency-limited for free-tier stability, so total batch time can exceed the per-label SLA.
