from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import uuid

from database import get_db
from models import VipPlan, VipOrder, User
from schemas import VipOrderCreateRequest, ApiResponse
from utils.security import get_current_user
from utils.wechat_pay import create_vip_payment, verify_payment_notify, generate_out_trade_no

router = APIRouter(prefix="/api/vip", tags=["VIP会员"])


@router.get("/plans", response_model=ApiResponse)
def get_vip_plans(db: Session = Depends(get_db)):
    plans = db.query(VipPlan).filter(
        VipPlan.is_active == True
    ).order_by(VipPlan.sort_order.desc(), VipPlan.id.asc()).all()
    
    return ApiResponse(
        code=0,
        message="success",
        data=[
            {
                "id": plan.id,
                "plan_id": plan.plan_id,
                "name": plan.name,
                "description": plan.description,
                "duration_days": plan.duration_days,
                "price": float(plan.price),
                "original_price": float(plan.original_price),
                "is_popular": plan.is_popular
            }
            for plan in plans
        ]
    )


@router.post("/order", response_model=ApiResponse)
def create_vip_order(
    request: VipOrderCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    plan = db.query(VipPlan).filter(
        VipPlan.plan_id == request.plan_id,
        VipPlan.is_active == True
    ).first()
    
    if not plan:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="套餐不存在"
        )
    
    order_no = generate_out_trade_no("VIP")
    
    order = VipOrder(
        order_no=order_no,
        user_id=current_user.user_id,
        plan_id=plan.plan_id,
        plan_name=plan.name,
        duration_days=plan.duration_days,
        amount=plan.price,
        status="pending",
        pay_type="wechat"
    )
    db.add(order)
    db.commit()
    db.refresh(order)
    
    try:
        pay_params = create_vip_payment(
            out_trade_no=order_no,
            openid=current_user.openid or "",
            total_fee=int(float(plan.price) * 100),
            body=f"VIP会员 - {plan.name}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"创建支付失败: {str(e)}"
        )
    
    return ApiResponse(
        code=0,
        message="success",
        data={
            "order_no": order_no,
            "amount": float(order.amount),
            "pay_params": pay_params
        }
    )


@router.post("/pay/notify")
async def vip_pay_notify(request: Request, db: Session = Depends(get_db)):
    xml_data = await request.body()
    xml_str = xml_data.decode('utf-8')
    
    try:
        result = verify_payment_notify(xml_str)
    except Exception as e:
        return f"<xml><return_code><![CDATA[FAIL]]></return_code><return_msg><![CDATA[{str(e)}]]></return_msg></xml>"
    
    if result.get("return_code") != "SUCCESS":
        return "<xml><return_code><![CDATA[FAIL]]></return_code><return_msg><![CDATA[支付失败]]></return_msg></xml>"
    
    out_trade_no = result.get("out_trade_no", "")
    transaction_id = result.get("transaction_id", "")
    
    order = db.query(VipOrder).filter(VipOrder.order_no == out_trade_no).first()
    
    if not order:
        return "<xml><return_code><![CDATA[SUCCESS]]></return_code><return_msg><![CDATA[OK]]></return_msg></xml>"
    
    if order.status == "paid":
        return "<xml><return_code><![CDATA[SUCCESS]]></return_code><return_msg><![CDATA[OK]]></return_msg></xml>"
    
    order.status = "paid"
    order.transaction_id = transaction_id
    order.paid_at = datetime.now()
    
    user = db.query(User).filter(User.user_id == order.user_id).first()
    if user:
        now = datetime.now()
        if user.vip_expire_time and user.vip_expire_time > now:
            user.vip_expire_time = user.vip_expire_time + timedelta(days=order.duration_days)
        else:
            user.vip_expire_time = now + timedelta(days=order.duration_days)
        user.is_vip = True
        order.expire_time = user.vip_expire_time
    
    db.commit()
    
    return "<xml><return_code><![CDATA[SUCCESS]]></return_code><return_msg><![CDATA[OK]]></return_msg></xml>"


@router.get("/orders", response_model=ApiResponse)
def get_vip_orders(
    page: int = 1,
    page_size: int = 20,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    query = db.query(VipOrder).filter(VipOrder.user_id == current_user.user_id)
    
    total = query.count()
    offset = (page - 1) * page_size
    orders = query.order_by(VipOrder.id.desc()).offset(offset).limit(page_size).all()
    
    return ApiResponse(
        code=0,
        message="success",
        data={
            "list": [
                {
                    "id": order.id,
                    "order_no": order.order_no,
                    "plan_name": order.plan_name,
                    "duration_days": order.duration_days,
                    "amount": float(order.amount),
                    "status": order.status,
                    "paid_at": order.paid_at.isoformat() if order.paid_at else None,
                    "expire_time": order.expire_time.isoformat() if order.expire_time else None,
                    "created_at": order.created_at.isoformat() if order.created_at else None
                }
                for order in orders
            ],
            "total": total,
            "page": page,
            "page_size": page_size
        }
    )


@router.post("/mock-pay/{order_no}", response_model=ApiResponse)
def mock_vip_pay(
    order_no: str,
    db: Session = Depends(get_db)
):
    from config import DEBUG
    if not DEBUG:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="仅调试模式可用"
        )
    
    order = db.query(VipOrder).filter(VipOrder.order_no == order_no).first()
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="订单不存在"
        )
    
    if order.status == "paid":
        return ApiResponse(code=0, message="订单已支付", data={"status": order.status})
    
    order.status = "paid"
    order.transaction_id = f"MOCK{uuid.uuid4().hex[:20].upper()}"
    order.paid_at = datetime.now()
    
    user = db.query(User).filter(User.user_id == order.user_id).first()
    if user:
        now = datetime.now()
        if user.vip_expire_time and user.vip_expire_time > now:
            user.vip_expire_time = user.vip_expire_time + timedelta(days=order.duration_days)
        else:
            user.vip_expire_time = now + timedelta(days=order.duration_days)
        user.is_vip = True
        order.expire_time = user.vip_expire_time
    
    db.commit()
    
    return ApiResponse(
        code=0,
        message="模拟支付成功",
        data={
            "status": "paid",
            "vip_expire_time": user.vip_expire_time.isoformat() if user and user.vip_expire_time else None
        }
    )
