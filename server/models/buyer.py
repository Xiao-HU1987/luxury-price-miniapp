from sqlalchemy import Column, Integer, String, DateTime, Float, Text
from sqlalchemy.sql import func
from database import Base


class Buyer(Base):
    __tablename__ = "buyers"

    id = Column(Integer, primary_key=True, index=True)
    buyer_id = Column(String(64), unique=True, index=True)
    name = Column(String(128))
    avatar = Column(String(255), default="")
    country = Column(String(8), index=True)
    city = Column(String(64))
    rating = Column(Float, default=5.0)
    orders = Column(Integer, default=0)
    fee_rate = Column(Float, default=10.0)
    delivery_days = Column(Integer, default=15)
    intro = Column(Text, default="")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
