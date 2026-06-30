from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel

from database import get_db
from models import User
from utils.security import create_access_token, verify_password, get_password_hash

router = APIRouter(prefix="/api/admin/auth", tags=["管理端认证"])


class AdminLoginRequest(BaseModel):
    username: str
    password: str


@router.post("/login")
def admin_login(request: AdminLoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.phone == request.username).first()
    if not user:
        user = db.query(User).filter(User.user_id == request.username).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误"
        )
    if not user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="不是管理员账号"
        )
    if user.status != "active":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="账号已被禁用"
        )
    if not user.password_hash:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="该管理员账号未设置密码"
        )
    if not verify_password(request.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误"
        )

    access_token = create_access_token(data={"sub": user.user_id})
    return {
        "code": 0,
        "message": "success",
        "data": {
            "access_token": access_token,
            "token_type": "bearer",
            "user": {
                "user_id": user.user_id,
                "nickname": user.nickname,
                "avatar": user.avatar,
                "phone": user.phone,
                "is_admin": user.is_admin
            }
        }
    }
