from pydantic import BaseModel, Field
from typing import Dict, Optional
from datetime import datetime


class ExchangeRateUpdateRequest(BaseModel):
    base: str = Field("CNY", description="基准货币")
    rates: Dict[str, float] = Field(..., description="汇率数据，{货币代码: 汇率}")


class ExchangeRateResponse(BaseModel):
    id: int
    base: str
    rates: Dict[str, float]
    update_time: Optional[datetime] = None

    class Config:
        from_attributes = True


class ExchangeConvertRequest(BaseModel):
    from_currency: str = Field(..., description="源货币")
    to_currency: str = Field(..., description="目标货币")
    amount: float = Field(..., description="金额")


class ExchangeConvertResponse(BaseModel):
    from_currency: str
    to_currency: str
    amount: float
    result: float
    rate: float
    update_time: Optional[datetime] = None