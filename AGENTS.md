# AGENTS.md

This file provides guidance to Codex (claude.ai/code) when working with code in this repository.

## Project

University final-year project (Yerevan State University, Ijevan Branch, Informatics and Applied Mathematics). Solo. Deadline: ~May 31, 2027.

Official title (Armenian, registered and locked, cannot be changed):
«HTTP հարցումների հաճախականության հարմարվողական սահմանափակման համակարգի մշակում»
(English: "Development of an adaptive system for limiting the frequency of HTTP requests")

An **adaptive rate limiter** implemented as a **FastAPI reverse proxy**:

    Client → Rate Limiter (this app) → Backend

Allowed requests are forwarded to the backend; rejected ones get `429` without touching the backend. The adaptive part is not built yet — currently only a static in-memory fixed-window limiter exists.

## Scope (important)

- HTTP requests only.
- Describe it as **application-layer abuse mitigation**. Do NOT claim it prevents all DoS/DDoS or volumetric network DDoS.
- The university rubric requires a novelty/research angle. Novelty comes from the **adaptive mechanism plus a rigorous, reproducible evaluation**, not from the basic limiter. The evaluation matters more than extra features.

## Thesis claim (everything should help prove or disprove this)

Static limiters either miss abusive patterns (low-and-slow, distributed across many IPs, bursts at window boundaries) or punish legitimate users (users sharing one IP behind NAT/mobile carriers/offices, normal users during backend overload). The adaptive limiter reduces both problems, measured against fixed-window, sliding-window and token-bucket baselines on reproducible traffic scenarios.

Metrics: % abusive requests blocked, % legitimate requests wrongly blocked, added proxy latency (p50/p95), backend latency/error rate under load.

## Commands

Dependencies are managed with **uv** (Python 3.14, see `.python-version`).

```bash
uv sync                                   # install deps into .venv
uv run fastapi dev main.py                # dev server with reload (port 8000)
uv run uvicorn main:app --workers 4       # multi-worker run (exposes per-worker state issue, see below)
```

Configuration comes from `.env` (gitignored) via `pydantic-settings` in `config.py`. Required: `BACKEND_URL` — the upstream service requests are proxied to.

There is no test suite, linter, or type checker configured yet.

## Architecture

Everything currently lives in `main.py`:

- A single catch-all route (`/{path:path}`, all common methods) is the proxy. Flow: rate-limit check → build target URL from `settings.backend_url` + path + query → strip hop-by-hop headers → forward with `httpx` → strip hop-by-hop headers from the response → return it. Upstream connection errors become `502`.
- `is_allowed()` is a fixed-window counter keyed by `request.client.host`, with `RATE_LIMIT` / `WINDOW_SECONDS` as module constants (currently 5 requests / 60 s).

Done so far: working reverse proxy, in-memory fixed-window limiter, IP-based client identification, `429` responses, manual sequential and concurrent request testing.

## Known limitations

Don't "fix" these silently — several are meant to be demonstrated in the dissertation. Fix them as explicit, explained steps.

- **Limiter state is a module-level dict**, so each uvicorn worker/instance has its own counters (effective limit = limit × workers) and the dict never evicts old keys. Planned fix: shared state in Redis with atomic Lua scripts (`flow.png`, gitignored, diagrams this).
- **Client key is the direct peer IP**; behind Nginx every client would share one bucket. Trusting `X-Forwarded-For` must be limited to known proxies.
- A new `httpx.AsyncClient` is created per request (no connection pooling).
- No `Retry-After` / `X-RateLimit-*` headers; fixed window allows ~2× limit bursts at window boundaries.
- No defined behavior when Redis (once added) is unavailable — fail-open vs fail-closed must be chosen and justified.

## Roadmap

1. **Nov–Dec — Interface + Redis.**
   - Extract the limiter behind one small interface (input: client key; output: allowed, remaining, retry-after) so algorithms and storage backends can be swapped and compared fairly.
   - Implement fixed window, sliding window and token bucket; storage backends: memory and Redis.
   - Redis via `redis.asyncio` + docker-compose. First demonstrate the race condition of a naive GET→check→INCR under concurrency, then fix it with atomic Lua scripts.
   - Test with 2+ proxy instances: total limit must hold across instances.
   - Decide fail-open vs fail-closed when Redis is down.
2. **Jan — Load testing + metrics.**
   - Traffic generator (Locust or k6) with reproducible scenarios: normal users, shared-IP users, burst attack, low-and-slow attack, distributed attack across many IPs, backend-overload situation.
   - Log every limiter decision. Metrics via Prometheus/Grafana only if simple logging/CSV isn't enough (KISS).
3. **Feb–Mar — Adaptive layer.** Two possible signals (see Open decision below):
   - **Per-client behavior score** (rule-based first, explainable): request rate, 4xx ratio, inter-arrival regularity, endpoint diversity → suspicious clients get lower limits.
   - **Backend-health controller**: adjust limits from backend latency/error rate, AIMD-style.
   - Isolation Forest only afterwards, as a comparison against the rule-based scorer — never as the first step.
4. **Apr — Evaluation.** Every limiter × every scenario → result tables (static vs adaptive).
5. **May — Write-up and demo.**

## Open decision: what does "adaptive" adapt to?

Not settled yet — ask before building the adaptive layer.
- Backend health only (AIMD): protects the backend, but doesn't distinguish abusers from legitimate users, and is close to known work (e.g. Netflix concurrency-limits).
- Client behavior only: directly matches the "abusive traffic" scope and the shared-IP problem.
- Both: backend health decides **how much** total traffic to allow; behavior score decides **who** gets limited first. Strongest story, but biggest scope — only if time allows.

## Engineering principles

- KISS, minimal dependencies, scope appropriate for a bachelor's project.
- Rule-based before ML.
- Every limiter implements the same interface.
- Stay on the roadmap path; no extra features that don't serve the evaluation.

## How to work with me (very important)

- I'm a junior developer (Laravel background, moving to Node.js/Python). I want to **understand**, not just receive code.
- Work as a step-by-step teaching assistant: explain the concept first, then pseudocode, then small incremental changes. **Stop after each step** so I can understand and test it.
- Don't generate large implementations in one go. Ask me questions where useful instead of doing all the thinking.
- Be skeptical and give critical feedback. Explain *why* a solution works.
- Keep answers concise.