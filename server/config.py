import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

SECRET_KEY = "luxury-price-miniapp-secret-key-change-in-production"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7

DATABASE_URL = f"sqlite:///{BASE_DIR / 'database.db'}"

WECHAT_APPID = ""
WECHAT_SECRET = ""

DEBUG = True
