from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func

from database import get_db
from models import Brand, Category, SPU, SKU, SKUPrice
from utils.trino_db import TrinoClient, TrinoUnavailableError
from schemas import (
    ApiResponse,
    BrandCreateRequest,
    BrandUpdateRequest,
    BrandResponse,
    CategoryCreateRequest,
    CategoryUpdateRequest,
    CategoryResponse,
    SPUCreateRequest,
    SPUUpdateRequest,
    SPUResponse,
    SKUCreateRequest,
    SKUUpdateRequest,
    SKUResponse,
    SKUPriceCreateRequest,
    SKUPriceUpdateRequest,
    SKUPriceResponse,
)

router = APIRouter(prefix="/api/product", tags=["商品管理"])
trino_client = TrinoClient()


@router.get("/brands", response_model=ApiResponse)
def get_brands(
    keyword: str = Query(None, description="搜索关键词"),
    category: str = Query(None, description="品牌分类"),
    db: Session = Depends(get_db)
):
    if trino_client.is_enabled():
        try:
            brands = trino_client.get_brands(keyword=keyword, category=category)
            return ApiResponse(code=0, message="success", data=brands)
        except TrinoUnavailableError:
            pass

    query = db.query(Brand)
    
    if keyword:
        query = query.filter(
            Brand.name.ilike(f"%{keyword}%") | 
            Brand.name_cn.ilike(f"%{keyword}%")
        )
    
    if category:
        query = query.filter(Brand.category == category)
    
    brands = query.order_by(Brand.name_cn).all()
    
    return ApiResponse(
        code=0,
        message="success",
        data=[BrandResponse.from_orm(b) for b in brands]
    )


@router.get("/brands/{brand_id}", response_model=ApiResponse)
def get_brand(brand_id: str, db: Session = Depends(get_db)):
    brand = db.query(Brand).filter(Brand.brand_id == brand_id).first()
    
    if not brand:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="品牌不存在"
        )
    
    return ApiResponse(
        code=0,
        message="success",
        data=BrandResponse.from_orm(brand)
    )


@router.post("/brands", response_model=ApiResponse)
def create_brand(request: BrandCreateRequest, db: Session = Depends(get_db)):
    existing = db.query(Brand).filter(Brand.brand_id == request.brand_id).first()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="品牌ID已存在"
        )
    
    brand = Brand(
        brand_id=request.brand_id,
        name=request.name,
        name_cn=request.name_cn,
        logo=request.logo,
        category=request.category
    )
    
    db.add(brand)
    db.commit()
    db.refresh(brand)
    
    return ApiResponse(
        code=0,
        message="创建成功",
        data=BrandResponse.from_orm(brand)
    )


@router.put("/brands/{brand_id}", response_model=ApiResponse)
def update_brand(brand_id: str, request: BrandUpdateRequest, db: Session = Depends(get_db)):
    brand = db.query(Brand).filter(Brand.brand_id == brand_id).first()
    
    if not brand:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="品牌不存在"
        )
    
    if request.name is not None:
        brand.name = request.name
    if request.name_cn is not None:
        brand.name_cn = request.name_cn
    if request.logo is not None:
        brand.logo = request.logo
    if request.category is not None:
        brand.category = request.category
    
    db.commit()
    db.refresh(brand)
    
    return ApiResponse(
        code=0,
        message="更新成功",
        data=BrandResponse.from_orm(brand)
    )


@router.delete("/brands/{brand_id}", response_model=ApiResponse)
def delete_brand(brand_id: str, db: Session = Depends(get_db)):
    brand = db.query(Brand).filter(Brand.brand_id == brand_id).first()
    
    if not brand:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="品牌不存在"
        )
    
    db.delete(brand)
    db.commit()
    
    return ApiResponse(
        code=0,
        message="删除成功"
    )


