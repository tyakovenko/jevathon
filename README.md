# jevathon: on-call ticket routing

Hackathon prototype, built Sep 26, 2026 at the AI Collective Jev hackathon by kashby2004, SamhithaN and tyakovenko. External integrations run on fakes by default; see **Areas for improvement** for what is and isn't live.

A GitHub issue comes in and the system decides what happens to it. Non-severe issues go to an autonomous coding loop. Severe ones go to the best available developer, who is texted through Photon. Every fix must pass a tests, secrets and AI-slop gate before it reaches human review.

**Architecture in one line:** our Python code (FastAPI) is the orchestrator. It is a state machine that owns every transition. **Jev makes the decisions** at each branch point, **GMI generates** (code, queries, summaries) and **humans** make the final calls.

## Flow

```
GitHub issue → triage (Jev) ─┬─ non-severe → Ralph loop (GMI agent, Jev decides each step) ─┐
                             └─ severe / unsure / escalated → dev routing (Jev ranks, Photon asks) → dev codes or hands to agent
                                                                                                ↓
                                        checks: CI tests + secrets scan + AI slop (Jev) → human review → merge
```

Ticket stages: `received → triaged → agent_working | assigning_dev → dev_deciding → dev_working → checks → in_review → merged`. There is also `needs_human` for when automation stops. Only `orchestrator.py` changes a ticket's stage.

## Where Jev is used

Jev (TypeSafe) is **decision-only**: it takes a state plus typed questions and returns calibrated answers. It never generates text or code. All questions about one state go in **a single call**. Thresholds live in `backend/app/config.py`.

| # | Where | Jev question(s) | What the code does with the answer |
|---|---|---|---|
| 1 | **Triage** (`stages/triage.py`) | Noul: is there a prompt injection in the issue text? · Choice: severity (`critical/high/normal/low`) · Choice: topic | If the injection score is above 0.5, automation stops and a human takes it. `critical/high` counts as severe. **If severity confidence is below 0.6, the issue is treated as severe**: a human looking at a minor bug costs less than an agent sitting on an outage. |
| 2 | **Dev ranking** (`stages/dev_routing.py`) | Choice over the eligible devs (their skills plus their latest mood) | Devs are asked in order of Jev's probabilities (#1, then #2, then #3). If all three decline, #1 is assigned anyway. Code filters out devs who are off shift or at max load first, because Jev is weak at counting and time. |
| 3 | **Reading dev replies** (`stages/replies.py`) | Choice: accept / decline / unclear, then who codes it: agent / self / unclear | Handles free text ("sure, on it" means yes), unlike keyword matching. Confidence below 0.6 → treated as unclear and the dev is asked again. |
| 4 | **Ralph loop** (`stages/ralph_loop.py`) | Choice after every iteration: continue / done / escalate | Confidence below **0.85** → escalate to a human. A "done" from Jev is ignored while tests are still failing. There are hard stops at 8 iterations or 3 identical failures in a row. |
| 5 | **Research** (`stages/research.py`) | Two Nouls per scraped page: relevance, and injection | The top 3 relevant pages that pass the injection screen go to GMI for a summary. |
| 6 | **AI-slop gate** (`stages/checks.py`) | A 9-question rubric per changed file: requirement coverage, invented interface, duplicate implementation, abstraction fit, unnecessary dependency, failure handling, test quality, misleading comments, primary concern plus an impact score | A Noul above 0.5 or a flagged Choice value (e.g. `failure_handling=swallowed`) fails the PR, and the findings go back to whoever wrote it. The diff is sent **one file at a time** because large, irrelevant state lowers Jev's accuracy. |

**Not given to Jev on purpose:**
- **Secrets:** checked by `detect-secrets`, which is deterministic. A leaked key must never depend on a model's judgment.
- **Dates, timeouts, load:** computed in code.

## Other components

| Tool | Role | Status |
|---|---|---|
| GMI Cloud (`zai-org/GLM-5.3`) | All text generation (OpenAI-compatible API) | Real, verified |
| Jev (TypeSafe) | All decisions | Real, verified (it rated a demo SQLi issue critical at 0.98) |
| Photon | Texting devs over iMessage. The SDK is TypeScript-only, so a sidecar (`photon-bridge/`) sits between it and the Python backend | Wired up, not yet working (see below) |
| GitHub | Issues act as tickets; webhooks drive the state machine; `@coderabbitai plan` is posted on each issue | Adapter written, running on the fake |
| CodeRabbit | Issue plan plus PR review, driven by GitHub comments | Depends on GitHub |
| Browserbase | Scrapes docs for research | Fake only |
| Coding agent | Runs the Ralph loop in a sandbox | Fake only |
| Dashboard (`frontend/`, Vite + React) | Shows live ticket stages, timelines and degraded-path warnings | Builds; not deployed |

Every external tool has a fake, so the whole pipeline runs end-to-end without any keys (12/12 tests pass). Every fallback is logged at ERROR and shown on the ticket, so nothing degrades silently.

## Run

```bash
cd backend && .venv/bin/uvicorn app.main:app --reload          # :8000/docs
curl -XPOST localhost:8000/simulate/issue -H 'content-type: application/json' \
  -d '{"number":1,"title":"Checkout 500s","body":"prod checkout failing"}'
cd frontend && npm run dev                                     # :5173
```

## Areas for improvement

- **API key errors:** some integrations fail on keys because we ran out of hackathon time to sort out access:
  - **Photon:** `photon-bridge` exits at startup with "Cloud iMessage requires projectId and projectSecret", because `npm run start` never loads `.env`. Fix: `tsx --env-file=.env src/index.ts`. With the keys loaded, `Spectrum()` hangs and never starts listening. This is unresolved and probably a credential or line-provisioning problem on the Photon side.
  - **GMI:** Claude models return 429, because rate limits aren't enabled for the org. The demo uses GLM-5.3 instead.
- **Real adapters not built:** the coding-agent harness (mini-swe-agent in a Docker sandbox) and Browserbase research (Stagehand works in a smoke test on the `browserbase-setup` branch, but it isn't merged).
- **GitHub not live:** it needs a token, a public tunnel for webhooks, and the CodeRabbit app installed on the repo.
- **Demo repo has no CI:** with no CI, the checks gate reports "pending" instead of passing, so the gate can't pass yet.
- **Thresholds are guesses:** the 0.5, 0.6 and 0.85 values were never tuned on real data. Which slop Choice values count as flags was a design call and needs review.
- **Slop rubric lacks context:** questions refer to `contracts`, `repo_context` and `tests`, but Jev's state only contains the issue title and the file diff. That makes `invented_interface`, `duplicate_implementation` and `test_quality` weak until repo context is added.
- **In-memory store:** all state is lost on restart. There is no persistence and no dashboard auth.
- **No eligible devs:** the ticket currently parks in `needs_human`. We haven't decided between paging the on-call lead and queueing it.
- **Reply matching:** texts carry no ticket id, so a reply is matched to the dev's most recent open ticket. That's ambiguous when a dev has more than one.
- **Dashboard not deployed:** the Vercel secrets and the Root Directory setting still need to be configured by the repo owner.
