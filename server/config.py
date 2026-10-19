import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent

# 加载 .env 文件中的环境变量（开发环境使用，生产环境建议通过系统环境变量配置）
load_dotenv(BASE_DIR / ".env")

SECRET_KEY = os.getenv("SECRET_KEY", "luxury-price-miniapp-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 60 * 24 * 7))

DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR / 'database.db'}")

WECHAT_APPID = os.getenv("WECHAT_APPID", "")
WECHAT_SECRET = os.getenv("WECHAT_SECRET", "")

WECHAT_MCH_ID = os.getenv("WECHAT_MCH_ID", "")
WECHAT_PAY_KEY = os.getenv("WECHAT_PAY_KEY", "")
WECHAT_NOTIFY_URL = os.getenv("WECHAT_NOTIFY_URL", "")

DEBUG = os.getenv("DEBUG", "True").lower() == "true"
