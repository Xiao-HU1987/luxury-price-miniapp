from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func

from database import get_db
from models import AccessLog, OperationLog
from schemas import (
    ApiResponse,
    AccessLogCreateRequest,
    AccessLogResponse,
    OperationLogCreateRequest,
    OperationLogResponse,
)

router = APIRouter(prefix="/api/log", tags=["日志管理"])


@router.post("/access", response_model=ApiResponse)
def create_access_log(request: AccessLogCreateRequest, db: Session = Depends(get_db)):
    log = AccessLog(
        user_id=request.user_id or "",
        session_id=request.session_id or "",
        page=request.page or "",
        action=request.action or "",
        target_id=request.target_id or "",
        target_type=request.target_type or "",
        ip=request.ip or "",
        user_agent=request.user_agent or "",
        referer=request.referer or "",
    )
    db.add(log)
    db.commit()
    db.refresh(log)

    return ApiResponse(
        code=0,
        message="记录成功",
        data=AccessLogResponse.from_orm(log)
    )


@router.get("/access/list", response_model=ApiResponse)
def get_access_logs(
    user_id: str = Query(None, description="用户ID"),
    page_path: str = Query(None, description="页面路径"),
    action: str = Query(None, description="操作类型"),
    start_date: str = Query(None, description="开始日期"),
    end_date: str = Query(None, description="结束日期"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    query = db.query(AccessLog)

    if user_id:
        query = query.filter(AccessLog.user_id == user_id)
    if page_path:
        query = query.filter(AccessLog.page.contains(page_path))
    if action:
        query = query.filter(AccessLog.action == action)
    if start_date:
        query = query.filter(AccessLog.created_at >= start_date)
    if end_date:
        query = query.filter(AccessLog.created_at <= end_date + " 23:59:59")

    total = query.count()
    offset = (page - 1) * page_size
    logs = query.order_by(AccessLog.created_at.desc()).offset(offset).limit(page_size).all()

    return ApiResponse(
        code=0,
        message="success",
        data={
            "list": [AccessLogResponse.from_orm(l) for l in logs],
            "total": total,
            "page": page,
            "page_size": page_size
        }
    )


@router.post("/operation", response_model=ApiResponse)
def create_operation_log(request: OperationLogCreateRequest, db: Session = Depends(get_db)):
    log = OperationLog(
        admin_id=request.admin_id or "",
        admin_name=request.admin_name or "",
        module=request.module or "",
        action=request.action or "",
        target_id=request.target_id or "",
        target_name=request.target_name or "",
        before_data=request.before_data or "",
        after_data=request.after_data or "",
        ip=request.ip or "",
        user_agent=request.user_agent or "",
        remark=request.remark or "",
    )
    db.add(log)
    db.commit()
    db.refresh(log)

    return ApiResponse(
        code=0,
        message="记录成功",
        data=OperationLogResponse.from_orm(log)
    )


@router.get("/operation/list", response_model=ApiResponse)
def get_operation_logs(
    admin_id: str = Query(None, description="管理员ID"),
    module: str = Query(None, description="模块"),
    action: str = Query(None, description="操作类型"),
    start_date: str = Query(None, description="开始日期"),
    end_date: str = Query(None, description="结束日期"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    query = db.query(OperationLog)

    if admin_id:
        query = query.filter(OperationLog.admin_id == admin_id)
    if module:
        query = query.filter(OperationLog.module == module)
    if action:
        query = query.filter(OperationLog.action == action)
    if start_date:
        query = query.filter(OperationLog.created_at >= start_date)
    if end_date:
        query = query.filter(OperationLog.created_at <= end_date + " 23:59:59")

    total = query.count()
    offset = (page - 1) * page_size
    logs = query.order_by(OperationLog.created_at.desc()).offset(offset).limit(page_size).all()

    return ApiResponse(
        code=0,
        message="success",
        data={
            "list": [OperationLogResponse.from_orm(l) for l in logs],
            "total": total,
            "page": page,
            "page_size": page_size
        }
    )
