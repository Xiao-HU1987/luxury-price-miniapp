from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from database import get_db
from models import ExchangeRate
from schemas import (
    ApiResponse,
    ExchangeRateUpdateRequest,
    ExchangeRateResponse,
    ExchangeConvertRequest,
    ExchangeConvertResponse,
)

router = APIRouter(prefix="/api/exchange", tags=["汇率"])


@router.get("/rates", response_model=ApiResponse)
def get_exchange_rates(db: Session = Depends(get_db)):
    latest = db.query(ExchangeRate).order_by(ExchangeRate.update_time.desc()).first()
    
    if not latest:
        return ApiResponse(
            code=0,
            message="success",
            data={
                "base": "CNY",
                "rates": {},
                "update_time": None
            }
        )
    
    return ApiResponse(
        code=0,
        message="success",
        data=ExchangeRateResponse.from_orm(latest)
    )


@router.get("/rates/{currency}", response_model=ApiResponse)
def get_exchange_rate(currency: str, db: Session = Depends(get_db)):
    latest = db.query(ExchangeRate).order_by(ExchangeRate.update_time.desc()).first()
    
    if not latest:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="汇率数据不存在"
        )
    
    rate = latest.rates.get(currency.upper())
    
    if rate is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"不支持的货币: {currency}"
        )
    
    return ApiResponse(
        code=0,
        message="success",
        data={
            "currency": currency.upper(),
            "rate": rate,
            "base": latest.base,
            "update_time": latest.update_time
        }
    )


@router.post("/rates", response_model=ApiResponse)
def update_exchange_rates(request: ExchangeRateUpdateRequest, db: Session = Depends(get_db)):
    rate = ExchangeRate(
        base=request.base,
        rates=request.rates
    )

    db.add(rate)
    db.commit()
    db.refresh(rate)

    return ApiResponse(
        code=0,
        message="汇率更新成功",
        data=ExchangeRateResponse.from_orm(rate)
    )


@router.put("/rates", response_model=ApiResponse)
def put_exchange_rates(request: ExchangeRateUpdateRequest, db: Session = Depends(get_db)):
    """更新汇率（与 POST /rates 功能一致，供管理后台 PUT 调用）"""
    rate = ExchangeRate(
        base=request.base,
        rates=request.rates
    )

    db.add(rate)
    db.commit()
    db.refresh(rate)

    return ApiResponse(
        code=0,
        message="汇率更新成功",
        data=ExchangeRateResponse.from_orm(rate)
    )


@router.post("/convert", response_model=ApiResponse)
def convert_currency(request: ExchangeConvertRequest, db: Session = Depends(get_db)):
    latest = db.query(ExchangeRate).order_by(ExchangeRate.update_time.desc()).first()
    
    if not latest:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="汇率数据不存在"
        )
    
    from_cur = request.from_currency.upper()
    to_cur = request.to_currency.upper()
    
    all_rates = latest.rates.copy()
    all_rates[latest.base] = 1.0
    
    from_rate = all_rates.get(from_cur)
    to_rate = all_rates.get(to_cur)
    
    if from_rate is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"不支持的源货币: {from_cur}"
        )
    
    if to_rate is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"不支持的目标货币: {to_cur}"
        )
    
    if from_rate == 0:
        result = 0
        rate = 0
    else:
        base_amount = request.amount / from_rate
        result = base_amount * to_rate
        rate = to_rate / from_rate
    
    return ApiResponse(
        code=0,
        message="success",
        data=ExchangeConvertResponse(
            from_currency=from_cur,
            to_currency=to_cur,
            amount=request.amount,
            result=round(result, 2),
            rate=round(rate, 6),
            update_time=latest.update_time
        )
    )