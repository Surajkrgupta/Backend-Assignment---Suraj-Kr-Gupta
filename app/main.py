from fastapi import FastAPI, Request, Response, Header, HTTPException, Depends, status
from fastapi.responses import JSONResponse, PlainTextResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, validator
import hmac, hashlib, os, time, uuid, logging
from .config import WEBHOOK_SECRET, DATABASE_URL, LOG_LEVEL
from .models import init_db
from .storage import insert_message, query_messages, stats as stats_fn
from .logging_utils import setup_logging
from .metrics import metrics
import sqlite3
from typing import Optional
from datetime import datetime
from .config import DATABASE_URL
from app.models import init_db

logger = setup_logging(LOG_LEVEL)

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize DB connection at startup
db_conn: Optional[sqlite3.Connection] = None

class WebhookModel(BaseModel):
    message_id: str = Field(..., min_length=1)
    from_: str = Field(..., alias="from")
    to: str
    ts: str
    text: Optional[str] = None

    @validator("from_", "to")
    def e164_like(cls, v):
        if not (v.startswith("+") and v[1:].isdigit()):
            raise ValueError("must be E.164-like")
        return v

    @validator("ts")
    def ts_utc_z(cls, v):
        try:
            # Basic validation for ISO-8601 Z suffix
            if not v.endswith("Z"):
                raise ValueError("must end with Z")
            # parse
            datetime.fromisoformat(v.replace("Z", "+00:00"))
        except Exception:
            raise ValueError("must be ISO-8601 UTC with Z suffix")
        return v

    @validator("text")
    def text_len(cls, v):
        if v is not None and len(v) > 4096:
            raise ValueError("text too long")
        return v

@app.on_event("startup")
def startup():
    global db_conn
    logger.info("starting app", extra={"extra":{"event":"startup"}})
    db_conn = init_db(DATABASE_URL)

@app.middleware("http")
async def metrics_and_logging_middleware(request: Request, call_next):
    start = time.time()
    req_id = str(uuid.uuid4())
    request.state.request_id = req_id
    method = request.method
    path = request.url.path
    try:
        response = await call_next(request)
        status_code = response.status_code
    except Exception as e:
        status_code = 500
        raise
    finally:
        latency_ms = int((time.time() - start) * 1000)
        metrics.observe_latency(latency_ms)
        metrics.inc_http(path, status_code)
        log_extra = {
            "request_id": req_id,
            "method": method,
            "path": path,
            "status": status_code,
            "latency_ms": latency_ms
        }
        logger.info("", extra={"extra": log_extra})
    return response

def verify_signature(raw_body: bytes, signature: str) -> bool:
    if not WEBHOOK_SECRET:
        return False
    computed = hmac.new(WEBHOOK_SECRET.encode(), raw_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(computed, signature)

@app.post("/webhook")
async def webhook(request: Request, x_signature: Optional[str] = Header(None)):
    raw = await request.body()
    req_id = request.state.request_id if hasattr(request.state, "request_id") else str(uuid.uuid4())
    message_id = None
    dup = False
    result = None
    if not x_signature:
        metrics.inc_webhook("invalid_signature")
        result = "invalid_signature"
        logger.error("invalid signature header", extra={"extra":{"request_id": req_id, "result": result}})
        raise HTTPException(status_code=401, detail="invalid signature")
    if not verify_signature(raw, x_signature):
        metrics.inc_webhook("invalid_signature")
        result = "invalid_signature"
        logger.error("invalid signature", extra={"extra":{"request_id": req_id, "result": result}})
        raise HTTPException(status_code=401, detail="invalid signature")
    # parse json + validation via Pydantic
    try:
        body = await request.json()
        model = WebhookModel.parse_obj(body)
    except Exception as e:
        metrics.inc_webhook("validation_error")
        result = "validation_error"
        logger.error("validation error", extra={"extra":{"request_id": req_id, "result": result}})
        raise

    message = {
        "message_id": model.message_id,
        "from": model.from_,
        "to": model.to,
        "ts": model.ts,
        "text": model.text
    }
    message_id = message["message_id"]
    created, reason = insert_message(db_conn, message)
    metrics.inc_webhook(reason)
    result = reason
    dup = (not created)
    # log with webhook specific fields
    logger.info("webhook processed", extra={"extra":{
        "request_id": req_id,
        "message_id": message_id,
        "dup": dup,
        "result": result,
        "method": "POST",
        "path": "/webhook",
        "status": 200,
        "latency_ms": 0
    }})
    return JSONResponse({"status":"ok"})

@app.get("/messages")
def get_messages(
    limit: int = 50,
    offset: int = 0,
    from_: Optional[str] = None,
    since: Optional[str] = None,
    q: Optional[str] = None
):
    # Validate limits
    if limit < 1 or limit > 100:
        raise HTTPException(status_code=422, detail="limit must be 1..100")
    if offset < 0:
        raise HTTPException(status_code=422, detail="offset must be >= 0")

    # Build filters dict
    filters = {}
    if from_:
        filters["from"] = from_
    if since:
        filters["since"] = since
    if q:
        filters["q"] = q

    # Query messages from DB
    data, total = query_messages(db_conn, limit, offset, filters)

    return {
        "data": data,
        "total": total,
        "limit": limit,
        "offset": offset
    }


@app.get("/stats")
def get_stats():
    s = stats_fn(db_conn)
    return s

@app.get("/health/live")
def live():
    return PlainTextResponse("ok")

@app.get("/health/ready")
def ready():
    # DB reachable and WEBHOOK_SECRET set
    ok_db = True
    try:
        cur = db_conn.cursor()
        cur.execute("SELECT 1")
        cur.fetchone()
    except Exception:
        ok_db = False
    if not ok_db or not WEBHOOK_SECRET:
        return PlainTextResponse("not ready", status_code=503)
    return PlainTextResponse("ok")

@app.get("/metrics")
def get_metrics():
    return Response(content=metrics.render(), media_type="text/plain")


db_conn = init_db(DATABASE_URL)

