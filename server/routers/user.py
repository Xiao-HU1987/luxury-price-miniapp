from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from database import get_db
from models import User
from schemas import ProfileUpdateRequest, PhoneUpdateRequest, ApiResponse
from utils.security import get_current_user
from utils.wechat import decrypt_wechat_phone

router = APIRouter(prefix="/api/user", tags=["用户"])


@router.get("/profile", response_model=ApiResponse)
def get_profile(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return ApiResponse(
        code=0,
        message="success",
        data={
            "user_id": current_user.user_id,
            "nickname": current_user.nickname,
            "avatar": current_user.avatar,
            "phone": current_user.phone,
            "is_vip": current_user.is_vip,
            "is_admin": current_user.is_admin,
            "is_buyer": current_user.is_buyer,
            "status": current_user.status,
            "is_registered": bool(current_user.phone and current_user.nickname)
        }
    )


@router.put("/profile", response_model=ApiResponse)
def update_profile(
    request: ProfileUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if request.nickname is not None:
        current_user.nickname = request.nickname
    if request.avatar is not None:
        current_user.avatar = request.avatar

    db.commit()
    db.refresh(current_user)

    return ApiResponse(
        code=0,
        message="更新成功",
        data={
            "user_id": current_user.user_id,
            "nickname": current_user.nickname,
            "avatar": current_user.avatar,
            "phone": current_user.phone,
            "is_vip": current_user.is_vip,
            "is_admin": current_user.is_admin,
            "is_buyer": current_user.is_buyer
        }
    )


@router.put("/phone", response_model=ApiResponse)
def update_phone(
    request: PhoneUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    phone = decrypt_wechat_phone(
        request.encrypted_data,
        request.iv,
        request.session_key
    )

    if not phone:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="手机号解密失败"
        )

    current_user.phone = phone
    db.commit()
    db.refresh(current_user)

    return ApiResponse(
        code=0,
        message="手机号更新成功",
        data={
            "user_id": current_user.user_id,
            "phone": current_user.phone
        }
    )
