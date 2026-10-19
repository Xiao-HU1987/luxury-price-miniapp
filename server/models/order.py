from sqlalchemy import Column, Integer, String, DateTime, Float, Text
from sqlalchemy.sql import func
from database import Base


class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(String(64), unique=True, index=True)
    user_id = Column(String(64), index=True)
    buyer_id = Column(String(64), index=True, default="")
    buyer_name = Column(String(64), default="")
    spu_id = Column(String(64), default="")
    sku_id = Column(String(64), default="")
    product_name = Column(String(255), default="")
    product_image = Column(String(255), default="")
    sku_spec = Column(String(255), default="")
    quantity = Column(Integer, default=1)
    original_price = Column(Float, default=0)
    original_currency = Column(String(16), default="CNY")
    cny_price = Column(Float, default=0)
    fee_rate = Column(Float, default=0)
    fee_amount = Column(Float, default=0)
    shipping_fee = Column(Float, default=0)
    total_amount = Column(Float, default=0)
    status = Column(String(32), default="pending")
    country = Column(String(16), default="")
    store = Column(String(128), default="")
    remark = Column(Text, default="")
    tracking_no = Column(String(64), default="")
    tracking_company = Column(String(64), default="")
    receiver_name = Column(String(64), default="")
    receiver_phone = Column(String(20), default="")
    receiver_address = Column(String(255), default="")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    paid_at = Column(DateTime(timezone=True), nullable=True)
    shipped_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    cancelled_at = Column(DateTime(timezone=True), nullable=True)
