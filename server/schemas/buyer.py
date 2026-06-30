from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class BuyerCreateRequest(BaseModel):
    buyer_id: str = Field(..., description="买手ID")
    name: str = Field(..., description="买手名称")
    avatar: Optional[str] = Field("", description="头像")
    country: str = Field(..., description="国家")
    city: str = Field(..., description="城市")
    rating: Optional[float] = Field(5.0, description="评分")
    orders: Optional[int] = Field(0, description="完成订单数")
    fee_rate: Optional[float] = Field(10.0, description="服务费比例%")
    delivery_days: Optional[int] = Field(15, description="预计交货天数")
    intro: Optional[str] = Field("", description="介绍")


class BuyerUpdateRequest(BaseModel):
    name: Optional[str] = None
    avatar: Optional[str] = None
    country: Optional[str] = None
    city: Optional[str] = None
    rating: Optional[float] = None
    orders: Optional[int] = None
    fee_rate: Optional[float] = None
    delivery_days: Optional[int] = None
    intro: Optional[str] = None


class BuyerResponse(BaseModel):
    id: int
    buyer_id: str
    name: str
    avatar: str
    country: str
    city: str
    rating: float
    orders: int
    fee_rate: float
    delivery_days: int
    intro: str
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True