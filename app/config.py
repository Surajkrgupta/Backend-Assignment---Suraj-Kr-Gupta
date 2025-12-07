import os
from urllib.parse import urlparse

# DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./app.db")
# config.py
DATABASE_URL = "sqlite:///./data/mydb.sqlite"

WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
