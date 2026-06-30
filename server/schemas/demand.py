from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class DemandCreateRequest(BaseModel):
    demand_id: str = Field(..., description="需求ID")
    user_id: str = Field(..., description="发布用户ID")
    product_name: str = Field(..., description="商品名称")
    brand_id: Optional[str] = Field("", description="品牌ID")
    country: Optional[str] = Field("", description="期望国家")
    deadline: str = Field(..., description="期望交货日期")
    budget: Optional[float] = Field(0, description="预算")
    budget_currency: Optional[str] = Field("CNY", description="预算货币")
    quantity: Optional[int] = Field(1, description="数量")
    description: Optional[str] = Field("", description="详细描述")


class DemandUpdateRequest(BaseModel):
    product_name: Optional[str] = None
    brand_id: Optional[str] = None
    country: Optional[str] = None
    deadline: Optional[str] = None
    budget: Optional[float] = None
    budget_currency: Optional[str] = None
    quantity: Optional[int] = None
    status: Optional[str] = None
    bids: Optional[int] = None
    matched_buyer_id: Optional[str] = None
    description: Optional[str] = None


class DemandResponse(BaseModel):
    id: int
    demand_id: str
    user_id: str
    product_name: str
    brand_id: str
    country: str
    deadline: str
    budget: float
    budget_currency: str
    quantity: int
    status: str
    bids: int
    matched_buyer_id: str
    description: str
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True