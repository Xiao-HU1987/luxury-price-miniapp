from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from database import get_db
from models import Coupon
from schemas import (
    ApiResponse,
    CouponCreateRequest,
    CouponUpdateRequest,
    CouponResponse,
)

router = APIRouter(prefix="/api/coupon", tags=["优惠券"])


@router.get("/list", response_model=ApiResponse)
def get_coupons(
    country: str = Query(None, description="国家代码"),
    store_id: str = Query(None, description="店铺ID"),
    status: str = Query(None, description="状态"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    query = db.query(Coupon)
    
    if country:
        query = query.filter(Coupon.country == country)
    
    if store_id:
        query = query.filter(Coupon.store_id == store_id)
    
    if status:
        query = query.filter(Coupon.status == status)
    
    total = query.count()
    offset = (page - 1) * page_size
    coupons = query.order_by(Coupon.created_at.desc()).offset(offset).limit(page_size).all()
    
    return ApiResponse(
        code=0,
        message="success",
        data={
            "list": [CouponResponse.from_orm(c) for c in coupons],
            "total": total,
            "page": page,
            "page_size": page_size
        }
    )


@router.get("/{coupon_id}", response_model=ApiResponse)
def get_coupon(coupon_id: str, db: Session = Depends(get_db)):
    coupon = db.query(Coupon).filter(Coupon.coupon_id == coupon_id).first()
    
    if not coupon:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="优惠券不存在"
        )
    
    return ApiResponse(
        code=0,
        message="success",
        data=CouponResponse.from_orm(coupon)
    )


@router.post("", response_model=ApiResponse)
def create_coupon(request: CouponCreateRequest, db: Session = Depends(get_db)):
    existing = db.query(Coupon).filter(Coupon.coupon_id == request.coupon_id).first()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="优惠券ID已存在"
        )
    
    coupon = Coupon(
        coupon_id=request.coupon_id,
        title=request.title,
        type=request.type,
        discount=request.discount,
        threshold=request.threshold,
        country=request.country,
        store_id=request.store_id,
        store_name=request.store_name,
        expire_date=request.expire_date,
        status=request.status
    )
    
    db.add(coupon)
    db.commit()
    db.refresh(coupon)
    
    return ApiResponse(
        code=0,
        message="创建成功",
        data=CouponResponse.from_orm(coupon)
    )


@router.put("/{coupon_id}", response_model=ApiResponse)
def update_coupon(coupon_id: str, request: CouponUpdateRequest, db: Session = Depends(get_db)):
    coupon = db.query(Coupon).filter(Coupon.coupon_id == coupon_id).first()
    
    if not coupon:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="优惠券不存在"
        )
    
    if request.title is not None:
        coupon.title = request.title
    if request.type is not None:
        coupon.type = request.type
    if request.discount is not None:
        coupon.discount = request.discount
    if request.threshold is not None:
        coupon.threshold = request.threshold
    if request.country is not None:
        coupon.country = request.country
    if request.store_id is not None:
        coupon.store_id = request.store_id
    if request.store_name is not None:
        coupon.store_name = request.store_name
    if request.expire_date is not None:
        coupon.expire_date = request.expire_date
    if request.status is not None:
        coupon.status = request.status
    
    db.commit()
    db.refresh(coupon)
    
    return ApiResponse(
        code=0,
        message="更新成功",
        data=CouponResponse.from_orm(coupon)
    )


@router.delete("/{coupon_id}", response_model=ApiResponse)
def delete_coupon(coupon_id: str, db: Session = Depends(get_db)):
    coupon = db.query(Coupon).filter(Coupon.coupon_id == coupon_id).first()
    
    if not coupon:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="优惠券不存在"
        )
    
    db.delete(coupon)
    db.commit()
    
    return ApiResponse(
        code=0,
        message="删除成功"
    )