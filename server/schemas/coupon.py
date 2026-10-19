from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class CouponCreateRequest(BaseModel):
    coupon_id: str = Field(..., description="优惠券ID")
    title: str = Field(..., description="优惠券标题")
    type: str = Field("discount", description="类型：discount-折扣券，cash-满减券")
    discount: float = Field(0, description="折扣比例或减免金额")
    threshold: float = Field(0, description="使用门槛")
    country: str = Field(..., description="适用国家")
    store_id: Optional[str] = Field("", description="适用店铺ID")
    store_name: Optional[str] = Field("", description="适用店铺名称")
    expire_date: str = Field(..., description="有效期截止日期")
    status: Optional[str] = Field("available", description="状态")


class CouponUpdateRequest(BaseModel):
    title: Optional[str] = None
    type: Optional[str] = None
    discount: Optional[float] = None
    threshold: Optional[float] = None
    country: Optional[str] = None
    store_id: Optional[str] = None
    store_name: Optional[str] = None
    expire_date: Optional[str] = None
    status: Optional[str] = None


class CouponResponse(BaseModel):
    id: int
    coupon_id: str
    title: str
    type: str
    discount: float
    threshold: float
    country: str
    store_id: str
    store_name: str
    expire_date: str
    status: str
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True