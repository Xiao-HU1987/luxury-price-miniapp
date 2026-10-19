from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.sql import func
from database import Base


class Brand(Base):
    __tablename__ = "brands"

    id = Column(Integer, primary_key=True, index=True)
    brand_id = Column(String(32), unique=True, index=True)
    name = Column(String(128))
    name_cn = Column(String(64))
    logo = Column(String(16), default="")
    category = Column(String(32), default="")
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Category(Base):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, index=True)
    category_id = Column(String(32), unique=True, index=True)
    name = Column(String(64))
    icon = Column(String(16), default="")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
