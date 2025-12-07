
# Lyftr AI — Backend Assignment (sample implementation)

## Overview
A production-style FastAPI service that ingests WhatsApp-like messages via `/webhook`, validates HMAC signatures, stores messages in SQLite, provides paginated `/messages`, `/stats`, health checks, structured JSON logs, and a `/metrics` endpoint.

## How to run
Set env vars and start the stack:

```bash
export WEBHOOK_SECRET="testsecret"
export DATABASE_URL="sqlite:////data/app.db"
make up
```

Wait ~5-10s, then:
- Liveness: `GET http://localhost:8000/health/live`
- Readiness: `GET http://localhost:8000/health/ready`
- Webhook: `POST http://localhost:8000/webhook`
  - Header `X-Signature` = hex(HMAC_SHA256(WEBHOOK_SECRET, raw_body_bytes))
- Messages: `GET http://localhost:8000/messages`
- Stats: `GET http://localhost:8000/stats`
- Metrics: `GET http://localhost:8000/metrics`

## Design decisions
- Tech: FastAPI, builtin `sqlite3` for simplicity and small image.
- DB: SQLite file stored at `/data/app.db` mounted as Docker volume in docker-compose.
- HMAC verification: `hmac.new(secret_bytes, body_bytes, hashlib.sha256).hexdigest()` and compared with `hmac.compare_digest`.
- Pagination contract: `limit` (default 50, 1..100) and `offset` (default 0). Results ordered by `ts ASC, message_id ASC`. `total` is count for the filter (ignores limit/offset).
- /stats: Uses SQL queries for counts and aggregates (top 10 senders).
- Metrics: In-memory counters exposed in Prometheus text format. Provides `http_requests_total` and `webhook_requests_total` as required.
- Logs: JSON per-line structured logs with `ts`, `level`, `request_id`, `method`, `path`, `status`, `latency_ms` and webhook-specific fields (`message_id`, `dup`, `result`).

## Makefile
- `make up` → `docker compose up -d --build`
- `make down` → `docker compose down -v`
- `make logs` → `docker compose logs -f api`
- `make test` → runs pytest (lightweight tests included)

## Setup Used
VSCode + Copilot + occasional ChatGPT prompts

