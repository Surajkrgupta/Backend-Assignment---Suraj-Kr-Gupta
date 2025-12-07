import sqlite3
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime
from .models import DB_LOCK

def insert_message(conn: sqlite3.Connection, message: Dict[str, Any]) -> Tuple[bool, str]:
    """Insert message. Returns (created, reason). created True if new row inserted, False otherwise."""
    with DB_LOCK:
        try:
            conn.execute(
                "INSERT INTO messages (message_id, from_msisdn, to_msisdn, ts, text, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                (message["message_id"], message["from"], message["to"], message["ts"], message.get("text"), datetime.utcnow().isoformat() + "Z"),
            )
            conn.commit()
            return True, "created"
        except sqlite3.IntegrityError:
            return False, "duplicate"
        except Exception as e:
            return False, "error: " + str(e)

def build_filters(params: Dict[str, Any]) -> Tuple[str, List[Any]]:
    clauses = []
    args = []
    if params.get("from"):
        clauses.append("from_msisdn = ?")
        args.append(params["from"])
    if params.get("since"):
        clauses.append("ts >= ?")
        args.append(params["since"])
    if params.get("q"):
        clauses.append("LOWER(text) LIKE ?")
        args.append(f"%{params['q'].lower()}%")
    where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
    return where, args

def query_messages(conn, limit: int, offset: int, filters: dict):
    query = "SELECT * FROM messages WHERE 1=1"
    count_query = "SELECT COUNT(*) FROM messages WHERE 1=1"
    params = []

    # Apply filters
    if "from" in filters:
        query += " AND from_msisdn = ?"
        count_query += " AND from_msisdn = ?"
        params.append(filters["from"])
    if "since" in filters:
        query += " AND ts >= ?"
        count_query += " AND ts >= ?"
        params.append(filters["since"])
    if "q" in filters:
        query += " AND LOWER(text) LIKE ?"
        count_query += " AND LOWER(text) LIKE ?"
        params.append(f"%{filters['q'].lower()}%")

    # Ordering and pagination
    query += " ORDER BY ts ASC, message_id ASC LIMIT ? OFFSET ?"
    params.extend([limit, offset])

    # Execute query
    cursor = conn.cursor()
    cursor.execute(query, params)
    rows = cursor.fetchall()

    # Convert rows to dict
    data = [
        {
            "message_id": row["message_id"],
            "from": row["from_msisdn"],
            "to": row["to_msisdn"],
            "ts": row["ts"],
            "text": row["text"]
        } for row in rows
    ]

    # Get total count (without limit/offset)
    cursor.execute(count_query, params[:-2])
    total = cursor.fetchone()[0]

    return data, total


def stats(conn: sqlite3.Connection) -> Dict[str, Any]:
    cur = conn.cursor()
    cur.execute("SELECT COUNT(1) FROM messages")
    total_messages = cur.fetchone()[0]
    cur.execute("SELECT COUNT(DISTINCT from_msisdn) FROM messages")
    senders_count = cur.fetchone()[0]
    cur.execute("""SELECT from_msisdn, COUNT(1) as cnt FROM messages GROUP BY from_msisdn ORDER BY cnt DESC, from_msisdn ASC LIMIT 10""")
    rows = cur.fetchall()
    messages_per_sender = [{"from": r[0], "count": r[1]} for r in rows]
    cur.execute("SELECT MIN(ts), MAX(ts) FROM messages")
    mn, mx = cur.fetchone()
    return {
        "total_messages": total_messages,
        "senders_count": senders_count,
        "messages_per_sender": messages_per_sender,
        "first_message_ts": mn,
        "last_message_ts": mx
    }
