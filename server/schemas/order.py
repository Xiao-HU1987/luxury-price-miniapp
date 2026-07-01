from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class OrderCreateRequest(BaseModel):
    user_id: str
    buyer_id: Optional[str] = ""
    spu_id: Optional[str] = ""
    sku_id: Optional[str] = ""
    product_name: Optional[str] = ""
    product_image: Optional[str] = ""
    sku_spec: Optional[str] = ""
    quantity: Optional[int] = 1
    original_price: Optional[float] = 0
    original_currency: Optional[str] = "CNY"
    cny_price: Optional[float] = 0
    fee_rate: Optional[float] = 0
    fee_amount: Optional[float] = 0
    shipping_fee: Optional[float] = 0
    total_amount: Optional[float] = 0
    country: Optional[str] = ""
    store: Optional[str] = ""
    remark: Optional[str] = ""
    receiver_name: Optional[str] = ""
    receiver_phone: Optional[str] = ""
    receiver_address: Optional[str] = ""


class OrderUpdateRequest(BaseModel):
    status: Optional[str] = None
    tracking_no: Optional[str] = None
    tracking_company: Optional[str] = None
    receiver_name: Optional[str] = None
    receiver_phone: Optional[str] = None
    receiver_address: Optional[str] = None
    remark: Optional[str] = None


class OrderResponse(BaseModel):
    order_id: str
    user_id: str
    buyer_id: str
    buyer_name: str
    spu_id: str
    sku_id: str
    product_name: str
    product_image: str
    sku_spec: str
    quantity: int
    original_price: float
    original_currency: str
    cny_price: float
    fee_rate: float
    fee_amount: float
    shipping_fee: float
    total_amount: float
    status: str
    country: str
    store: str
    remark: str
    tracking_no: str
    tracking_company: str
    receiver_name: str
    receiver_phone: str
    receiver_address: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    paid_at: Optional[datetime] = None
    shipped_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None

    class Config:
        from_attributes = True
