# TTB Label Verification

Phase 0 scaffolds a deployable proof-of-concept: a FastAPI backend with
`GET /health` and a Vite React frontend that fetches that endpoint.

## Local Backend

From a WSL/Linux terminal at the repo root:

```bash
python3 -m pip install --user uv
export PATH="$HOME/.local/bin:$PATH"
uv sync
uv run uvicorn backend.app.main:app --reload --port 8000
```

Open `http://localhost:8000/health`.

## Local Frontend

From a WSL/Linux terminal with Linux Node/npm installed:

```bash
cd frontend
npm install
npm run dev
```

If you are using PowerShell on the WSL UNC path with Windows Node/npm, run these from the repo root instead:

```powershell
cmd /d /s /c "pushd `"$PWD\frontend`" && npm install"
cmd /d /s /c "pushd `"$PWD\frontend`" && npm run build"
cmd /d /s /c "pushd `"$PWD\frontend`" && npm run preview -- --host 0.0.0.0 --port 5173"
```

Open `http://localhost:5173`.

## Tests And Builds

```bash
uv run pytest
```

```powershell
cmd /d /s /c "pushd `"$PWD\frontend`" && npm run build"
```

## Render Backend Deploy

Create a Render web service from the repo root.

- Runtime: Python
- Build command: `uv sync --frozen --no-dev`
- Start command: `uv run --no-sync uvicorn backend.app.main:app --host 0.0.0.0 --port $PORT`
- Environment variables:
  - `APP_ENV=production`
  - `CORS_ALLOWED_ORIGINS=http://localhost:5173,https://YOUR-VERCEL-APP.vercel.app`

After deploy, open `https://YOUR-RENDER-SERVICE.onrender.com/health`.

## Vercel Frontend Deploy

Create a Vercel project with `frontend` as the project root.

- Build command: `npm run build`
- Output directory: `dist`
- Environment variables:
  - `VITE_API_BASE_URL=https://YOUR-RENDER-SERVICE.onrender.com`

After deploy, open the Vercel URL and confirm the page shows the backend health JSON.

## Secrets

Never commit real secrets. Use `.env.example` for names only, and set real values in
Render or Vercel environment variables.