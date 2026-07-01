from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class FavoriteCreateRequest(BaseModel):
    user_id: str
    target_type: Optional[str] = "product"
    target_id: str
    target_name: Optional[str] = ""
    target_image: Optional[str] = ""
    remark: Optional[str] = ""


class FavoriteResponse(BaseModel):
    id: int
    user_id: str
    target_type: str
    target_id: str
    target_name: str
    target_image: str
    remark: str
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class BrowseHistoryCreateRequest(BaseModel):
    user_id: str
    target_type: Optional[str] = "product"
    target_id: str
    target_name: Optional[str] = ""
    target_image: Optional[str] = ""


class BrowseHistoryResponse(BaseModel):
    id: int
    user_id: str
    target_type: str
    target_id: str
    target_name: str
    target_image: str
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True