@router.get("/categories", response_model=ApiResponse)
def get_categories(db: Session = Depends(get_db)):
    if trino_client.is_enabled():
        try:
            categories = trino_client.get_categories()
            return ApiResponse(code=0, message="success", data=categories)
        except TrinoUnavailableError:
            pass

    categories = db.query(Category).order_by(Category.name).all()
    
    return ApiResponse(
        code=0,
        message="success",
        data=[CategoryResponse.from_orm(c) for c in categories]
    )


@router.get("/categories/{category_id}", response_model=ApiResponse)
def get_category(category_id: str, db: Session = Depends(get_db)):
    category = db.query(Category).filter(Category.category_id == category_id).first()
    
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="品类不存在"
        )
    
    return ApiResponse(
        code=0,
        message="success",
        data=CategoryResponse.from_orm(category)
    )


@router.post("/categories", response_model=ApiResponse)
def create_category(request: CategoryCreateRequest, db: Session = Depends(get_db)):
    existing = db.query(Category).filter(Category.category_id == request.category_id).first()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="品类ID已存在"
        )
    
    category = Category(
        category_id=request.category_id,
        name=request.name,
        icon=request.icon
    )
    
    db.add(category)
    db.commit()
    db.refresh(category)
    
    return ApiResponse(
        code=0,
        message="创建成功",
        data=CategoryResponse.from_orm(category)
    )


@router.put("/categories/{category_id}", response_model=ApiResponse)
def update_category(category_id: str, request: CategoryUpdateRequest, db: Session = Depends(get_db)):
    category = db.query(Category).filter(Category.category_id == category_id).first()
    
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="品类不存在"
        )
    
    if request.name is not None:
        category.name = request.name
    if request.icon is not None:
        category.icon = request.icon
    
    db.commit()
    db.refresh(category)
    
    return ApiResponse(
        code=0,
        message="更新成功",
        data=CategoryResponse.from_orm(category)
    )


@router.delete("/categories/{category_id}", response_model=ApiResponse)
def delete_category(category_id: str, db: Session = Depends(get_db)):
    category = db.query(Category).filter(Category.category_id == category_id).first()
    
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="品类不存在"
        )
    
    db.delete(category)
    db.commit()
    
    return ApiResponse(
        code=0,
        message="删除成功"
    )


@router.get("/spus", response_model=ApiResponse)
def get_spus(
    keyword: str = Query(None, description="搜索关键词"),
    brand_id: str = Query(None, description="品牌ID"),
    category_id: str = Query(None, description="品类ID"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    query = db.query(SPU)
    
    if keyword:
        query = query.filter(
            SPU.name.ilike(f"%{keyword}%") | 
            SPU.name_en.ilike(f"%{keyword}%") |
            SPU.article_no.ilike(f"%{keyword}%")
        )
    
    if brand_id:
        query = query.filter(SPU.brand_id == brand_id)
    
    if category_id:
        query = query.filter(SPU.category_id == category_id)
    
    total = query.count()
    offset = (page - 1) * page_size
    spus = query.offset(offset).limit(page_size).order_by(SPU.created_at.desc()).all()
    
    return ApiResponse(
        code=0,
        message="success",
        data={
            "list": [SPUResponse.from_orm(s) for s in spus],
            "total": total,
            "page": page,
            "page_size": page_size
        }
    )


@router.get("/spus/{spu_id}", response_model=ApiResponse)
def get_spu(spu_id: str, db: Session = Depends(get_db)):
    spu = db.query(SPU).filter(SPU.spu_id == spu_id).first()
    
    if not spu:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="SPU不存在"
        )
    
    return ApiResponse(
        code=0,
        message="success",
        data=SPUResponse.from_orm(spu)
    )


@router.post("/spus", response_model=ApiResponse)
def create_spu(request: SPUCreateRequest, db: Session = Depends(get_db)):
    existing = db.query(SPU).filter(SPU.spu_id == request.spu_id).first()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="SPU ID已存在"
        )
    
    spu = SPU(
        spu_id=request.spu_id,
        brand_id=request.brand_id,
        brand_name=request.brand_name,
        name=request.name,
        name_en=request.name_en,
        article_no=request.article_no,
        category_id=request.category_id,
        image=request.image,
        description=request.description
    )
    
    db.add(spu)
    db.commit()
    db.refresh(spu)
    
    return ApiResponse(
        code=0,
        message="创建成功",
        data=SPUResponse.from_orm(spu)
    )


