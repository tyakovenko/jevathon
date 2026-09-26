# jevathon — on-call ticket routing

GitHub issue → Jev triage → autonomous Ralph loop (non-severe) or best available dev via Photon (severe) → secrets / AI-slop / test gate → human review.

Design and open questions: **[docs/oncall-ticket-routing.md](docs/oncall-ticket-routing.md)**.

## Run locally

```bash
# backend (Python 3.12)
cd backend
uv venv .venv && VIRTUAL_ENV=.venv uv pip install -r pyproject.toml --extra dev
cp .env.example .env                      # all adapters default to fake — no keys needed
.venv/bin/uvicorn app.main:app --reload   # http://localhost:8000/docs
.venv/bin/python -m pytest -q

# frontend
cd ../frontend
npm install && npm run dev                # http://localhost:5173
```

Try it without GitHub (fake mode):

```bash
curl -XPOST localhost:8000/simulate/issue -H 'content-type: application/json' \
  -d '{"number":1,"title":"Checkout 500s","body":"prod checkout failing"}'
curl -XPOST localhost:8000/simulate/reply -H 'content-type: application/json' -d '{"dev_id":"ana","text":"yes"}'
curl localhost:8000/outbox                # texts that would have gone out via Photon
```

## Going real

Flip one adapter at a time in `backend/.env` (`JEV_MODE=real`, …). Startup fails fast if that adapter's keys are missing.
GitHub webhooks need a public URL: `cloudflared tunnel --url http://localhost:8000` → repo Settings → Webhooks → `<url>/webhooks/github` (events: Issues, Issue comments, Pull requests, Check suites).

## Layout

| Path | What |
|---|---|
| `backend/app/orchestrator.py` | State machine — the only place stages change |
| `backend/app/stages/` | triage · dev_routing · replies · research · ralph_loop · checks · handoff |
| `backend/app/services/` | One adapter per tool (Jev, GMI, Photon, Browserbase, GitHub, coding agent), each with a fake |
| `backend/data/devs.json` | Seed dev roster |
| `frontend/` | Dashboard (Vite + React + Tailwind), deployed via Vercel |
