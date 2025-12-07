import sqlite3
from pathlib import Path
import threading

DB_LOCK = threading.Lock()

def init_db(database_url: str):
    # expect sqlite:/// or sqlite:////absolute/path
    if database_url.startswith("sqlite:///"):
        db_path = database_url.replace("sqlite://", "")
        # On Windows, remove leading slash before drive letter
        if db_path.startswith("/") and db_path[2] == ":":
            db_path = db_path[1:]
    else:
        db_path = ":memory:"

    db_file = Path(db_path)
    db_file.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row  # <-- Add this line
    conn.execute("""CREATE TABLE IF NOT EXISTS messages (
        message_id TEXT PRIMARY KEY,
        from_msisdn TEXT NOT NULL,
        to_msisdn TEXT NOT NULL,
        ts TEXT NOT NULL,
        text TEXT,
        created_at TEXT NOT NULL
    );""")
    conn.commit()
    return conn
