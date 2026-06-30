from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class BrandCreateRequest(BaseModel):
    brand_id: str = Field(..., description="品牌ID")
    name: str = Field(..., description="品牌英文名称")
    name_cn: str = Field(..., description="品牌中文名称")
    logo: Optional[str] = Field("", description="品牌Logo")
    category: Optional[str] = Field("", description="品牌分类")


class BrandUpdateRequest(BaseModel):
    name: Optional[str] = None
    name_cn: Optional[str] = None
    logo: Optional[str] = None
    category: Optional[str] = None


class BrandResponse(BaseModel):
    id: int
    brand_id: str
    name: str
    name_cn: str
    logo: str
    category: str
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class CategoryCreateRequest(BaseModel):
    category_id: str = Field(..., description="品类ID")
    name: str = Field(..., description="品类名称")
    icon: Optional[str] = Field("", description="品类图标")


class CategoryUpdateRequest(BaseModel):
    name: Optional[str] = None
    icon: Optional[str] = None


class CategoryResponse(BaseModel):
    id: int
    category_id: str
    name: str
    icon: str
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class SPUCreateRequest(BaseModel):
    spu_id: str = Field(..., description="SPU ID")
    brand_id: str = Field(..., description="品牌ID")
    brand_name: str = Field(..., description="品牌名称")
    name: str = Field(..., description="商品名称")
    name_en: Optional[str] = Field("", description="英文名称")
    article_no: str = Field(..., description="商品货号")
    category_id: str = Field(..., description="品类ID")
    image: Optional[str] = Field("", description="商品图片")
    description: Optional[str] = Field("", description="商品描述")


class SPUUpdateRequest(BaseModel):
    name: Optional[str] = None
    name_en: Optional[str] = None
    article_no: Optional[str] = None
    category_id: Optional[str] = None
    image: Optional[str] = None
    description: Optional[str] = None


class SPUResponse(BaseModel):
    id: int
    spu_id: str
    brand_id: str
    brand_name: str
    name: str
    name_en: str
    article_no: str
    category_id: str
    image: str
    description: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class SKUCreateRequest(BaseModel):
    sku_id: str = Field(..., description="SKU ID")
    spu_id: str = Field(..., description="SPU ID")
    name: str = Field(..., description="SKU名称")
    color: Optional[str] = Field("", description="颜色")
    size: Optional[str] = Field("", description="尺码")


class SKUUpdateRequest(BaseModel):
    name: Optional[str] = None
    color: Optional[str] = None
    size: Optional[str] = None


class SKUResponse(BaseModel):
    id: int
    sku_id: str
    spu_id: str
    name: str
    color: str
    size: str
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class SKUPriceCreateRequest(BaseModel):
    sku_id: str = Field(..., description="SKU ID")
    country: str = Field(..., description="国家代码")
    currency: str = Field(..., description="货币代码")
    price: float = Field(..., description="价格")
    stock: Optional[int] = Field(0, description="库存")
    store: Optional[str] = Field("", description="店铺名称")


class SKUPriceUpdateRequest(BaseModel):
    price: Optional[float] = None
    stock: Optional[int] = None
    store: Optional[str] = None


class SKUPriceResponse(BaseModel):
    id: int
    sku_id: str
    country: str
    currency: str
    price: float
    stock: int
    store: str
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ProductSearchRequest(BaseModel):
    keyword: Optional[str] = None
    brand_id: Optional[str] = None
    category_id: Optional[str] = None
    country: Optional[str] = None
    page: int = 1
    page_size: int = 20


class ProductSearchResponse(BaseModel):
    spu_id: str
    brand_id: str
    brand_name: str
    name: str
    name_en: str
    article_no: str
    category_id: str
    image: str
    min_price: float = 0
    max_price: float = 0
    countries: List[str] = []

    class Config:
        from_attributes = True