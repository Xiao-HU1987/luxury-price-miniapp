from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from pydantic import BaseModel
from typing import Optional, List, Any
import uuid
import json

from database import get_db
from models import (
    User, Brand, Category, SPU, SKU, SKUPrice, Store,
    Coupon, Buyer, Demand, ExchangeRate, Rebate
)
from utils.security import get_current_admin

router = APIRouter(prefix="/api/admin", tags=["管理端"], dependencies=[Depends(get_current_admin)])


def paginate_query(query, page: int = 1, page_size: int = 20):
    total = query.count()
    items = query.offset((page - 1) * page_size).limit(page_size).all()
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "list": items
    }


# ============ 仪表盘 ============
@router.get("/dashboard/stats")
def get_dashboard_stats(db: Session = Depends(get_db)):
    stats = {
        "total_products": db.query(SPU).count(),
        "total_brands": db.query(Brand).count(),
        "total_buyers": db.query(Buyer).count(),
        "total_demands": db.query(Demand).count(),
        "total_coupons": db.query(Coupon).count(),
        "total_stores": db.query(Store).count(),
        "total_users": db.query(User).count(),
        "total_rebates": db.query(Rebate).count(),
    }
    return {"code": 0, "message": "success", "data": stats}


# ============ 用户管理 ============
@router.get("/users")
def list_users(
    page: int = 1,
    page_size: int = 20,
    keyword: Optional[str] = None,
    db: Session = Depends(get_db)
):
    query = db.query(User)
    if keyword:
        query = query.filter(
            (User.nickname.contains(keyword)) |
            (User.phone.contains(keyword)) |
            (User.user_id.contains(keyword))
        )
    query = query.order_by(desc(User.created_at))
    result = paginate_query(query, page, page_size)
    return {"code": 0, "message": "success", "data": result}


class UserUpdateRequest(BaseModel):
    nickname: Optional[str] = None
    phone: Optional[str] = None
    is_vip: Optional[bool] = None
    is_admin: Optional[bool] = None
    status: Optional[str] = None
    password: Optional[str] = None


