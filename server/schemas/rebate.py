from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class RebateCreateRequest(BaseModel):
    rebate_id: str = Field(..., description="返点ID")
    title: str = Field(..., description="返点标题")
    brand_id: Optional[str] = Field("", description="适用品牌ID")
    brand_name: Optional[str] = Field("", description="适用品牌名称")
    store_id: Optional[str] = Field("", description="适用店铺ID")
    store_name: Optional[str] = Field("", description="适用店铺名称")
    country: str = Field(..., description="国家")
    rate: float = Field(..., description="返点比例%")
    is_vip_only: Optional[bool] = Field(False, description="是否仅VIP可见")
    status: Optional[str] = Field("available", description="状态")
    start_date: Optional[str] = Field("", description="开始日期")
    end_date: Optional[str] = Field("", description="结束日期")
    description: Optional[str] = Field("", description="说明")


class RebateUpdateRequest(BaseModel):
    title: Optional[str] = None
    brand_id: Optional[str] = None
    brand_name: Optional[str] = None
    store_id: Optional[str] = None
    store_name: Optional[str] = None
    country: Optional[str] = None
    rate: Optional[float] = None
    is_vip_only: Optional[bool] = None
    status: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    description: Optional[str] = None


class RebateResponse(BaseModel):
    id: int
    rebate_id: str
    title: str
    brand_id: str
    brand_name: str
    store_id: str
    store_name: str
    country: str
    rate: float
    is_vip_only: bool
    status: str
    start_date: str
    end_date: str
    description: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True