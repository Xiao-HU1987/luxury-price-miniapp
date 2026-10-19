"""翻译校对 API

提供管理后台用于校对自动翻译结果的接口：
- 查询待校对列表（商品 + 门店）
- 修改翻译内容
- 确认校对通过（单个/批量）
- 重新触发翻译

状态流转：pending → translated → approved
"""
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
from models import SPU, SKU
from models.lv import LvInventory
from schemas import ApiResponse

router = APIRouter(prefix="/api/translate", tags=["翻译校对"])


# ==================== 请求模型 ====================

class ApproveProductRequest(BaseModel):
    spu_id: str
    name_cn: Optional[str] = None
    description_cn: Optional[str] = None
    color_cn: Optional[str] = None  # 对应 SKU 的颜色翻译


class ApproveStoreRequest(BaseModel):
    inventory_id: int
    store_name_cn: Optional[str] = None
    store_address_cn: Optional[str] = None
    store_city_cn: Optional[str] = None


class BatchApproveRequest(BaseModel):
    spu_ids: list[str] = []
    inventory_ids: list[int] = []


class RetryTranslateRequest(BaseModel):
    spu_ids: list[str] = []


# ==================== 商品翻译校对 ====================

@router.get("/products/pending", response_model=ApiResponse)
def get_pending_products(
    status_filter: str = Query("translated", description="翻译状态: pending/translatod/approved/all"),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """查询待校对的商品翻译列表。"""
    query = db.query(SPU)
    if status_filter != "all":
        query = query.filter(SPU.translate_status == status_filter)
    total = query.count()
    items = query.order_by(SPU.updated_at.desc()).offset((page - 1) * size).limit(size).all()

    data = []
    for spu in items:
        # 关联 SKU 的颜色翻译
        sku = db.query(SKU).filter(SKU.spu_id == spu.spu_id).first()
        data.append({
            "spu_id": spu.spu_id,
            "article_no": spu.article_no,
            "name": spu.name,
            "name_cn": spu.name_cn,
            "description": (spu.description or "")[:200],
            "description_cn": (spu.description_cn or "")[:200],
            "color": sku.color if sku else "",
            "color_cn": sku.color_cn if sku else "",
            "translate_status": spu.translate_status,
            "image": spu.image,
        })

    return ApiResponse(code=0, message="success", data={
        "total": total, "page": page, "size": size, "items": data,
    })


@router.post("/products/approve", response_model=ApiResponse)
def approve_product_translation(req: ApproveProductRequest, db: Session = Depends(get_db)):
    """确认（或修改后确认）商品翻译。

    - 如果传了 name_cn / description_cn，会先更新翻译内容
    - 然后将状态改为 approved
    """
    spu = db.query(SPU).filter(SPU.spu_id == req.spu_id).first()
    if not spu:
        raise HTTPException(status_code=404, detail="商品不存在")

    # 更新翻译内容（如果提供了修改）
    if req.name_cn is not None:
        spu.name_cn = req.name_cn
    if req.description_cn is not None:
        spu.description_cn = req.description_cn

    # 更新 SKU 颜色翻译
    if req.color_cn is not None:
        sku = db.query(SKU).filter(SKU.spu_id == spu.spu_id).first()
        if sku:
            sku.color_cn = req.color_cn

    spu.translate_status = "approved"
    spu.approved_at = datetime.now(timezone.utc)
    db.commit()

    return ApiResponse(code=0, message="校对确认成功", data={
        "spu_id": spu.spu_id,
        "name_cn": spu.name_cn,
        "translate_status": spu.translate_status,
    })


# ==================== 门店翻译校对 ====================

@router.get("/stores/pending", response_model=ApiResponse)
def get_pending_stores(
    status_filter: str = Query("translated", description="翻译状态"),
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    """查询待校对的门店翻译列表。"""
    query = db.query(LvInventory)
    if status_filter != "all":
        query = query.filter(LvInventory.translate_status == status_filter)

    # 去重：同一 store_id 只取一条（不同 SKU 的同一门店翻译是一样的）
    query = query.distinct(LvInventory.store_id)
    total = query.count()
    items = query.order_by(LvInventory.updated_at.desc()).offset((page - 1) * size).limit(size).all()

    data = []
    for inv in items:
        data.append({
            "inventory_id": inv.id,
            "store_id": inv.store_id,
            "store_name": inv.store_name,
            "store_name_cn": inv.store_name_cn,
            "store_address": inv.store_address,
            "store_address_cn": inv.store_address_cn,
            "store_city": inv.store_city,
            "store_city_cn": inv.store_city_cn,
            "translate_status": inv.translate_status,
        })

    return ApiResponse(code=0, message="success", data={
        "total": total, "page": page, "size": size, "items": data,
    })


@router.post("/stores/approve", response_model=ApiResponse)
def approve_store_translation(req: ApproveStoreRequest, db: Session = Depends(get_db)):
    """确认（或修改后确认）门店翻译。

    会同时更新同一 store_id 的所有库存记录的翻译。
    """
    inv = db.query(LvInventory).filter(LvInventory.id == req.inventory_id).first()
    if not inv:
        raise HTTPException(status_code=404, detail="库存记录不存在")

    # 更新翻译内容
    if req.store_name_cn is not None:
        inv.store_name_cn = req.store_name_cn
    if req.store_address_cn is not None:
        inv.store_address_cn = req.store_address_cn
    if req.store_city_cn is not None:
        inv.store_city_cn = req.store_city_cn

    # 批量更新同一 store_id 的所有记录
    now = datetime.now(timezone.utc)
    db.query(LvInventory).filter(LvInventory.store_id == inv.store_id).update({
        LvInventory.store_name_cn: inv.store_name_cn,
        LvInventory.store_address_cn: inv.store_address_cn,
        LvInventory.store_city_cn: inv.store_city_cn,
        LvInventory.translate_status: "approved",
        LvInventory.approved_at: now,
    }, synchronize_session=False)

    db.commit()

    return ApiResponse(code=0, message="门店翻译校对成功", data={
        "store_id": inv.store_id,
        "store_name_cn": inv.store_name_cn,
    })


# ==================== 批量操作 ====================

@router.post("/batch-approve", response_model=ApiResponse)
def batch_approve(req: BatchApproveRequest, db: Session = Depends(get_db)):
    """批量确认翻译。"""
    now = datetime.now(timezone.utc)
    spu_count = 0
    store_count = 0

    if req.spu_ids:
        result = db.query(SPU).filter(SPU.spu_id.in_(req.spu_ids)).update({
            SPU.translate_status: "approved",
            SPU.approved_at: now,
        }, synchronize_session=False)
        spu_count = result

    if req.inventory_ids:
        # 先查出 store_ids，再批量更新
        invs = db.query(LvInventory).filter(LvInventory.id.in_(req.inventory_ids)).all()
        store_ids = list(set(inv.store_id for inv in invs if inv.store_id))
        if store_ids:
            result = db.query(LvInventory).filter(
                LvInventory.store_id.in_(store_ids)
            ).update({
                LvInventory.translate_status: "approved",
                LvInventory.approved_at: now,
            }, synchronize_session=False)
            store_count = result

    db.commit()

    return ApiResponse(code=0, message=f"批量确认完成: {spu_count} 商品, {store_count} 门店", data={
        "spu_count": spu_count,
        "store_count": store_count,
    })


# ==================== 统计 ====================

@router.get("/stats", response_model=ApiResponse)
def get_translate_stats(db: Session = Depends(get_db)):
    """翻译校对统计。"""
    # 商品统计
    spu_total = db.query(SPU).count()
    spu_pending = db.query(SPU).filter(SPU.translate_status == "pending").count()
    spu_translated = db.query(SPU).filter(SPU.translate_status == "translated").count()
    spu_approved = db.query(SPU).filter(SPU.translate_status == "approved").count()

    # 门店统计（按 store_id 去重）
    store_total = db.query(LvInventory.store_id).distinct().count()
    store_pending = db.query(LvInventory.store_id).filter(
        LvInventory.translate_status == "pending"
    ).distinct().count()
    store_translated = db.query(LvInventory.store_id).filter(
        LvInventory.translate_status == "translated"
    ).distinct().count()
    store_approved = db.query(LvInventory.store_id).filter(
        LvInventory.translate_status == "approved"
    ).distinct().count()

    return ApiResponse(code=0, message="success", data={
        "products": {
            "total": spu_total,
            "pending": spu_pending,
            "translated": spu_translated,
            "approved": spu_approved,
        },
        "stores": {
            "total": store_total,
            "pending": store_pending,
            "translated": store_translated,
            "approved": store_approved,
        },
    })
