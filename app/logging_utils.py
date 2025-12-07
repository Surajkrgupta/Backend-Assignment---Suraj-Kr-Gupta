import logging, json, time
from datetime import datetime

class JSONFormatter(logging.Formatter):
    def format(self, record):
        data = {
            "ts": datetime.utcfromtimestamp(record.created).isoformat() + "Z",
            "level": record.levelname,
            "message": record.getMessage(),
        }
        if hasattr(record, "extra") and isinstance(record.extra, dict):
            data.update(record.extra)
        return json.dumps(data)

def setup_logging(level: str = "INFO"):
    handler = logging.StreamHandler()
    handler.setFormatter(JSONFormatter())
    root = logging.getLogger()
    root.setLevel(getattr(logging, level.upper(), logging.INFO))
    # remove default handlers
    if root.handlers:
        root.handlers = []
    root.addHandler(handler)
    return root
