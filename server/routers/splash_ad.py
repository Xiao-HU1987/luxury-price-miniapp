from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_, func

from database import get_db
from models import SplashAd, SplashAdLog
from schemas import ApiResponse, SplashAdCreateRequest, SplashAdUpdateRequest, SplashAdResponse
from utils.security import get_current_admin

router = APIRouter(tags=["开屏广告"])


# ========== 小程序端接口 ==========

@router.get("/api/splash-ad/current", response_model=ApiResponse)
def get_current_splash_ad(
    user_id: str = Query("", description="用户ID"),
    db: Session = Depends(get_db)
):
    now = func.now()
    
    query = db.query(SplashAd).filter(SplashAd.is_active == True)
    query = query.filter(
        and_(
            SplashAd.start_time.is_(None) | (SplashAd.start_time <= now),
            SplashAd.end_time.is_(None) | (SplashAd.end_time >= now)
        )
    )
    
    ads = query.order_by(SplashAd.sort_order.desc(), SplashAd.id.desc()).all()
    
    if not ads:
        return ApiResponse(code=0, message="success", data=None)
    
    ad = ads[0]
    
    if user_id and ad.daily_limit > 0:
        from datetime import date
        today = date.today()
        today_start = f"{today} 00:00:00"
        today_end = f"{today} 23:59:59"
        
        today_count = db.query(SplashAdLog).filter(
            and_(
                SplashAdLog.ad_id == ad.id,
                SplashAdLog.user_id == user_id,
                SplashAdLog.action_type == "show",
                SplashAdLog.created_at >= today_start,
                SplashAdLog.created_at <= today_end
            )
        ).count()
        
        if today_count >= ad.daily_limit:
            return ApiResponse(code=0, message="今日已达展示上限", data=None)
    
    return ApiResponse(code=0, message="success", data=SplashAdResponse.from_orm(ad))


@router.post("/api/splash-ad/{ad_id}/show", response_model=ApiResponse)
def record_splash_ad_show(
    ad_id: int,
    user_id: str = Query("", description="用户ID"),
    db: Session = Depends(get_db)
):
    ad = db.query(SplashAd).filter(SplashAd.id == ad_id).first()
    if ad:
        ad.show_count += 1
        log = SplashAdLog(
            ad_id=ad_id,
            user_id=user_id,
            action_type="show"
        )
        db.add(log)
        db.commit()
    
    return ApiResponse(code=0, message="success")


@router.post("/api/splash-ad/{ad_id}/click", response_model=ApiResponse)
def record_splash_ad_click(
    ad_id: int,
    user_id: str = Query("", description="用户ID"),
    db: Session = Depends(get_db)
):
    ad = db.query(SplashAd).filter(SplashAd.id == ad_id).first()
    if ad:
        ad.click_count += 1
        log = SplashAdLog(
            ad_id=ad_id,
            user_id=user_id,
            action_type="click"
        )
        db.add(log)
        db.commit()
    
    return ApiResponse(code=0, message="success")


# ========== 后台管理接口 ==========

@router.get("/api/admin/splash-ads", response_model=ApiResponse)
def get_splash_ads(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    is_active: bool = Query(None),
    db: Session = Depends(get_db),
    admin: dict = Depends(get_current_admin)
):
    query = db.query(SplashAd)
    if is_active is not None:
        query = query.filter(SplashAd.is_active == is_active)
    
    total = query.count()
    offset = (page - 1) * page_size
    ads = query.order_by(SplashAd.sort_order.desc(), SplashAd.id.desc()).offset(offset).limit(page_size).all()
    
    return ApiResponse(
        code=0,
        message="success",
        data={
            "list": [SplashAdResponse.from_orm(ad) for ad in ads],
            "total": total,
            "page": page,
            "page_size": page_size
        }
    )


@router.get("/api/admin/splash-ads/{ad_id}", response_model=ApiResponse)
def get_splash_ad_detail(ad_id: int, db: Session = Depends(get_db), admin: dict = Depends(get_current_admin)):
    ad = db.query(SplashAd).filter(SplashAd.id == ad_id).first()
    if not ad:
        return ApiResponse(code=1, message="广告不存在")
    
    return ApiResponse(code=0, message="success", data=SplashAdResponse.from_orm(ad))


@router.post("/api/admin/splash-ads", response_model=ApiResponse)
def create_splash_ad(request: SplashAdCreateRequest, db: Session = Depends(get_db), admin: dict = Depends(get_current_admin)):
    ad = SplashAd(
        title=request.title or "",
        image_url=request.image_url or "",
        video_url=request.video_url or "",
        ad_type=request.ad_type or "image",
        duration=request.duration or 5,
        skip_enabled=request.skip_enabled if request.skip_enabled is not None else True,
        link_type=request.link_type or "none",
        link_url=request.link_url or "",
        link_page=request.link_page or "",
        is_active=request.is_active if request.is_active is not None else True,
        sort_order=request.sort_order or 0,
        start_time=request.start_time,
        end_time=request.end_time,
        daily_limit=request.daily_limit or 1
    )
    db.add(ad)
    db.commit()
    db.refresh(ad)
    
    return ApiResponse(code=0, message="创建成功", data=SplashAdResponse.from_orm(ad))


@router.put("/api/admin/splash-ads/{ad_id}", response_model=ApiResponse)
def update_splash_ad(ad_id: int, request: SplashAdUpdateRequest, db: Session = Depends(get_db), admin: dict = Depends(get_current_admin)):
    ad = db.query(SplashAd).filter(SplashAd.id == ad_id).first()
    if not ad:
        return ApiResponse(code=1, message="广告不存在")
    
    update_data = request.dict(exclude_unset=True)
    for key, value in update_data.items():
        if value is not None:
            setattr(ad, key, value)
    
    db.commit()
    db.refresh(ad)
    
    return ApiResponse(code=0, message="更新成功", data=SplashAdResponse.from_orm(ad))


@router.delete("/api/admin/splash-ads/{ad_id}", response_model=ApiResponse)
def delete_splash_ad(ad_id: int, db: Session = Depends(get_db), admin: dict = Depends(get_current_admin)):
    ad = db.query(SplashAd).filter(SplashAd.id == ad_id).first()
    if not ad:
        return ApiResponse(code=1, message="广告不存在")
    
    db.delete(ad)
    db.commit()
    
    return ApiResponse(code=0, message="删除成功")


@router.patch("/api/admin/splash-ads/{ad_id}/toggle", response_model=ApiResponse)
def toggle_splash_ad(ad_id: int, db: Session = Depends(get_db), admin: dict = Depends(get_current_admin)):
    ad = db.query(SplashAd).filter(SplashAd.id == ad_id).first()
    if not ad:
        return ApiResponse(code=1, message="广告不存在")
    
    ad.is_active = not ad.is_active
    db.commit()
    
    return ApiResponse(code=0, message="success", data={"is_active": ad.is_active})
