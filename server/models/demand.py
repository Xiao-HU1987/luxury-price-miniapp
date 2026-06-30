from sqlalchemy import Column, Integer, String, DateTime, Text, Float
from sqlalchemy.sql import func
from database import Base


class Demand(Base):
    __tablename__ = "demands"

    id = Column(Integer, primary_key=True, index=True)
    demand_id = Column(String(64), unique=True, index=True)
    user_id = Column(String(64), index=True)
    product_name = Column(String(255))
    brand_id = Column(String(32), default="")
    country = Column(String(8), default="")
    deadline = Column(String(32))
    budget = Column(Float, default=0)
    budget_currency = Column(String(8), default="CNY")
    quantity = Column(Integer, default=1)
    status = Column(String(16), default="bidding")
    bids = Column(Integer, default=0)
    matched_buyer_id = Column(String(64), default="")
    description = Column(Text, default="")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
