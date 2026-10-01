"""MySQL connection factory. Credentials from environment -- never committed.
D22: no default password, ever. Missing env vars = hard stop."""
import os
from urllib.parse import quote_plus

from sqlalchemy import create_engine


def get_engine():
    user = os.environ.get("MYSQL_USER")
    pwd = os.environ.get("MYSQL_PASSWORD")
    if not user or not pwd:
        raise RuntimeError(
            "Set MYSQL_USER and MYSQL_PASSWORD environment variables first. "
            "No defaults, no secrets in code (see decisions.md D22).")
    host = os.environ.get("MYSQL_HOST", "127.0.0.1")
    port = os.environ.get("MYSQL_PORT", "3306")
    url = f"mysql+pymysql://{user}:{quote_plus(pwd)}@{host}:{port}/?charset=utf8mb4"
    return create_engine(url, pool_pre_ping=True)
