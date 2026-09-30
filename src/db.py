import os
from urllib.parse import quote_plus

from sqlalchemy import create_engine


def get_engine():
    user = os.environ.get("MYSQL_USER", "root")
    pwd = quote_plus(os.environ.get("MYSQL_PASSWORD", "***REMOVED***"))
    host = os.environ.get("MYSQL_HOST", "127.0.0.1")
    port = os.environ.get("MYSQL_PORT", "3306")
    url = f"mysql+pymysql://{user}:{pwd}@{host}:{port}/?charset=utf8mb4"
    return create_engine(url, pool_pre_ping=True)