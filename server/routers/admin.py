from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, distinct, or_
from datetime import datetime, timedelta
from pydantic import BaseModel
from typing import Optional

from database import get_db
from models import User, Order, SPU, Brand, Buyer, Demand, AccessLog, Coupon, Store
from schemas import ApiResponse
from utils.security import create_access_token, get_password_hash, verify_password, get_current_admin

router = APIRouter(prefix="/api/admin", tags=["管理后台"])


class AdminLoginRequest(BaseModel):
    username: str
    password: str


class AdminUserUpdateRequest(BaseModel):
    user_id: str
    nickname: Optional[str] = None
    is_vip: Optional[bool] = None
    is_buyer: Optional[bool] = None
    is_admin: Optional[bool] = None
    status: Optional[str] = None


# 预置管理员账号（实际项目中应存入数据库）
ADMIN_ACCOUNTS = {
    "admin": {
        "password_hash": get_password_hash("admin123"),
        "nickname": "超级管理员",
        "role": "admin"
    }
}


@router.post("/login", response_model=ApiResponse)
def admin_login(request: AdminLoginRequest, db: Session = Depends(get_db)):
    """管理员登录"""
    account = ADMIN_ACCOUNTS.get(request.username)

    # 先查预置账号
    if account:
        if not verify_password(request.password, account["password_hash"]):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="用户名或密码错误"
            )
        token = create_access_token({"sub": f"admin:{request.username}", "role": "admin"})
        return ApiResponse(
            code=0,
            message="登录成功",
            data={
                "token": token,
                "user": {
                    "id": request.username,
                    "username": request.username,
                    "nickname": account["nickname"],
                    "role": "admin"
                }
            }
        )

    # 再查数据库中 is_admin=True 的用户（通过 user_id 或 phone 登录）
    user = db.query(User).filter(
        User.is_admin == True,
        or_(User.user_id == request.username, User.phone == request.username)
    ).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误"
        )

    # 简单密码校验（实际项目中应使用 hashed password）
    if user.status != "active":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="账号已被禁用"
        )

    token = create_access_token({"sub": user.user_id, "role": "admin"})
    return ApiResponse(
        code=0,
        message="登录成功",
        data={
            "token": token,
            "user": {
                "id": user.user_id,
                "username": user.user_id,
                "nickname": user.nickname or "管理员",
                "role": "admin"
            }
        }
    )


@router.get("/users", response_model=ApiResponse)
def get_users(
    user_id: str = Query(None),
    role: str = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    admin: dict = Depends(get_current_admin)
):
    """获取用户列表"""
    query = db.query(User)

    if user_id:
        query = query.filter(User.user_id == user_id)
    if role == "vip":
        query = query.filter(User.is_vip == True)
    elif role == "buyer":
        query = query.filter(User.is_buyer == True)
    elif role == "normal":
        query = query.filter(User.is_vip == False, User.is_buyer == False)

    total = query.count()
    offset = (page - 1) * page_size
    users = query.order_by(User.created_at.desc()).offset(offset).limit(page_size).all()

    return ApiResponse(
        code=0,
        message="success",
        data={
            "list": [{
                "user_id": u.user_id,
                "nickname": u.nickname,
                "avatar": u.avatar,
                "phone": u.phone,
                "is_vip": u.is_vip,
                "is_admin": u.is_admin,
                "is_buyer": u.is_buyer,
                "status": u.status,
                "created_at": u.created_at.isoformat() if u.created_at else None
            } for u in users],
            "total": total,
            "page": page,
            "page_size": page_size
        }
    )


