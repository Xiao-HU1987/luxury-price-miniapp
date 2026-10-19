from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from database import get_db
from models import Demand
from schemas import (
    ApiResponse,
    DemandCreateRequest,
    DemandUpdateRequest,
    DemandResponse,
)

router = APIRouter(prefix="/api/demand", tags=["寻买手需求"])


@router.get("/list", response_model=ApiResponse)
def get_demands(
    user_id: str = Query(None, description="用户ID"),
    brand_id: str = Query(None, description="品牌ID"),
    country: str = Query(None, description="国家"),
    status: str = Query(None, description="状态"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    query = db.query(Demand)
    
    if user_id:
        query = query.filter(Demand.user_id == user_id)
    
    if brand_id:
        query = query.filter(Demand.brand_id == brand_id)
    
    if country:
        query = query.filter(Demand.country == country)
    
    if status:
        query = query.filter(Demand.status == status)
    
    total = query.count()
    offset = (page - 1) * page_size
    demands = query.order_by(Demand.created_at.desc()).offset(offset).limit(page_size).all()
    
    return ApiResponse(
        code=0,
        message="success",
        data={
            "list": [DemandResponse.from_orm(d) for d in demands],
            "total": total,
            "page": page,
            "page_size": page_size
        }
    )


@router.get("/{demand_id}", response_model=ApiResponse)
def get_demand(demand_id: str, db: Session = Depends(get_db)):
    demand = db.query(Demand).filter(Demand.demand_id == demand_id).first()
    
    if not demand:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="需求不存在"
        )
    
    return ApiResponse(
        code=0,
        message="success",
        data=DemandResponse.from_orm(demand)
    )


@router.post("", response_model=ApiResponse)
def create_demand(request: DemandCreateRequest, db: Session = Depends(get_db)):
    existing = db.query(Demand).filter(Demand.demand_id == request.demand_id).first()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="需求ID已存在"
        )
    
    demand = Demand(
        demand_id=request.demand_id,
        user_id=request.user_id,
        product_name=request.product_name,
        brand_id=request.brand_id,
        country=request.country,
        deadline=request.deadline,
        budget=request.budget,
        budget_currency=request.budget_currency,
        quantity=request.quantity,
        description=request.description
    )
    
    db.add(demand)
    db.commit()
    db.refresh(demand)
    
    return ApiResponse(
        code=0,
        message="发布成功",
        data=DemandResponse.from_orm(demand)
    )


@router.put("/{demand_id}", response_model=ApiResponse)
def update_demand(demand_id: str, request: DemandUpdateRequest, db: Session = Depends(get_db)):
    demand = db.query(Demand).filter(Demand.demand_id == demand_id).first()
    
    if not demand:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="需求不存在"
        )
    
    if request.product_name is not None:
        demand.product_name = request.product_name
    if request.brand_id is not None:
        demand.brand_id = request.brand_id
    if request.country is not None:
        demand.country = request.country
    if request.deadline is not None:
        demand.deadline = request.deadline
    if request.budget is not None:
        demand.budget = request.budget
    if request.budget_currency is not None:
        demand.budget_currency = request.budget_currency
    if request.quantity is not None:
        demand.quantity = request.quantity
    if request.status is not None:
        demand.status = request.status
    if request.bids is not None:
        demand.bids = request.bids
    if request.matched_buyer_id is not None:
        demand.matched_buyer_id = request.matched_buyer_id
    if request.description is not None:
        demand.description = request.description
    
    db.commit()
    db.refresh(demand)
    
    return ApiResponse(
        code=0,
        message="更新成功",
        data=DemandResponse.from_orm(demand)
    )


@router.delete("/{demand_id}", response_model=ApiResponse)
def delete_demand(demand_id: str, db: Session = Depends(get_db)):
    demand = db.query(Demand).filter(Demand.demand_id == demand_id).first()
    
    if not demand:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="需求不存在"
        )
    
    db.delete(demand)
    db.commit()
    
    return ApiResponse(
        code=0,
        message="删除成功"
    )