@router.put("/spus/{spu_id}", response_model=ApiResponse)
def update_spu(spu_id: str, request: SPUUpdateRequest, db: Session = Depends(get_db)):
    spu = db.query(SPU).filter(SPU.spu_id == spu_id).first()
    
    if not spu:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="SPU不存在"
        )
    
    if request.name is not None:
        spu.name = request.name
    if request.name_en is not None:
        spu.name_en = request.name_en
    if request.article_no is not None:
        spu.article_no = request.article_no
    if request.category_id is not None:
        spu.category_id = request.category_id
    if request.image is not None:
        spu.image = request.image
    if request.description is not None:
        spu.description = request.description
    
    db.commit()
    db.refresh(spu)
    
    return ApiResponse(
        code=0,
        message="更新成功",
        data=SPUResponse.from_orm(spu)
    )


@router.delete("/spus/{spu_id}", response_model=ApiResponse)
def delete_spu(spu_id: str, db: Session = Depends(get_db)):
    spu = db.query(SPU).filter(SPU.spu_id == spu_id).first()
    
    if not spu:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="SPU不存在"
        )
    
    db.delete(spu)
    db.commit()
    
    return ApiResponse(
        code=0,
        message="删除成功"
    )


@router.get("/skus", response_model=ApiResponse)
def get_skus(
    spu_id: str = Query(None, description="SPU ID"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    query = db.query(SKU)
    
    if spu_id:
        query = query.filter(SKU.spu_id == spu_id)
    
    total = query.count()
    offset = (page - 1) * page_size
    skus = query.offset(offset).limit(page_size).order_by(SKU.created_at.desc()).all()
    
    return ApiResponse(
        code=0,
        message="success",
        data={
            "list": [SKUResponse.from_orm(s) for s in skus],
            "total": total,
            "page": page,
            "page_size": page_size
        }
    )


@router.get("/skus/{sku_id}", response_model=ApiResponse)
def get_sku(sku_id: str, db: Session = Depends(get_db)):
    sku = db.query(SKU).filter(SKU.sku_id == sku_id).first()
    
    if not sku:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="SKU不存在"
        )
    
    return ApiResponse(
        code=0,
        message="success",
        data=SKUResponse.from_orm(sku)
    )


@router.post("/skus", response_model=ApiResponse)
def create_sku(request: SKUCreateRequest, db: Session = Depends(get_db)):
    existing = db.query(SKU).filter(SKU.sku_id == request.sku_id).first()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="SKU ID已存在"
        )
    
    sku = SKU(
        sku_id=request.sku_id,
        spu_id=request.spu_id,
        name=request.name,
        color=request.color,
        size=request.size
    )
    
    db.add(sku)
    db.commit()
    db.refresh(sku)
    
    return ApiResponse(
        code=0,
        message="创建成功",
        data=SKUResponse.from_orm(sku)
    )


@router.put("/skus/{sku_id}", response_model=ApiResponse)
def update_sku(sku_id: str, request: SKUUpdateRequest, db: Session = Depends(get_db)):
    sku = db.query(SKU).filter(SKU.sku_id == sku_id).first()
    
    if not sku:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="SKU不存在"
        )
    
    if request.name is not None:
        sku.name = request.name
    if request.color is not None:
        sku.color = request.color
    if request.size is not None:
        sku.size = request.size
    
    db.commit()
    db.refresh(sku)
    
    return ApiResponse(
        code=0,
        message="更新成功",
        data=SKUResponse.from_orm(sku)
    )


@router.delete("/skus/{sku_id}", response_model=ApiResponse)
def delete_sku(sku_id: str, db: Session = Depends(get_db)):
    sku = db.query(SKU).filter(SKU.sku_id == sku_id).first()
    
    if not sku:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="SKU不存在"
        )
    
    db.delete(sku)
    db.commit()
    
    return ApiResponse(
        code=0,
        message="删除成功"
    )


