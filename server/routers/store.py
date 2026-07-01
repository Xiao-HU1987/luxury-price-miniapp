from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from database import get_db
from models import Store
from schemas import (
    ApiResponse,
    StoreCreateRequest,
    StoreUpdateRequest,
    StoreResponse,
)
from utils.trino_db import TrinoClient, TrinoUnavailableError

router = APIRouter(prefix="/api/store", tags=["商场店铺"])
trino_client = TrinoClient()


@router.get("/list", response_model=ApiResponse)
def get_stores(
    country: str = Query(None, description="国家"),
    city: str = Query(None, description="城市"),
    type: str = Query(None, description="类型"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    if trino_client.is_enabled():
        try:
            data = trino_client.get_store_list(country=country, city=city, type=type, page=page, page_size=page_size)
            return ApiResponse(code=0, message="success", data=data)
        except TrinoUnavailableError:
            pass

    query = db.query(Store)
    
    if country:
        query = query.filter(Store.country == country)
    
    if city:
        query = query.filter(Store.city == city)
    
    if type:
        query = query.filter(Store.type == type)
    
    total = query.count()
    offset = (page - 1) * page_size
    stores = query.order_by(Store.created_at.desc()).offset(offset).limit(page_size).all()
    
    return ApiResponse(
        code=0,
        message="success",
        data={
            "list": [StoreResponse.from_orm(s) for s in stores],
            "total": total,
            "page": page,
            "page_size": page_size
        }
    )


@router.get("/{store_id}", response_model=ApiResponse)
def get_store(store_id: str, db: Session = Depends(get_db)):
    if trino_client.is_enabled():
        try:
            store = trino_client.get_store_detail(store_id)
            if not store:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="店铺不存在"
                )
            return ApiResponse(code=0, message="success", data=store)
        except TrinoUnavailableError:
            pass

    store = db.query(Store).filter(Store.store_id == store_id).first()
    
    if not store:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="店铺不存在"
        )
    
    return ApiResponse(
        code=0,
        message="success",
        data=StoreResponse.from_orm(store)
    )


@router.post("", response_model=ApiResponse)
def create_store(request: StoreCreateRequest, db: Session = Depends(get_db)):
    existing = db.query(Store).filter(Store.store_id == request.store_id).first()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="店铺ID已存在"
        )
    
    store = Store(
        store_id=request.store_id,
        name=request.name,
        type=request.type,
        country=request.country,
        city=request.city,
        address=request.address,
        rating=request.rating,
        image=request.image
    )
    
    db.add(store)
    db.commit()
    db.refresh(store)
    
    return ApiResponse(
        code=0,
        message="创建成功",
        data=StoreResponse.from_orm(store)
    )


@router.put("/{store_id}", response_model=ApiResponse)
def update_store(store_id: str, request: StoreUpdateRequest, db: Session = Depends(get_db)):
    store = db.query(Store).filter(Store.store_id == store_id).first()
    
    if not store:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="店铺不存在"
        )
    
    if request.name is not None:
        store.name = request.name
    if request.type is not None:
        store.type = request.type
    if request.country is not None:
        store.country = request.country
    if request.city is not None:
        store.city = request.city
    if request.address is not None:
        store.address = request.address
    if request.rating is not None:
        store.rating = request.rating
    if request.image is not None:
        store.image = request.image
    
    db.commit()
    db.refresh(store)
    
    return ApiResponse(
        code=0,
        message="更新成功",
        data=StoreResponse.from_orm(store)
    )


@router.delete("/{store_id}", response_model=ApiResponse)
def delete_store(store_id: str, db: Session = Depends(get_db)):
    store = db.query(Store).filter(Store.store_id == store_id).first()
    
    if not store:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="店铺不存在"
        )
    
    db.delete(store)
    db.commit()
    
    return ApiResponse(
        code=0,
        message="删除成功"
    )