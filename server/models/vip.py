from sqlalchemy import Column, Integer, String, DateTime, Boolean, Numeric, Text
from sqlalchemy.sql import func
from database import Base


class VipPlan(Base):
    __tablename__ = "vip_plans"

    id = Column(Integer, primary_key=True, index=True)
    plan_id = Column(String(32), unique=True, index=True)
    name = Column(String(64), default="")
    description = Column(String(255), default="")
    duration_days = Column(Integer, default=30)
    price = Column(Numeric(10, 2), default=0)
    original_price = Column(Numeric(10, 2), default=0)
    is_popular = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    sort_order = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class VipOrder(Base):
    __tablename__ = "vip_orders"

    id = Column(Integer, primary_key=True, index=True)
    order_no = Column(String(64), unique=True, index=True)
    user_id = Column(String(64), index=True)
    plan_id = Column(String(32), default="")
    plan_name = Column(String(64), default="")
    duration_days = Column(Integer, default=30)
    amount = Column(Numeric(10, 2), default=0)
    status = Column(String(16), default="pending")
    pay_type = Column(String(16), default="wechat")
    transaction_id = Column(String(64), default="")
    paid_at = Column(DateTime(timezone=True), nullable=True)
    expire_time = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
