from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_, delete
from sqlalchemy.sql import func

from database import get_db
from models import Favorite, BrowseHistory, Coupon
from schemas import ApiResponse, FavoriteCreateRequest, FavoriteResponse
from schemas import BrowseHistoryCreateRequest, BrowseHistoryResponse

router = APIRouter(prefix="/api/user", tags=["用户功能"])


# ============== 收藏管理 ==============

@router.get("/favorites", response_model=ApiResponse)
def get_favorites(
    user_id: str = Query(..., description="用户ID"),
    target_type: str = Query(None, description="类型：product/buyer/store"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    query = db.query(Favorite).filter(Favorite.user_id == user_id)
    if target_type:
        query = query.filter(Favorite.target_type == target_type)

    total = query.count()
    offset = (page - 1) * page_size
    favorites = query.order_by(Favorite.created_at.desc()).offset(offset).limit(page_size).all()

    return ApiResponse(
        code=0,
        message="success",
        data={
            "list": [FavoriteResponse.from_orm(f) for f in favorites],
            "total": total,
            "page": page,
            "page_size": page_size
        }
    )


@router.post("/favorites", response_model=ApiResponse)
def add_favorite(request: FavoriteCreateRequest, db: Session = Depends(get_db)):
    existing = db.query(Favorite).filter(
        and_(
            Favorite.user_id == request.user_id,
            Favorite.target_id == request.target_id
        )
    ).first()

    if existing:
        return ApiResponse(code=0, message="已收藏", data=FavoriteResponse.from_orm(existing))

    favorite = Favorite(
        user_id=request.user_id,
        target_type=request.target_type or "product",
        target_id=request.target_id,
        target_name=request.target_name or "",
        target_image=request.target_image or "",
        remark=request.remark or ""
    )
    db.add(favorite)
    db.commit()
    db.refresh(favorite)

    return ApiResponse(code=0, message="收藏成功", data=FavoriteResponse.from_orm(favorite))


@router.delete("/favorites/{target_id}", response_model=ApiResponse)
def remove_favorite(
    target_id: str,
    user_id: str = Query(..., description="用户ID"),
    db: Session = Depends(get_db)
):
    db.query(Favorite).filter(
        and_(Favorite.user_id == user_id, Favorite.target_id == target_id)
    ).delete()
    db.commit()
    return ApiResponse(code=0, message="取消收藏成功")


@router.get("/favorites/check", response_model=ApiResponse)
def check_favorite(
    user_id: str = Query(..., description="用户ID"),
    target_id: str = Query(..., description="目标ID"),
    db: Session = Depends(get_db)
):
    existing = db.query(Favorite).filter(
        and_(Favorite.user_id == user_id, Favorite.target_id == target_id)
    ).first()
    return ApiResponse(code=0, message="success", data={"is_favorited": existing is not None})


# ============== 浏览历史 ==============

@router.get("/history", response_model=ApiResponse)
def get_browse_history(
    user_id: str = Query(..., description="用户ID"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    query = db.query(BrowseHistory).filter(BrowseHistory.user_id == user_id)
    total = query.count()
    offset = (page - 1) * page_size

    favorites = db.query(Bavorite).filter(
        and_(
            Favorite.user_id == user_id,
            BrowseHistory.target_id == Favorite.target_id
        )
    ).all()
    favorited_ids = set(f.target_id for f in favorites)

    history = query.order_by(BrowseHistory.created_at.desc()).offset(offset).limit(page_size).all()
    result = []
    for h in history:
        item = BrowseHistoryResponse.from_orm(h)
        item.is_favorited = h.target_id in favorited_ids
        result.append(item)

    return ApiResponse(
        code=0,
        message="success",
        data={
            "list": result,
            "total": total,
            "page": page,
            "page_size": page_size
        }
    )


@router.post("/history", response_model=ApiResponse)
def add_browse_history(request: BrowseHistoryCreateRequest, db: Session = Depends(get_db)):
    existing = db.query(BrowseHistory).filter(
        and_(
            BrowseHistory.user_id == request.user_id,
            BrowseHistory.target_id == request.target_id
        )
    ).first()

    if existing:
        existing.created_at = func.now()
        db.commit()
        return ApiResponse(code=0, message="success", data=BrowseHistoryResponse.from_orm(existing))

    history = BrowseHistory(
        user_id=request.user_id,
        target_type=request.target_type or "product",
        target_id=request.target_id,
        target_name=request.target_name or "",
        target_image=request.target_image or ""
    )
    db.add(history)
    db.commit()
    db.refresh(history)

    return ApiResponse(code=0, message="success", data=BrowseHistoryResponse.from_orm(history))


@router.delete("/history", response_model=ApiResponse)
def clear_browse_history(
    user_id: str = Query(..., description="用户ID"),
    db: Session = Depends(get_db)
):
    db.query(BrowseHistory).filter(BrowseHistory.user_id == user_id).delete()
    db.commit()
    return ApiResponse(code=0, message="清除成功")


@router.delete("/history/{target_id}", response_model=ApiResponse)
def remove_history_item(
    target_id: str,
    user_id: str = Query(..., description="用户ID"),
    db: Session = Depends(get_db)
):
    db.query(BrowseHistory).filter(
        and_(BrowseHistory.user_id == user_id, BrowseHistory.target_id == target_id)
    ).delete()
    db.commit()
    return ApiResponse(code=0, message="删除成功")


# ============== 我的优惠券 ==============

@router.get("/my-coupons", response_model=ApiResponse)
def get_my_coupons(
    user_id: str = Query(..., description="用户ID"),
    status: str = Query(None, description="状态：available/used/expired"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    from models import UserCoupon
    query = db.query(UserCoupon).filter(UserCoupon.user_id == user_id)
    if status:
        query = query.filter(UserCoupon.status == status)

    total = query.count()
    offset = (page - 1) * page_size
    user_coupons = query.order_by(UserCoupon.created_at.desc()).offset(offset).limit(page_size).all()

    result = []
    for uc in user_coupons:
        coupon = db.query(Coupon).filter(Coupon.coupon_id == uc.coupon_id).first()
        if coupon:
            result.append({
                "id": uc.id,
                "user_coupon_id": uc.user_coupon_id,
                "coupon_id": coupon.coupon_id,
                "title": coupon.title,
                "type": coupon.type,
                "discount": coupon.discount,
                "min_amount": coupon.min_amount,
                "country": coupon.country,
                "store_name": coupon.store_name,
                "status": uc.status,
                "obtained_at": uc.created_at,
                "used_at": uc.used_at
            })

    return ApiResponse(
        code=0,
        message="success",
        data={
            "list": result,
            "total": total,
            "page": page,
            "page_size": page_size
        }
    )


@router.post("/my-coupons/claim", response_model=ApiResponse)
def claim_coupon(
    user_id: str = Query(..., description="用户ID"),
    coupon_id: str = Query(..., description="优惠券ID"),
    db: Session = Depends(get_db)
):
    from models import UserCoupon
    from datetime import datetime

    existing = db.query(UserCoupon).filter(
        and_(UserCoupon.user_id == user_id, UserCoupon.coupon_id == coupon_id)
    ).first()

    if existing:
        return ApiResponse(code=1, message="您已领取过该优惠券")

    coupon = db.query(Coupon).filter(Coupon.coupon_id == coupon_id).first()
    if not coupon:
        return ApiResponse(code=1, message="优惠券不存在")

    import uuid
    user_coupon = UserCoupon(
        user_coupon_id="UC" + str(int(datetime.now().timestamp() * 1000)),
        user_id=user_id,
        coupon_id=coupon_id,
        status="available"
    )
    db.add(user_coupon)
    db.commit()
    db.refresh(user_coupon)

    return ApiResponse(code=0, message="领取成功", data={
        "user_coupon_id": user_coupon.user_coupon_id
    })


@router.put("/my-coupons/{user_coupon_id}/use", response_model=ApiResponse)
def use_coupon(
    user_coupon_id: str,
    db: Session = Depends(get_db)
):
    from models import UserCoupon
    from datetime import datetime

    user_coupon = db.query(UserCoupon).filter(UserCoupon.user_coupon_id == user_coupon_id).first()
    if not user_coupon:
        return ApiResponse(code=1, message="优惠券不存在")

    if user_coupon.status != "available":
        return ApiResponse(code=1, message="优惠券不可用")

    user_coupon.status = "used"
    user_coupon.used_at = datetime.utcnow()
    db.commit()

    return ApiResponse(code=0, message="使用成功")