@router.get("/sku-prices", response_model=ApiResponse)
def get_sku_prices(
    sku_id: str = Query(None, description="SKU ID"),
    country: str = Query(None, description="国家代码"),
    db: Session = Depends(get_db)
):
    query = db.query(SKUPrice)
    
    if sku_id:
        query = query.filter(SKUPrice.sku_id == sku_id)
    
    if country:
        query = query.filter(SKUPrice.country == country)
    
    prices = query.order_by(SKUPrice.country).all()
    
    return ApiResponse(
        code=0,
        message="success",
        data=[SKUPriceResponse.from_orm(p) for p in prices]
    )


@router.get("/sku-prices/{price_id}", response_model=ApiResponse)
def get_sku_price(price_id: int, db: Session = Depends(get_db)):
    price = db.query(SKUPrice).filter(SKUPrice.id == price_id).first()
    
    if not price:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="价格记录不存在"
        )
    
    return ApiResponse(
        code=0,
        message="success",
        data=SKUPriceResponse.from_orm(price)
    )


@router.post("/sku-prices", response_model=ApiResponse)
def create_sku_price(request: SKUPriceCreateRequest, db: Session = Depends(get_db)):
    existing = db.query(SKUPrice).filter(
        SKUPrice.sku_id == request.sku_id,
        SKUPrice.country == request.country
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="该SKU在该国家的价格记录已存在"
        )
    
    price = SKUPrice(
        sku_id=request.sku_id,
        country=request.country,
        currency=request.currency,
        price=request.price,
        stock=request.stock,
        store=request.store
    )
    
    db.add(price)
    db.commit()
    db.refresh(price)
    
    return ApiResponse(
        code=0,
        message="创建成功",
        data=SKUPriceResponse.from_orm(price)
    )


@router.put("/sku-prices/{price_id}", response_model=ApiResponse)
def update_sku_price(price_id: int, request: SKUPriceUpdateRequest, db: Session = Depends(get_db)):
    price = db.query(SKUPrice).filter(SKUPrice.id == price_id).first()
    
    if not price:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="价格记录不存在"
        )
    
    if request.price is not None:
        price.price = request.price
    if request.stock is not None:
        price.stock = request.stock
    if request.store is not None:
        price.store = request.store
    
    db.commit()
    db.refresh(price)
    
    return ApiResponse(
        code=0,
        message="更新成功",
        data=SKUPriceResponse.from_orm(price)
    )


@router.delete("/sku-prices/{price_id}", response_model=ApiResponse)
def delete_sku_price(price_id: int, db: Session = Depends(get_db)):
    price = db.query(SKUPrice).filter(SKUPrice.id == price_id).first()
    
    if not price:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="价格记录不存在"
        )
    
    db.delete(price)
    db.commit()
    
    return ApiResponse(
        code=0,
        message="删除成功"
    )


