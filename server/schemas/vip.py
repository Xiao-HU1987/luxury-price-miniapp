from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from decimal import Decimal


class VipPlanResponse(BaseModel):
    id: int
    plan_id: str
    name: str
    description: str
    duration_days: int
    price: float
    original_price: float
    is_popular: bool
    is_active: bool
    sort_order: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class VipOrderCreateRequest(BaseModel):
    plan_id: str


class VipOrderResponse(BaseModel):
    id: int
    order_no: str
    user_id: str
    plan_id: str
    plan_name: str
    duration_days: int
    amount: float
    status: str
    pay_type: str
    transaction_id: str
    paid_at: Optional[datetime] = None
    expire_time: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class VipPayResponse(BaseModel):
    order_no: str
    pay_params: dict
