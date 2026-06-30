from pydantic import BaseModel, Field
from typing import Optional, Any
from datetime import datetime


class WechatLoginRequest(BaseModel):
    code: str


class PhoneUpdateRequest(BaseModel):
    encrypted_data: str
    iv: str
    session_key: str = ""


class ProfileUpdateRequest(BaseModel):
    nickname: Optional[str] = None
    avatar: Optional[str] = None


class UserResponse(BaseModel):
    user_id: str
    nickname: str
    avatar: str
    phone: str
    is_vip: bool
    is_admin: bool
    is_buyer: bool
    status: str
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class LoginResponse(BaseModel):
    code: int = 0
    message: str = "success"
    data: dict


class ApiResponse(BaseModel):
    code: int = 0
    message: str = "success"
    data: Optional[Any] = None
