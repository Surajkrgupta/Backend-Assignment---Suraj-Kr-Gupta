Lyftr AI API

A secure, high-performance FastAPI service for ingesting webhook messages, validating them using HMAC SHA-256, storing them in SQLite, and exposing analytics and Prometheus metrics.
Features

 HMAC SHA-256 webhook signature verification

 SQLite storage with safe concurrent writes

 Message search + pagination (limit, offset, text search, timestamp filter, sender filter)

 Aggregated stats endpoint (/stats)

 Prometheus-compatible metrics (/metrics)

 Built-in Swagger API docs

 Clean modular architecture (FastAPI + Pydantic + SQLite)

 Getting Started
1. Install dependencies
pip install -r requirements.txt

2. Run the server
python -m uvicorn app.main:app --reload


The API will start at:

http://localhost:8000

3. Open API docs (Swagger)
http://localhost:8000/docs

 API Endpoints
Method	Endpoint	Description
GET	/healthz	Health check
POST	/webhook	Ingest a webhook event (HMAC-verified)
GET	/messages	Paginated message search & filtering
GET	/stats	Message analytics
GET	/metrics	Prometheus metrics
 Webhook Ingestion
POST /webhook

This endpoint receives incoming message events.

Required Headers
Content-Type: application/json
x-signature: <hex-encoded HMAC SHA-256>

Example Payload
{
  "message_id": "msg-001",
  "from": "919000000001",
  "to": "919000000002",
  "ts": 1710001123,
  "text": "Hello world"
}

Example cURL
BODY='{"message_id":"msg-001","from":"100","to":"200","ts":1710000000,"text":"hi"}'
SIG=$(echo -n $BODY | openssl dgst -sha256 -hmac "$WEBHOOK_SECRET" | sed 's/^.* //')

curl -X POST http://localhost:8000/webhook \
  -H "Content-Type: application/json" \
  -H "x-signature: $SIG" \
  -d "$BODY"


Success response:

{ "status": "ok" }

 Messages API
GET /messages

Supports pagination, search, date filters, and sender filters.

Query Parameters
Name	Type	Default	Description
limit	int	50	Page size (1–100)
offset	int	0	Items to skip
q	string	—	Text search
from_	string	—	Filter by sender
since	ISO datetime	—	Filter by timestamp
Example
/messages?limit=20&offset=0&q=hello&from_=9190&since=2024-01-01T00:00:00Z

Response
{
  "total": 142,
  "limit": 20,
  "offset": 0,
  "data": [
    {
      "message_id": "msg-001",
      "from": "9190",
      "to": "9200",
      "ts": 1710001123,
      "text": "hello world"
    }
  ]
}

Pagination Contract

Backend always returns total matching records.

Client checks:

has_more = offset + limit < total

 Stats API
GET /stats

Returns system-level analytics.

Example:

{
  "total_messages": 1203,
  "senders_count": 42,
  "messages_per_sender": [
    { "from": "9190", "count": 233 },
    { "from": "9200", "count": 199 }
  ],
  "first_message_ts": "2024-02-15T10:21:33Z",
  "last_message_ts": "2024-02-17T09:48:01Z"
}

 Metrics API
GET /metrics

Prometheus-compatible metrics.
Used for monitoring ingestion rates, DB status, and signature failures.

Example output:

webhook_total{status="created"} 54
webhook_total{status="invalid_signature"} 3
db_write_total{result="success"} 54

 HMAC Verification (How It Works)

Webhook security uses HMAC SHA-256 with a shared secret.

The server:

Reads the raw request body

Computes:

hmac.new(
    WEBHOOK_SECRET.encode(),
    raw_body,
    hashlib.sha256
).hexdigest()


Compares signatures using constant-time comparison:

hmac.compare_digest(computed, provided)


Rejects invalid signatures (401 Unauthorized)

Updates Prometheus metrics for success/failure

This ensures:

Payload integrity

Authentic source

Protection from tampering / replay attempts

 Design Decisions
✔ FastAPI for speed and typed APIs

Automatic Swagger docs

Async support

Strong Pydantic validation

✔ SQLite for simplicity and performance

Zero-config database

Perfect for webhook ingestion

Thread-safe writes via a database lock

✔ Secure webhook ingestion

HMAC avoids spoofing and tampering

Signature mismatch tracked via metrics

✔ Offset-based pagination

Predictable

Easy for frontend clients

Efficient for sequential SQLite reads

✔ Clear separation of concerns

main.py → routing + validation

models.py → DB operations

metrics.py → Prometheus counters

schemas.py → Pydantic models

 Project Structure
app/
 ├── main.py              # FastAPI routes & webhook logic
 ├── metrics.py           # Prometheus counters / registry
 ├── models.py            # SQLite table & query helpers
 ├── storage.py           # DB connection & stats aggregation
 ├── config.py            # Environment variables & settings
 ├── schemas.py           # Pydantic request/response models
