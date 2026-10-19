from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.sql import func
from database import Base


class UserCoupon(Base):
    __tablename__ = "user_coupons"

    id = Column(Integer, primary_key=True, index=True)
    user_coupon_id = Column(String(64), unique=True, index=True)
    user_id = Column(String(64), index=True)
    coupon_id = Column(String(64), index=True)
    status = Column(String(32), default="available")
    obtained_at = Column(DateTime(timezone=True), server_default=func.now())
    used_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