@router.put("/users", response_model=ApiResponse)
def admin_update_user(request: AdminUserUpdateRequest, db: Session = Depends(get_db), admin: dict = Depends(get_current_admin)):
    """管理员编辑用户"""
    user = db.query(User).filter(User.user_id == request.user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")

    if request.nickname is not None:
        user.nickname = request.nickname
    if request.is_vip is not None:
        user.is_vip = request.is_vip
    if request.is_buyer is not None:
        user.is_buyer = request.is_buyer
    if request.is_admin is not None:
        user.is_admin = request.is_admin
    if request.status is not None:
        user.status = request.status

    db.commit()
    db.refresh(user)

    return ApiResponse(
        code=0,
        message="修改成功",
        data={
            "user_id": user.user_id,
            "nickname": user.nickname,
            "is_vip": user.is_vip,
            "is_admin": user.is_admin,
            "is_buyer": user.is_buyer,
            "status": user.status
        }
    )


@router.get("/dashboard/stats", response_model=ApiResponse)
def get_dashboard_stats(db: Session = Depends(get_db), admin: dict = Depends(get_current_admin)):
    today = datetime.now().date()
    today_start = datetime.combine(today, datetime.min.time())
    yesterday = today - timedelta(days=1)
    yesterday_start = datetime.combine(yesterday, datetime.min.time())

    total_users = db.query(User).count()
    today_new_users = db.query(User).filter(User.created_at >= today_start).count()
    vip_users = db.query(User).filter(User.is_vip == True).count()
    buyer_users = db.query(User).filter(User.is_buyer == True).count()

    total_orders = db.query(Order).count()
    today_orders = db.query(Order).filter(Order.created_at >= today_start).count()
    paid_orders = db.query(Order).filter(Order.status == "paid").count()
    completed_orders = db.query(Order).filter(Order.status == "completed").count()
    total_sales = db.query(func.sum(Order.total_amount)).filter(Order.status.in_(["paid", "shipped", "completed"])).scalar() or 0
    today_sales = db.query(func.sum(Order.total_amount)).filter(
        Order.created_at >= today_start,
        Order.status.in_(["paid", "shipped", "completed"])
    ).scalar() or 0

    total_products = db.query(SPU).count()
    total_brands = db.query(Brand).count()
    total_buyers = db.query(Buyer).count()
    total_demands = db.query(Demand).count()
    total_coupons = db.query(Coupon).count()
    total_stores = db.query(Store).count()

    today_pv = db.query(AccessLog).filter(AccessLog.created_at >= today_start).count()
    today_uv = db.query(func.count(distinct(AccessLog.user_id))).filter(
        AccessLog.created_at >= today_start,
        AccessLog.user_id != ""
    ).scalar() or 0

    yesterday_pv = db.query(AccessLog).filter(
        AccessLog.created_at >= yesterday_start,
        AccessLog.created_at < today_start
    ).count()
    yesterday_uv = db.query(func.count(distinct(AccessLog.user_id))).filter(
        AccessLog.created_at >= yesterday_start,
        AccessLog.created_at < today_start,
        AccessLog.user_id != ""
    ).scalar() or 0

    return ApiResponse(
        code=0,
        message="success",
        data={
            "user": {
                "total": total_users,
                "today_new": today_new_users,
                "vip": vip_users,
                "buyer": buyer_users
            },
            "order": {
                "total": total_orders,
                "today": today_orders,
                "paid": paid_orders,
                "completed": completed_orders,
                "total_sales": float(total_sales),
                "today_sales": float(today_sales)
            },
            "product": {
                "total": total_products,
                "brands": total_brands
            },
            "buyer": {
                "total": total_buyers,
                "demands": total_demands
            },
            "other": {
                "coupons": total_coupons,
                "stores": total_stores
            },
            "traffic": {
                "today_pv": today_pv,
                "today_uv": today_uv,
                "yesterday_pv": yesterday_pv,
                "yesterday_uv": yesterday_uv
            }
        }
    )


@router.get("/dashboard/order-trend", response_model=ApiResponse)
def get_order_trend(
    days: int = Query(7, description="天数", ge=1, le=30),
    db: Session = Depends(get_db),
    admin: dict = Depends(get_current_admin)
):
    today = datetime.now().date()
    result = []

    for i in range(days - 1, -1, -1):
        date = today - timedelta(days=i)
        date_str = date.strftime("%m-%d")
        day_start = datetime.combine(date, datetime.min.time())
        day_end = datetime.combine(date, datetime.max.time())

        order_count = db.query(Order).filter(
            Order.created_at >= day_start,
            Order.created_at <= day_end
        ).count()
        sales = db.query(func.sum(Order.total_amount)).filter(
            Order.created_at >= day_start,
            Order.created_at <= day_end,
            Order.status.in_(["paid", "shipped", "completed"])
        ).scalar() or 0

        result.append({
            "date": date_str,
            "orders": order_count,
            "sales": float(sales)
        })

    return ApiResponse(
        code=0,
        message="success",
        data=result
    )


@router.get("/dashboard/traffic-trend", response_model=ApiResponse)
def get_traffic_trend(
    days: int = Query(7, description="天数", ge=1, le=30),
    db: Session = Depends(get_db),
    admin: dict = Depends(get_current_admin)
):
    today = datetime.now().date()
    result = []

    for i in range(days - 1, -1, -1):
        date = today - timedelta(days=i)
        date_str = date.strftime("%m-%d")
        day_start = datetime.combine(date, datetime.min.time())
        day_end = datetime.combine(date, datetime.max.time())

        pv = db.query(AccessLog).filter(
            AccessLog.created_at >= day_start,
            AccessLog.created_at <= day_end
        ).count()
        uv = db.query(func.count(distinct(AccessLog.user_id))).filter(
            AccessLog.created_at >= day_start,
            AccessLog.created_at <= day_end,
            AccessLog.user_id != ""
        ).scalar() or 0

        result.append({
            "date": date_str,
            "pv": pv,
            "uv": uv
        })

    return ApiResponse(
        code=0,
        message="success",
        data=result
    )


@router.get("/dashboard/hot-products", response_model=ApiResponse)
def get_hot_products(
    limit: int = Query(10, description="数量", ge=1, le=50),
    db: Session = Depends(get_db),
    admin: dict = Depends(get_current_admin)
):
    spus = db.query(SPU).order_by(SPU.created_at.desc()).limit(limit).all()
    result = []
    for spu in spus:
        result.append({
            "spu_id": spu.spu_id,
            "name": spu.name,
            "brand_name": spu.brand_name,
            "article_no": spu.article_no,
            "view_count": 0
        })

    return ApiResponse(
        code=0,
        message="success",
        data=result
    )
