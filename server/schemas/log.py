from pydantic import BaseModel, Field
from typing import Optional, Any
from datetime import datetime


class AccessLogCreateRequest(BaseModel):
    user_id: Optional[str] = ""
    session_id: Optional[str] = ""
    page: Optional[str] = ""
    action: Optional[str] = ""
    target_id: Optional[str] = ""
    target_type: Optional[str] = ""
    ip: Optional[str] = ""
    user_agent: Optional[str] = ""
    referer: Optional[str] = ""


class AccessLogResponse(BaseModel):
    id: int
    user_id: str
    session_id: str
    page: str
    action: str
    target_id: str
    target_type: str
    ip: str
    user_agent: str
    referer: str
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class OperationLogCreateRequest(BaseModel):
    admin_id: Optional[str] = ""
    admin_name: Optional[str] = ""
    module: Optional[str] = ""
    action: Optional[str] = ""
    target_id: Optional[str] = ""
    target_name: Optional[str] = ""
    before_data: Optional[str] = ""
    after_data: Optional[str] = ""
    ip: Optional[str] = ""
    user_agent: Optional[str] = ""
    remark: Optional[str] = ""


class OperationLogResponse(BaseModel):
    id: int
    admin_id: str
    admin_name: str
    module: str
    action: str
    target_id: str
    target_name: str
    before_data: str
    after_data: str
    ip: str
    user_agent: str
    remark: str
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True
