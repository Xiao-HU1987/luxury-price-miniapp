from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
import uuid

from database import get_db
from models import User
from schemas import WechatLoginRequest, LoginResponse, ApiResponse
from utils.wechat import wechat_login
from utils.security import create_access_token, get_current_user

router = APIRouter(prefix="/api/auth", tags=["认证"])


@router.post("/wechat-login", response_model=LoginResponse)
async def wechat_login_endpoint(request: WechatLoginRequest, db: Session = Depends(get_db)):
    try:
        wechat_data = await wechat_login(request.code)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

    openid = wechat_data.get("openid")
    session_key = wechat_data.get("session_key")

    if not openid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="微信登录失败，未获取到openid"
        )

    user = db.query(User).filter(User.openid == openid).first()

    is_new = False
    if not user:
        user_id = f"U{uuid.uuid4().hex[:10].upper()}"
        user = User(
            user_id=user_id,
            openid=openid,
            nickname="",
            avatar="",
            phone="",
            is_vip=False,
            is_admin=False,
            is_buyer=False,
            status="active"
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        is_new = True

    access_token = create_access_token(data={"sub": user.user_id})

    return LoginResponse(
        code=0,
        message="success",
        data={
            "access_token": access_token,
            "token_type": "bearer",
            "is_new": is_new,
            "session_key": session_key,
            "user": {
                "user_id": user.user_id,
                "nickname": user.nickname,
                "avatar": user.avatar,
                "phone": user.phone,
                "is_vip": user.is_vip,
                "is_admin": user.is_admin,
                "is_buyer": user.is_buyer,
                "status": user.status,
                "vip_expire_time": user.vip_expire_time.isoformat() if user.vip_expire_time else None
            }
        }
    )


@router.get("/check", response_model=ApiResponse)
def check_login(current_user: User = Depends(get_current_user)):
    return ApiResponse(
        code=0,
        message="success",
        data={
            "is_logged_in": True,
            "user": {
                "user_id": current_user.user_id,
                "nickname": current_user.nickname,
                "avatar": current_user.avatar,
                "phone": current_user.phone,
                "is_vip": current_user.is_vip,
                "is_admin": current_user.is_admin,
                "is_buyer": current_user.is_buyer,
                "status": current_user.status,
                "vip_expire_time": current_user.vip_expire_time.isoformat() if current_user.vip_expire_time else None
            }
        }
    )


@router.post("/refresh", response_model=LoginResponse)
def refresh_token(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    access_token = create_access_token(data={"sub": current_user.user_id})
    
    return LoginResponse(
        code=0,
        message="success",
        data={
            "access_token": access_token,
            "token_type": "bearer",
            "is_new": False,
            "user": {
                "user_id": current_user.user_id,
                "nickname": current_user.nickname,
                "avatar": current_user.avatar,
                "phone": current_user.phone,
                "is_vip": current_user.is_vip,
                "is_admin": current_user.is_admin,
                "is_buyer": current_user.is_buyer,
                "status": current_user.status,
                "vip_expire_time": current_user.vip_expire_time.isoformat() if current_user.vip_expire_time else None
            }
        }
    )
