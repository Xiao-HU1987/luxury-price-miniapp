import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

SECRET_KEY = os.getenv("SECRET_KEY", "luxury-price-miniapp-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 60 * 24 * 7))

DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR / 'database.db'}")

WECHAT_APPID = os.getenv("WECHAT_APPID", "")
WECHAT_SECRET = os.getenv("WECHAT_SECRET", "")

WECHAT_MCH_ID = os.getenv("WECHAT_MCH_ID", "")
WECHAT_PAY_KEY = os.getenv("WECHAT_PAY_KEY", "")
WECHAT_NOTIFY_URL = os.getenv("WECHAT_NOTIFY_URL", "")

TRINO_ENABLED = os.getenv("TRINO_ENABLED", "true").lower() == "true"
TRINO_HOST = os.getenv("TRINO_HOST", "localhost")
TRINO_PORT = int(os.getenv("TRINO_PORT", "8080"))
TRINO_USER = os.getenv("TRINO_USER", "trino")
TRINO_PASSWORD = os.getenv("TRINO_PASSWORD", "")
TRINO_CATALOG = os.getenv("TRINO_CATALOG", "hive")
TRINO_SCHEMA = os.getenv("TRINO_SCHEMA", "default")
TRINO_HTTP_SCHEME = os.getenv("TRINO_HTTP_SCHEME", "http")
TRINO_SOURCE = os.getenv("TRINO_SOURCE", "luxury-price-miniapp")

DEBUG = os.getenv("DEBUG", "True").lower() == "true"
