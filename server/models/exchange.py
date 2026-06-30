from sqlalchemy import Column, Integer, String, DateTime, JSON
from sqlalchemy.sql import func
from database import Base


class ExchangeRate(Base):
    __tablename__ = "exchange_rates"

    id = Column(Integer, primary_key=True, index=True)
    base = Column(String(8), default="CNY")
    rates = Column(JSON)
    update_time = Column(DateTime(timezone=True), server_default=func.now())
