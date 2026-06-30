from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from database import get_db
from models import Rebate
from schemas import (
    ApiResponse,
    RebateCreateRequest,
    RebateUpdateRequest,
    RebateResponse,
)

router = APIRouter(prefix="/api/rebate", tags=["返点优惠"])


@router.get("/list", response_model=ApiResponse)
def get_rebates(
    country: str = Query(None, description="国家"),
    brand_id: str = Query(None, description="品牌ID"),
    is_vip: bool = Query(False, description="是否VIP用户"),
    status: str = Query(None, description="状态"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    query = db.query(Rebate)
    
    if country:
        query = query.filter(Rebate.country == country)
    
    if brand_id:
        query = query.filter(Rebate.brand_id == brand_id)
    
    if not is_vip:
        query = query.filter(Rebate.is_vip_only == False)
    
    if status:
        query = query.filter(Rebate.status == status)
    
    total = query.count()
    offset = (page - 1) * page_size
    rebates = query.order_by(Rebate.created_at.desc()).offset(offset).limit(page_size).all()
    
    return ApiResponse(
        code=0,
        message="success",
        data={
            "list": [RebateResponse.from_orm(r) for r in rebates],
            "total": total,
            "page": page,
            "page_size": page_size
        }
    )


@router.get("/{rebate_id}", response_model=ApiResponse)
def get_rebate(rebate_id: str, db: Session = Depends(get_db)):
    rebate = db.query(Rebate).filter(Rebate.rebate_id == rebate_id).first()
    
    if not rebate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="返点不存在"
        )
    
    return ApiResponse(
        code=0,
        message="success",
        data=RebateResponse.from_orm(rebate)
    )


@router.post("", response_model=ApiResponse)
def create_rebate(request: RebateCreateRequest, db: Session = Depends(get_db)):
    existing = db.query(Rebate).filter(Rebate.rebate_id == request.rebate_id).first()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="返点ID已存在"
        )
    
    rebate = Rebate(
        rebate_id=request.rebate_id,
        title=request.title,
        brand_id=request.brand_id,
        brand_name=request.brand_name,
        store_id=request.store_id,
        store_name=request.store_name,
        country=request.country,
        rate=request.rate,
        is_vip_only=request.is_vip_only,
        status=request.status,
        start_date=request.start_date,
        end_date=request.end_date,
        description=request.description
    )
    
    db.add(rebate)
    db.commit()
    db.refresh(rebate)
    
    return ApiResponse(
        code=0,
        message="创建成功",
        data=RebateResponse.from_orm(rebate)
    )


@router.put("/{rebate_id}", response_model=ApiResponse)
def update_rebate(rebate_id: str, request: RebateUpdateRequest, db: Session = Depends(get_db)):
    rebate = db.query(Rebate).filter(Rebate.rebate_id == rebate_id).first()
    
    if not rebate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="返点不存在"
        )
    
    if request.title is not None:
        rebate.title = request.title
    if request.brand_id is not None:
        rebate.brand_id = request.brand_id
    if request.brand_name is not None:
        rebate.brand_name = request.brand_name
    if request.store_id is not None:
        rebate.store_id = request.store_id
    if request.store_name is not None:
        rebate.store_name = request.store_name
    if request.country is not None:
        rebate.country = request.country
    if request.rate is not None:
        rebate.rate = request.rate
    if request.is_vip_only is not None:
        rebate.is_vip_only = request.is_vip_only
    if request.status is not None:
        rebate.status = request.status
    if request.start_date is not None:
        rebate.start_date = request.start_date
    if request.end_date is not None:
        rebate.end_date = request.end_date
    if request.description is not None:
        rebate.description = request.description
    
    db.commit()
    db.refresh(rebate)
    
    return ApiResponse(
        code=0,
        message="更新成功",
        data=RebateResponse.from_orm(rebate)
    )


@router.delete("/{rebate_id}", response_model=ApiResponse)
def delete_rebate(rebate_id: str, db: Session = Depends(get_db)):
    rebate = db.query(Rebate).filter(Rebate.rebate_id == rebate_id).first()
    
    if not rebate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="返点不存在"
        )
    
    db.delete(rebate)
    db.commit()
    
    return ApiResponse(
        code=0,
        message="删除成功"
    )