@router.get("/search", response_model=ApiResponse)
def search_products(
    keyword: str = Query(None, description="搜索关键词"),
    brand_id: str = Query(None, description="品牌ID"),
    category_id: str = Query(None, description="品类ID"),
    country: str = Query(None, description="国家代码"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    if trino_client.is_enabled():
        try:
            data = trino_client.search_products(
                keyword=keyword,
                brand_id=brand_id,
                category_id=category_id,
                country=country,
                page=page,
                page_size=page_size,
            )
            return ApiResponse(code=0, message="success", data=data)
        except TrinoUnavailableError:
            pass

    spu_query = db.query(SPU)
    
    if keyword:
        spu_query = spu_query.filter(
            SPU.name.ilike(f"%{keyword}%") | 
            SPU.name_en.ilike(f"%{keyword}%") |
            SPU.article_no.ilike(f"%{keyword}%")
        )
    
    if brand_id:
        spu_query = spu_query.filter(SPU.brand_id == brand_id)
    
    if category_id:
        spu_query = spu_query.filter(SPU.category_id == category_id)
    
    total = spu_query.count()
    offset = (page - 1) * page_size
    spus = spu_query.order_by(SPU.created_at.desc()).offset(offset).limit(page_size).all()
    
    spu_ids = [s.spu_id for s in spus]
    
    price_query = db.query(
        SKU.spu_id,
        SKUPrice.country,
        func.min(SKUPrice.price).label("min_price"),
        func.max(SKUPrice.price).label("max_price")
    ).outerjoin(SKUPrice, SKU.sku_id == SKUPrice.sku_id)
    
    if spu_ids:
        price_query = price_query.filter(SKU.spu_id.in_(spu_ids))
    
    if country:
        price_query = price_query.filter(SKUPrice.country == country)
    
    price_query = price_query.group_by(SKU.spu_id, SKUPrice.country)
    price_results = price_query.all()
    
    price_map = {}
    for r in price_results:
        if r.spu_id not in price_map:
            price_map[r.spu_id] = {
                "min_price": float('inf'),
                "max_price": 0,
                "countries": []
            }
        price_map[r.spu_id]["min_price"] = min(price_map[r.spu_id]["min_price"], r.min_price or float('inf'))
        price_map[r.spu_id]["max_price"] = max(price_map[r.spu_id]["max_price"], r.max_price or 0)
        if r.country and r.country not in price_map[r.spu_id]["countries"]:
            price_map[r.spu_id]["countries"].append(r.country)
    
    products = []
    for spu in spus:
        price_info = price_map.get(spu.spu_id, {"min_price": 0, "max_price": 0, "countries": []})
        products.append({
            "spu_id": spu.spu_id,
            "brand_id": spu.brand_id,
            "brand_name": spu.brand_name,
            "name": spu.name,
            "name_en": spu.name_en,
            "article_no": spu.article_no,
            "category_id": spu.category_id,
            "image": spu.image,
            "min_price": price_info["min_price"] if price_info["min_price"] != float('inf') else 0,
            "max_price": price_info["max_price"],
            "countries": price_info["countries"]
        })
    
    return ApiResponse(
        code=0,
        message="success",
        data={
            "list": products,
            "total": total,
            "page": page,
            "page_size": page_size
        }
    )


@router.get("/product-detail/{spu_id}", response_model=ApiResponse)
def get_product_detail(spu_id: str, db: Session = Depends(get_db)):
    if trino_client.is_enabled():
        try:
            detail = trino_client.get_product_detail(spu_id)
            if not detail:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="商品不存在"
                )
            return ApiResponse(code=0, message="success", data=detail)
        except TrinoUnavailableError:
            pass

    spu = db.query(SPU).filter(SPU.spu_id == spu_id).first()
    
    if not spu:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="商品不存在"
        )
    
    skus = db.query(SKU).filter(SKU.spu_id == spu_id).all()
    
    sku_ids = [s.sku_id for s in skus]
    prices = []
    
    if sku_ids:
        prices = db.query(SKUPrice).filter(SKUPrice.sku_id.in_(sku_ids)).all()
    
    sku_list = []
    for sku in skus:
        sku_prices = [p for p in prices if p.sku_id == sku.sku_id]
        sku_item = {
            "sku_id": sku.sku_id,
            "name": sku.name,
            "color": sku.color,
            "size": sku.size,
            "prices": [SKUPriceResponse.from_orm(p) for p in sku_prices]
        }
        sku_list.append(sku_item)
    
    brand = db.query(Brand).filter(Brand.brand_id == spu.brand_id).first()
    category = db.query(Category).filter(Category.category_id == spu.category_id).first()
    
    return ApiResponse(
        code=0,
        message="success",
        data={
            "spu": SPUResponse.from_orm(spu),
            "brand": BrandResponse.from_orm(brand) if brand else None,
            "category": CategoryResponse.from_orm(category) if category else None,
            "skus": sku_list
        }
    )