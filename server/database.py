from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from config import DATABASE_URL

# 按数据库类型区分连接参数
# - SQLite 需要 check_same_thread=False（FastAPI 多线程访问）
# - MySQL 不支持该参数，改为连接池配置
_is_sqlite = DATABASE_URL.startswith("sqlite")

if _is_sqlite:
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False}
    )
else:
    # MySQL / 其他数据库
    # pool_pre_ping: 使用前 ping 连接，避免长连接被 MySQL wait_timeout 断开
    # pool_recycle: 1 小时回收连接，比 MySQL 默认 wait_timeout(8h) 更短，保证连接新鲜
    engine = create_engine(
        DATABASE_URL,
        pool_pre_ping=True,
        pool_recycle=3600,
        pool_size=10,
        max_overflow=20,
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
