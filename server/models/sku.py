from sqlalchemy import Column, Integer, String, DateTime, Text, Float
from sqlalchemy.sql import func
from database import Base


class SPU(Base):
    __tablename__ = "spus"

    id = Column(Integer, primary_key=True, index=True)
    spu_id = Column(String(64), unique=True, index=True)
    brand_id = Column(String(32), index=True)
    brand_name = Column(String(128))
    name = Column(String(255))
    name_en = Column(String(255), default="")
    article_no = Column(String(64), index=True)
    category_id = Column(String(32), index=True)
    image = Column(String(255), default="")
    description = Column(Text, default="")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class SKU(Base):
    __tablename__ = "skus"

    id = Column(Integer, primary_key=True, index=True)
    sku_id = Column(String(64), unique=True, index=True)
    spu_id = Column(String(64), index=True)
    name = Column(String(128))
    color = Column(String(64), default="")
    size = Column(String(32), default="")
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class SKUPrice(Base):
    __tablename__ = "sku_prices"

    id = Column(Integer, primary_key=True, index=True)
    sku_id = Column(String(64), index=True)
    country = Column(String(8), index=True)
    currency = Column(String(8))
    price = Column(Float)
    stock = Column(Integer, default=0)
    store = Column(String(128), default="")
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
