from sqlalchemy import Column, Integer, String, DateTime, Text, Float
from sqlalchemy.sql import func
from database import Base


class Store(Base):
    __tablename__ = "stores"

    id = Column(Integer, primary_key=True, index=True)
    store_id = Column(String(32), unique=True, index=True)
    name = Column(String(128))
    type = Column(String(16), default="mall")
    country = Column(String(8), index=True)
    city = Column(String(64))
    address = Column(String(255), default="")
    rating = Column(Float, default=0.0)
    image = Column(String(255), default="")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
