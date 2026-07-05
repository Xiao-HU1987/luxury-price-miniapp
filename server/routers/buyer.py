from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from database import get_db
from models import Buyer
from schemas import (
    ApiResponse,
    BuyerCreateRequest,
    BuyerUpdateRequest,
    BuyerResponse,
)
from utils.trino_db import TrinoClient, TrinoUnavailableError

router = APIRouter(prefix="/api/buyer", tags=["买手"])
trino_client = TrinoClient()


@router.get("/list", response_model=ApiResponse)
def get_buyers(
    country: str = Query(None, description="国家"),
    city: str = Query(None, description="城市"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    if trino_client.is_enabled():
        try:
            data = trino_client.get_buyer_list(country=country, city=city, page=page, page_size=page_size)
            return ApiResponse(code=0, message="success", data=data)
        except TrinoUnavailableError:
            pass

    query = db.query(Buyer)
    
    if country:
        query = query.filter(Buyer.country == country)
    
    if city:
        query = query.filter(Buyer.city == city)
    
    total = query.count()
    offset = (page - 1) * page_size
    buyers = query.order_by(Buyer.rating.desc()).offset(offset).limit(page_size).all()
    
    return ApiResponse(
        code=0,
        message="success",
        data={
            "list": [BuyerResponse.from_orm(b) for b in buyers],
            "total": total,
            "page": page,
            "page_size": page_size
        }
    )


@router.get("/{buyer_id}", response_model=ApiResponse)
def get_buyer(buyer_id: str, db: Session = Depends(get_db)):
    if trino_client.is_enabled():
        try:
            buyer = trino_client.get_buyer_detail(buyer_id)
            if not buyer:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="买手不存在"
                )
            return ApiResponse(code=0, message="success", data=buyer)
        except TrinoUnavailableError:
            pass

    buyer = db.query(Buyer).filter(Buyer.buyer_id == buyer_id).first()
    
    if not buyer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="买手不存在"
        )
    
    return ApiResponse(
        code=0,
        message="success",
        data=BuyerResponse.from_orm(buyer)
    )


@router.post("", response_model=ApiResponse)
def create_buyer(request: BuyerCreateRequest, db: Session = Depends(get_db)):
    existing = db.query(Buyer).filter(Buyer.buyer_id == request.buyer_id).first()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="买手ID已存在"
        )
    
    buyer = Buyer(
        buyer_id=request.buyer_id,
        name=request.name,
        avatar=request.avatar,
        country=request.country,
        city=request.city,
        rating=request.rating,
        orders=request.orders,
        fee_rate=request.fee_rate,
        delivery_days=request.delivery_days,
        intro=request.intro
    )
    
    db.add(buyer)
    db.commit()
    db.refresh(buyer)
    
    return ApiResponse(
        code=0,
        message="创建成功",
        data=BuyerResponse.from_orm(buyer)
    )


@router.put("/{buyer_id}", response_model=ApiResponse)
def update_buyer(buyer_id: str, request: BuyerUpdateRequest, db: Session = Depends(get_db)):
    buyer = db.query(Buyer).filter(Buyer.buyer_id == buyer_id).first()
    
    if not buyer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="买手不存在"
        )
    
    if request.name is not None:
        buyer.name = request.name
    if request.avatar is not None:
        buyer.avatar = request.avatar
    if request.country is not None:
        buyer.country = request.country
    if request.city is not None:
        buyer.city = request.city
    if request.rating is not None:
        buyer.rating = request.rating
    if request.orders is not None:
        buyer.orders = request.orders
    if request.fee_rate is not None:
        buyer.fee_rate = request.fee_rate
    if request.delivery_days is not None:
        buyer.delivery_days = request.delivery_days
    if request.intro is not None:
        buyer.intro = request.intro
    
    db.commit()
    db.refresh(buyer)
    
    return ApiResponse(
        code=0,
        message="更新成功",
        data=BuyerResponse.from_orm(buyer)
    )


@router.delete("/{buyer_id}", response_model=ApiResponse)
def delete_buyer(buyer_id: str, db: Session = Depends(get_db)):
    buyer = db.query(Buyer).filter(Buyer.buyer_id == buyer_id).first()
    
    if not buyer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="买手不存在"
        )
    
    db.delete(buyer)
    db.commit()
    
    return ApiResponse(
        code=0,
        message="删除成功"
    )