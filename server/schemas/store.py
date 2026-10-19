from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class StoreCreateRequest(BaseModel):
    store_id: str = Field(..., description="店铺ID")
    name: str = Field(..., description="店铺名称")
    type: str = Field("mall", description="类型：mall-商场，store-专卖店")
    country: str = Field(..., description="国家")
    city: str = Field(..., description="城市")
    address: Optional[str] = Field("", description="地址")
    rating: Optional[float] = Field(0.0, description="评分")
    image: Optional[str] = Field("", description="图片")


class StoreUpdateRequest(BaseModel):
    name: Optional[str] = None
    type: Optional[str] = None
    country: Optional[str] = None
    city: Optional[str] = None
    address: Optional[str] = None
    rating: Optional[float] = None
    image: Optional[str] = None


class StoreResponse(BaseModel):
    id: int
    store_id: str
    name: str
    type: str
    country: str
    city: str
    address: str
    rating: float
    image: str
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True