from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
import uuid

from database import get_db
from models import User
from schemas import WechatLoginRequest, LoginResponse
from utils.wechat import wechat_login
from utils.security import create_access_token

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
                "status": user.status
            }
        }
    )