@router.put("/users/{user_id}")
def update_user(user_id: str, request: UserUpdateRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    if request.nickname is not None:
        user.nickname = request.nickname
    if request.phone is not None:
        user.phone = request.phone
    if request.is_vip is not None:
        user.is_vip = request.is_vip
    if request.is_admin is not None:
        user.is_admin = request.is_admin
    if request.status is not None:
        user.status = request.status
    if request.password:
        from utils.security import get_password_hash
        user.password_hash = get_password_hash(request.password)
    db.commit()
    db.refresh(user)
    return {"code": 0, "message": "success", "data": user}


@router.delete("/users/{user_id}")
def delete_user(user_id: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    db.delete(user)
    db.commit()
    return {"code": 0, "message": "success"}


# ============ 品牌管理 ============
@router.get("/brands")
def list_brands(
    page: int = 1,
    page_size: int = 20,
    keyword: Optional[str] = None,
    db: Session = Depends(get_db)
):
    query = db.query(Brand)
    if keyword:
        query = query.filter(
            (Brand.name.contains(keyword)) |
            (Brand.name_cn.contains(keyword))
        )
    query = query.order_by(desc(Brand.created_at))
    result = paginate_query(query, page, page_size)
    return {"code": 0, "message": "success", "data": result}


class BrandCreateRequest(BaseModel):
    brand_id: str
    name: str
    name_cn: str
    logo: Optional[str] = ""
    category: Optional[str] = ""


@router.post("/brands")
def create_brand(request: BrandCreateRequest, db: Session = Depends(get_db)):
    existing = db.query(Brand).filter(Brand.brand_id == request.brand_id).first()
    if existing:
        raise HTTPException(status_code=400, detail="品牌ID已存在")
    brand = Brand(**request.model_dump())
    db.add(brand)
    db.commit()
    db.refresh(brand)
    return {"code": 0, "message": "success", "data": brand}


@router.put("/brands/{brand_id}")
def update_brand(brand_id: str, request: BrandCreateRequest, db: Session = Depends(get_db)):
    brand = db.query(Brand).filter(Brand.brand_id == brand_id).first()
    if not brand:
        raise HTTPException(status_code=404, detail="品牌不存在")
    for key, value in request.model_dump().items():
        if value is not None:
            setattr(brand, key, value)
    db.commit()
    db.refresh(brand)
    return {"code": 0, "message": "success", "data": brand}


@router.delete("/brands/{brand_id}")
def delete_brand(brand_id: str, db: Session = Depends(get_db)):
    brand = db.query(Brand).filter(Brand.brand_id == brand_id).first()
    if not brand:
        raise HTTPException(status_code=404, detail="品牌不存在")
    db.delete(brand)
    db.commit()
    return {"code": 0, "message": "success"}


# ============ 品类管理 ============
@router.get("/categories")
def list_categories(
    page: int = 1,
    page_size: int = 20,
    keyword: Optional[str] = None,
    db: Session = Depends(get_db)
):
    query = db.query(Category)
    if keyword:
        query = query.filter(Category.name.contains(keyword))
    query = query.order_by(desc(Category.created_at))
    result = paginate_query(query, page, page_size)
    return {"code": 0, "message": "success", "data": result}


class CategoryCreateRequest(BaseModel):
    category_id: str
    name: str
    icon: Optional[str] = ""


@router.post("/categories")
def create_category(request: CategoryCreateRequest, db: Session = Depends(get_db)):
    existing = db.query(Category).filter(Category.category_id == request.category_id).first()
    if existing:
        raise HTTPException(status_code=400, detail="品类ID已存在")
    category = Category(**request.model_dump())
    db.add(category)
    db.commit()
    db.refresh(category)
    return {"code": 0, "message": "success", "data": category}


@router.put("/categories/{category_id}")
def update_category(category_id: str, request: CategoryCreateRequest, db: Session = Depends(get_db)):
    category = db.query(Category).filter(Category.category_id == category_id).first()
    if not category:
        raise HTTPException(status_code=404, detail="品类不存在")
    for key, value in request.model_dump().items():
        if value is not None:
            setattr(category, key, value)
    db.commit()
    db.refresh(category)
    return {"code": 0, "message": "success", "data": category}


@router.delete("/categories/{category_id}")
def delete_category(category_id: str, db: Session = Depends(get_db)):
    category = db.query(Category).filter(Category.category_id == category_id).first()
    if not category:
        raise HTTPException(status_code=404, detail="品类不存在")
    db.delete(category)
    db.commit()
    return {"code": 0, "message": "success"}


# ============ 商品管理(SPU) ============
@router.get("/products")
def list_products(
    page: int = 1,
    page_size: int = 20,
    keyword: Optional[str] = None,
    brand_id: Optional[str] = None,
    category_id: Optional[str] = None,
    db: Session = Depends(get_db)
):
    query = db.query(SPU)
    if keyword:
        query = query.filter(
            (SPU.name.contains(keyword)) |
            (SPU.name_en.contains(keyword)) |
            (SPU.article_no.contains(keyword))
        )
    if brand_id:
        query = query.filter(SPU.brand_id == brand_id)
    if category_id:
        query = query.filter(SPU.category_id == category_id)
    query = query.order_by(desc(SPU.created_at))
    result = paginate_query(query, page, page_size)
    return {"code": 0, "message": "success", "data": result}


@router.get("/products/{spu_id}")
def get_product_detail(spu_id: str, db: Session = Depends(get_db)):
    spu = db.query(SPU).filter(SPU.spu_id == spu_id).first()
    if not spu:
        raise HTTPException(status_code=404, detail="商品不存在")
    skus = db.query(SKU).filter(SKU.spu_id == spu_id).all()
    sku_list = []
    for sku in skus:
        prices = db.query(SKUPrice).filter(SKUPrice.sku_id == sku.sku_id).all()
        sku_dict = {
            "sku_id": sku.sku_id,
            "name": sku.name,
            "color": sku.color,
            "size": sku.size,
            "prices": [
                {
                    "country": p.country,
                    "currency": p.currency,
                    "price": p.price,
                    "stock": p.stock,
                    "store": p.store
                }
                for p in prices
            ]
        }
        sku_list.append(sku_dict)
    return {
        "code": 0,
        "message": "success",
        "data": {
            "spu": spu,
            "skus": sku_list
        }
    }


class SPUCreateRequest(BaseModel):
    spu_id: str
    brand_id: str
    brand_name: str
    name: str
    name_en: Optional[str] = ""
    article_no: str
    category_id: str
    image: Optional[str] = ""
    description: Optional[str] = ""


@router.post("/products")
def create_product(request: SPUCreateRequest, db: Session = Depends(get_db)):
    existing = db.query(SPU).filter(SPU.spu_id == request.spu_id).first()
    if existing:
        raise HTTPException(status_code=400, detail="商品ID已存在")
    spu = SPU(**request.model_dump())
    db.add(spu)
    db.commit()
    db.refresh(spu)
    return {"code": 0, "message": "success", "data": spu}


@router.put("/products/{spu_id}")
def update_product(spu_id: str, request: SPUCreateRequest, db: Session = Depends(get_db)):
    spu = db.query(SPU).filter(SPU.spu_id == spu_id).first()
    if not spu:
        raise HTTPException(status_code=404, detail="商品不存在")
    for key, value in request.model_dump().items():
        if value is not None:
            setattr(spu, key, value)
    db.commit()
    db.refresh(spu)
    return {"code": 0, "message": "success", "data": spu}


@router.delete("/products/{spu_id}")
def delete_product(spu_id: str, db: Session = Depends(get_db)):
    spu = db.query(SPU).filter(SPU.spu_id == spu_id).first()
    if not spu:
        raise HTTPException(status_code=404, detail="商品不存在")
    skus = db.query(SKU).filter(SKU.spu_id == spu_id).all()
    for sku in skus:
        db.query(SKUPrice).filter(SKUPrice.sku_id == sku.sku_id).delete()
        db.delete(sku)
    db.delete(spu)
    db.commit()
    return {"code": 0, "message": "success"}


# ============ SKU管理 ============
class SKUPriceItem(BaseModel):
    country: str
    currency: str
    price: float
    stock: int = 0
    store: str = ""


class SKUCreateRequest(BaseModel):
    sku_id: str
    spu_id: str
    name: str
    color: Optional[str] = ""
    size: Optional[str] = ""
    prices: List[SKUPriceItem] = []


@router.post("/skus")
def create_sku(request: SKUCreateRequest, db: Session = Depends(get_db)):
    existing = db.query(SKU).filter(SKU.sku_id == request.sku_id).first()
    if existing:
        raise HTTPException(status_code=400, detail="SKU ID已存在")
    sku_data = request.model_dump(exclude={"prices"})
    sku = SKU(**sku_data)
    db.add(sku)
    db.flush()

    for price_item in request.prices:
        sku_price = SKUPrice(
            sku_id=request.sku_id,
            **price_item.model_dump()
        )
        db.add(sku_price)

    db.commit()
    db.refresh(sku)
    return {"code": 0, "message": "success", "data": sku}


@router.put("/skus/{sku_id}")
def update_sku(sku_id: str, request: SKUCreateRequest, db: Session = Depends(get_db)):
    sku = db.query(SKU).filter(SKU.sku_id == sku_id).first()
    if not sku:
        raise HTTPException(status_code=404, detail="SKU不存在")
    sku.name = request.name
    sku.color = request.color
    sku.size = request.size
    sku.spu_id = request.spu_id

    db.query(SKUPrice).filter(SKUPrice.sku_id == sku_id).delete()
    for price_item in request.prices:
        sku_price = SKUPrice(
            sku_id=sku_id,
            **price_item.model_dump()
        )
        db.add(sku_price)

    db.commit()
    db.refresh(sku)
    return {"code": 0, "message": "success", "data": sku}


@router.delete("/skus/{sku_id}")
def delete_sku(sku_id: str, db: Session = Depends(get_db)):
    sku = db.query(SKU).filter(SKU.sku_id == sku_id).first()
    if not sku:
        raise HTTPException(status_code=404, detail="SKU不存在")
    db.query(SKUPrice).filter(SKUPrice.sku_id == sku_id).delete()
    db.delete(sku)
    db.commit()
    return {"code": 0, "message": "success"}


# ============ 门店管理 ============
@router.get("/stores")
def list_stores(
    page: int = 1,
    page_size: int = 20,
    keyword: Optional[str] = None,
    country: Optional[str] = None,
    db: Session = Depends(get_db)
):
    query = db.query(Store)
    if keyword:
        query = query.filter(Store.name.contains(keyword))
    if country:
        query = query.filter(Store.country == country)
    query = query.order_by(desc(Store.created_at))
    result = paginate_query(query, page, page_size)
    return {"code": 0, "message": "success", "data": result}


class StoreCreateRequest(BaseModel):
    store_id: str
    name: str
    type: Optional[str] = "mall"
    country: str
    city: str
    address: Optional[str] = ""
    rating: Optional[float] = 0.0
    image: Optional[str] = ""


@router.post("/stores")
def create_store(request: StoreCreateRequest, db: Session = Depends(get_db)):
    existing = db.query(Store).filter(Store.store_id == request.store_id).first()
    if existing:
        raise HTTPException(status_code=400, detail="门店ID已存在")
    store = Store(**request.model_dump())
    db.add(store)
    db.commit()
    db.refresh(store)
    return {"code": 0, "message": "success", "data": store}


@router.put("/stores/{store_id}")
def update_store(store_id: str, request: StoreCreateRequest, db: Session = Depends(get_db)):
    store = db.query(Store).filter(Store.store_id == store_id).first()
    if not store:
        raise HTTPException(status_code=404, detail="门店不存在")
    for key, value in request.model_dump().items():
        if value is not None:
            setattr(store, key, value)
    db.commit()
    db.refresh(store)
    return {"code": 0, "message": "success", "data": store}


@router.delete("/stores/{store_id}")
def delete_store(store_id: str, db: Session = Depends(get_db)):
    store = db.query(Store).filter(Store.store_id == store_id).first()
    if not store:
        raise HTTPException(status_code=404, detail="门店不存在")
    db.delete(store)
    db.commit()
    return {"code": 0, "message": "success"}


# ============ 优惠券管理 ============
@router.get("/coupons")
def list_coupons(
    page: int = 1,
    page_size: int = 20,
    keyword: Optional[str] = None,
    status: Optional[str] = None,
    country: Optional[str] = None,
    db: Session = Depends(get_db)
):
    query = db.query(Coupon)
    if keyword:
        query = query.filter(Coupon.title.contains(keyword))
    if status:
        query = query.filter(Coupon.status == status)
    if country:
        query = query.filter(Coupon.country == country)
    query = query.order_by(desc(Coupon.created_at))
    result = paginate_query(query, page, page_size)
    return {"code": 0, "message": "success", "data": result}


class CouponCreateRequest(BaseModel):
    coupon_id: str
    title: str
    type: Optional[str] = "discount"
    discount: Optional[float] = 0
    threshold: Optional[float] = 0
    country: str
    store_id: Optional[str] = ""
    store_name: Optional[str] = ""
    expire_date: str
    status: Optional[str] = "available"


@router.post("/coupons")
def create_coupon(request: CouponCreateRequest, db: Session = Depends(get_db)):
    existing = db.query(Coupon).filter(Coupon.coupon_id == request.coupon_id).first()
    if existing:
        raise HTTPException(status_code=400, detail="优惠券ID已存在")
    coupon = Coupon(**request.model_dump())
    db.add(coupon)
    db.commit()
    db.refresh(coupon)
    return {"code": 0, "message": "success", "data": coupon}


@router.put("/coupons/{coupon_id}")
def update_coupon(coupon_id: str, request: CouponCreateRequest, db: Session = Depends(get_db)):
    coupon = db.query(Coupon).filter(Coupon.coupon_id == coupon_id).first()
    if not coupon:
        raise HTTPException(status_code=404, detail="优惠券不存在")
    for key, value in request.model_dump().items():
        if value is not None:
            setattr(coupon, key, value)
    db.commit()
    db.refresh(coupon)
    return {"code": 0, "message": "success", "data": coupon}


@router.delete("/coupons/{coupon_id}")
def delete_coupon(coupon_id: str, db: Session = Depends(get_db)):
    coupon = db.query(Coupon).filter(Coupon.coupon_id == coupon_id).first()
    if not coupon:
        raise HTTPException(status_code=404, detail="优惠券不存在")
    db.delete(coupon)
    db.commit()
    return {"code": 0, "message": "success"}


# ============ 买手管理 ============
@router.get("/buyers")
def list_buyers(
    page: int = 1,
    page_size: int = 20,
    keyword: Optional[str] = None,
    country: Optional[str] = None,
    db: Session = Depends(get_db)
):
    query = db.query(Buyer)
    if keyword:
        query = query.filter(Buyer.name.contains(keyword))
    if country:
        query = query.filter(Buyer.country == country)
    query = query.order_by(desc(Buyer.created_at))
    result = paginate_query(query, page, page_size)
    return {"code": 0, "message": "success", "data": result}


class BuyerCreateRequest(BaseModel):
    buyer_id: str
    name: str
    avatar: Optional[str] = ""
    country: str
    city: str
    rating: Optional[float] = 5.0
    orders: Optional[int] = 0
    fee_rate: Optional[float] = 10.0
    delivery_days: Optional[int] = 15
    intro: Optional[str] = ""


@router.post("/buyers")
def create_buyer(request: BuyerCreateRequest, db: Session = Depends(get_db)):
    existing = db.query(Buyer).filter(Buyer.buyer_id == request.buyer_id).first()
    if existing:
        raise HTTPException(status_code=400, detail="买手ID已存在")
    buyer = Buyer(**request.model_dump())
    db.add(buyer)
    db.commit()
    db.refresh(buyer)
    return {"code": 0, "message": "success", "data": buyer}


@router.put("/buyers/{buyer_id}")
def update_buyer(buyer_id: str, request: BuyerCreateRequest, db: Session = Depends(get_db)):
    buyer = db.query(Buyer).filter(Buyer.buyer_id == buyer_id).first()
    if not buyer:
        raise HTTPException(status_code=404, detail="买手不存在")
    for key, value in request.model_dump().items():
        if value is not None:
            setattr(buyer, key, value)
    db.commit()
    db.refresh(buyer)
    return {"code": 0, "message": "success", "data": buyer}


@router.delete("/buyers/{buyer_id}")
def delete_buyer(buyer_id: str, db: Session = Depends(get_db)):
    buyer = db.query(Buyer).filter(Buyer.buyer_id == buyer_id).first()
    if not buyer:
        raise HTTPException(status_code=404, detail="买手不存在")
    db.delete(buyer)
    db.commit()
    return {"code": 0, "message": "success"}


# ============ 需求管理 ============
@router.get("/demands")
def list_demands(
    page: int = 1,
    page_size: int = 20,
    keyword: Optional[str] = None,
    status: Optional[str] = None,
    user_id: Optional[str] = None,
    db: Session = Depends(get_db)
):
    query = db.query(Demand)
    if keyword:
        query = query.filter(Demand.product_name.contains(keyword))
    if status:
        query = query.filter(Demand.status == status)
    if user_id:
        query = query.filter(Demand.user_id == user_id)
    query = query.order_by(desc(Demand.created_at))
    result = paginate_query(query, page, page_size)
    return {"code": 0, "message": "success", "data": result}


class DemandUpdateRequest(BaseModel):
    product_name: Optional[str] = None
    brand_id: Optional[str] = None
    country: Optional[str] = None
    deadline: Optional[str] = None
    budget: Optional[float] = None
    quantity: Optional[int] = None
    status: Optional[str] = None
    matched_buyer_id: Optional[str] = None
    description: Optional[str] = None


@router.put("/demands/{demand_id}")
def update_demand(demand_id: str, request: DemandUpdateRequest, db: Session = Depends(get_db)):
    demand = db.query(Demand).filter(Demand.demand_id == demand_id).first()
    if not demand:
        raise HTTPException(status_code=404, detail="需求不存在")
    for key, value in request.model_dump().items():
        if value is not None:
            setattr(demand, key, value)
    db.commit()
    db.refresh(demand)
    return {"code": 0, "message": "success", "data": demand}


@router.delete("/demands/{demand_id}")
def delete_demand(demand_id: str, db: Session = Depends(get_db)):
    demand = db.query(Demand).filter(Demand.demand_id == demand_id).first()
    if not demand:
        raise HTTPException(status_code=404, detail="需求不存在")
    db.delete(demand)
    db.commit()
    return {"code": 0, "message": "success"}


# ============ 汇率管理 ============
@router.get("/exchange-rates")
def get_exchange_rates(db: Session = Depends(get_db)):
    rates = db.query(ExchangeRate).order_by(desc(ExchangeRate.update_time)).first()
    return {"code": 0, "message": "success", "data": rates}


class ExchangeRateUpdateRequest(BaseModel):
    base: str
    rates: dict


@router.put("/exchange-rates")
def update_exchange_rates(request: ExchangeRateUpdateRequest, db: Session = Depends(get_db)):
    from datetime import datetime
    rates = ExchangeRate(
        base=request.base,
        rates=request.rates,
        update_time=datetime.utcnow()
    )
    db.add(rates)
    db.commit()
    db.refresh(rates)
    return {"code": 0, "message": "success", "data": rates}


# ============ 返点管理 ============
@router.get("/rebates")
def list_rebates(
    page: int = 1,
    page_size: int = 20,
    keyword: Optional[str] = None,
    status: Optional[str] = None,
    country: Optional[str] = None,
    db: Session = Depends(get_db)
):
    query = db.query(Rebate)
    if keyword:
        query = query.filter(Rebate.title.contains(keyword))
    if status:
        query = query.filter(Rebate.status == status)
    if country:
        query = query.filter(Rebate.country == country)
    query = query.order_by(desc(Rebate.created_at))
    result = paginate_query(query, page, page_size)
    return {"code": 0, "message": "success", "data": result}


class RebateCreateRequest(BaseModel):
    rebate_id: str
    title: str
    brand_id: Optional[str] = ""
    brand_name: Optional[str] = ""
    store_id: Optional[str] = ""
    store_name: Optional[str] = ""
    country: str
    rate: float
    is_vip_only: Optional[bool] = False
    status: Optional[str] = "available"
    start_date: Optional[str] = ""
    end_date: Optional[str] = ""
    description: Optional[str] = ""


@router.post("/rebates")
def create_rebate(request: RebateCreateRequest, db: Session = Depends(get_db)):
    existing = db.query(Rebate).filter(Rebate.rebate_id == request.rebate_id).first()
    if existing:
        raise HTTPException(status_code=400, detail="返点活动ID已存在")
    rebate = Rebate(**request.model_dump())
    db.add(rebate)
    db.commit()
    db.refresh(rebate)
    return {"code": 0, "message": "success", "data": rebate}


@router.put("/rebates/{rebate_id}")
def update_rebate(rebate_id: str, request: RebateCreateRequest, db: Session = Depends(get_db)):
    rebate = db.query(Rebate).filter(Rebate.rebate_id == rebate_id).first()
    if not rebate:
        raise HTTPException(status_code=404, detail="返点活动不存在")
    for key, value in request.model_dump().items():
        if value is not None:
            setattr(rebate, key, value)
    db.commit()
    db.refresh(rebate)
    return {"code": 0, "message": "success", "data": rebate}


@router.delete("/rebates/{rebate_id}")
def delete_rebate(rebate_id: str, db: Session = Depends(get_db)):
    rebate = db.query(Rebate).filter(Rebate.rebate_id == rebate_id).first()
    if not rebate:
        raise HTTPException(status_code=404, detail="返点活动不存在")
    db.delete(rebate)
    db.commit()
    return {"code": 0, "message": "success"}
