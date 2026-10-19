from sqlalchemy import Column, Integer, String, DateTime, Text
from sqlalchemy.sql import func
from database import Base


class AccessLog(Base):
    __tablename__ = "access_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(64), index=True, default="")
    session_id = Column(String(128), default="")
    page = Column(String(128), default="")
    action = Column(String(64), default="")
    target_id = Column(String(64), default="")
    target_type = Column(String(32), default="")
    ip = Column(String(64), default="")
    user_agent = Column(String(512), default="")
    referer = Column(String(255), default="")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)


class OperationLog(Base):
    __tablename__ = "operation_logs"

    id = Column(Integer, primary_key=True, index=True)
    admin_id = Column(String(64), index=True, default="")
    admin_name = Column(String(64), default="")
    module = Column(String(64), default="")
    action = Column(String(64), default="")
    target_id = Column(String(64), default="")
    target_name = Column(String(255), default="")
    before_data = Column(Text, default="")
    after_data = Column(Text, default="")
    ip = Column(String(64), default="")
    user_agent = Column(String(512), default="")
    remark = Column(String(255), default="")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
