from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime

from database import get_db
from models import Order, Buyer, User
from schemas import (
    ApiResponse,
    OrderCreateRequest,
    OrderUpdateRequest,
    OrderResponse,
)
from utils.security import get_current_user_optional
from utils.wechat_pay import create_vip_payment, verify_payment_notify, generate_out_trade_no
from config import DEBUG

router = APIRouter(prefix="/api/order", tags=["订单管理"])


@router.get("/list", response_model=ApiResponse)
def get_orders(
    user_id: str = Query(None, description="用户ID"),
    buyer_id: str = Query(None, description="买手ID"),
    status: str = Query(None, description="订单状态"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    query = db.query(Order)

    if user_id:
        query = query.filter(Order.user_id == user_id)
    if buyer_id:
        query = query.filter(Order.buyer_id == buyer_id)
    if status:
        query = query.filter(Order.status == status)

    total = query.count()
    offset = (page - 1) * page_size
    orders = query.order_by(Order.created_at.desc()).offset(offset).limit(page_size).all()

    return ApiResponse(
        code=0,
        message="success",
        data={
            "list": [OrderResponse.from_orm(o) for o in orders],
            "total": total,
            "page": page,
            "page_size": page_size
        }
    )


@router.get("/{order_id}", response_model=ApiResponse)
def get_order(order_id: str, db: Session = Depends(get_db)):
    order = db.query(Order).filter(Order.order_id == order_id).first()

    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="订单不存在"
        )

    return ApiResponse(
        code=0,
        message="success",
        data=OrderResponse.from_orm(order)
    )


@router.post("", response_model=ApiResponse)
def create_order(request: OrderCreateRequest, db: Session = Depends(get_db)):
    order_id = "ORD" + str(int(datetime.now().timestamp() * 1000))

    buyer_name = ""
    if request.buyer_id:
        buyer = db.query(Buyer).filter(Buyer.buyer_id == request.buyer_id).first()
        if buyer:
            buyer_name = buyer.name

    fee_amount = request.fee_amount
    if fee_amount == 0 and request.cny_price > 0 and request.fee_rate > 0:
        fee_amount = round(request.cny_price * request.fee_rate / 100, 2)

    total_amount = request.total_amount
    if total_amount == 0:
        total_amount = round(request.cny_price * request.quantity + fee_amount + request.shipping_fee, 2)

    order = Order(
        order_id=order_id,
        user_id=request.user_id,
        buyer_id=request.buyer_id or "",
        buyer_name=buyer_name,
        spu_id=request.spu_id or "",
        sku_id=request.sku_id or "",
        product_name=request.product_name or "",
        product_image=request.product_image or "",
        sku_spec=request.sku_spec or "",
        quantity=request.quantity or 1,
        original_price=request.original_price or 0,
        original_currency=request.original_currency or "CNY",
        cny_price=request.cny_price or 0,
        fee_rate=request.fee_rate or 0,
        fee_amount=fee_amount,
        shipping_fee=request.shipping_fee or 0,
        total_amount=total_amount,
        status="pending",
        country=request.country or "",
        store=request.store or "",
        remark=request.remark or "",
        receiver_name=request.receiver_name or "",
        receiver_phone=request.receiver_phone or "",
        receiver_address=request.receiver_address or "",
    )

    db.add(order)
    db.commit()
    db.refresh(order)

    return ApiResponse(
        code=0,
        message="创建成功",
        data=OrderResponse.from_orm(order)
    )


@router.put("/{order_id}", response_model=ApiResponse)
def update_order(order_id: str, request: OrderUpdateRequest, db: Session = Depends(get_db)):
    order = db.query(Order).filter(Order.order_id == order_id).first()

    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="订单不存在"
        )

    if request.status is not None:
        order.status = request.status
        now = datetime.utcnow()
        if request.status == "paid" and not order.paid_at:
            order.paid_at = now
        elif request.status == "shipped" and not order.shipped_at:
            order.shipped_at = now
        elif request.status == "completed" and not order.completed_at:
            order.completed_at = now
        elif request.status == "cancelled" and not order.cancelled_at:
            order.cancelled_at = now

    if request.tracking_no is not None:
        order.tracking_no = request.tracking_no
    if request.tracking_company is not None:
        order.tracking_company = request.tracking_company
    if request.receiver_name is not None:
        order.receiver_name = request.receiver_name
    if request.receiver_phone is not None:
        order.receiver_phone = request.receiver_phone
    if request.receiver_address is not None:
        order.receiver_address = request.receiver_address
    if request.remark is not None:
        order.remark = request.remark

    db.commit()
    db.refresh(order)

    return ApiResponse(
        code=0,
        message="更新成功",
        data=OrderResponse.from_orm(order)
    )


@router.put("/{order_id}/status", response_model=ApiResponse)
def update_order_status(
    order_id: str,
    status_value: str = Query(..., description="订单状态"),
    db: Session = Depends(get_db)
):
    order = db.query(Order).filter(Order.order_id == order_id).first()

    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="订单不存在"
        )

    valid_statuses = ["pending", "paid", "shipped", "completed", "cancelled", "refunded"]
    if status_value not in valid_statuses:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="无效的订单状态"
        )

    order.status = status_value
    now = datetime.utcnow()
    if status_value == "paid" and not order.paid_at:
        order.paid_at = now
    elif status_value == "shipped" and not order.shipped_at:
        order.shipped_at = now
    elif status_value == "completed" and not order.completed_at:
        order.completed_at = now
    elif status_value == "cancelled" and not order.cancelled_at:
        order.cancelled_at = now

    db.commit()
    db.refresh(order)

    return ApiResponse(
        code=0,
        message="状态更新成功",
        data=OrderResponse.from_orm(order)
    )


@router.delete("/{order_id}", response_model=ApiResponse)
def delete_order(order_id: str, db: Session = Depends(get_db)):
    order = db.query(Order).filter(Order.order_id == order_id).first()

    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="订单不存在"
        )

    db.delete(order)
    db.commit()

    return ApiResponse(
        code=0,
        message="删除成功"
    )


@router.post("/{order_id}/pay", response_model=ApiResponse)
def pay_order(
    order_id: str,
    current_user: User = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    order = db.query(Order).filter(Order.order_id == order_id).first()

    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="订单不存在"
        )

    if order.status == "paid":
        return ApiResponse(code=0, message="订单已支付", data={"status": "paid"})

    if order.status not in ["pending"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="当前订单状态无法支付"
        )

    openid = ""
    if current_user:
        openid = current_user.openid or ""

    try:
        pay_params = create_vip_payment(
            out_trade_no=order.order_id,
            openid=openid,
            total_fee=int(float(order.total_amount) * 100),
            body=f"订单支付 - {order.product_name[:30]}"
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
            "order_id": order.order_id,
            "total_amount": float(order.total_amount),
            "pay_params": pay_params
        }
    )


@router.post("/pay/notify")
async def order_pay_notify(request: Request, db: Session = Depends(get_db)):
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

    order = db.query(Order).filter(Order.order_id == out_trade_no).first()

    if not order:
        return "<xml><return_code><![CDATA[SUCCESS]]></return_code><return_msg><![CDATA[OK]]></return_msg></xml>"

    if order.status == "paid":
        return "<xml><return_code><![CDATA[SUCCESS]]></return_code><return_msg><![CDATA[OK]]></return_msg></xml>"

    order.status = "paid"
    order.paid_at = datetime.now()

    db.commit()

    return "<xml><return_code><![CDATA[SUCCESS]]></return_code><return_msg><![CDATA[OK]]></return_msg></xml>"


@router.post("/mock-pay/{order_id}", response_model=ApiResponse)
def mock_pay_order(
    order_id: str,
    db: Session = Depends(get_db)
):
    if not DEBUG:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="仅调试模式可用"
        )

    order = db.query(Order).filter(Order.order_id == order_id).first()
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="订单不存在"
        )

    if order.status == "paid":
        return ApiResponse(code=0, message="订单已支付", data={"status": order.status})

    order.status = "paid"
    order.paid_at = datetime.now()

    db.commit()
    db.refresh(order)

    return ApiResponse(
        code=0,
        message="模拟支付成功",
        data={
            "order_id": order.order_id,
            "status": "paid",
            "paid_at": order.paid_at.isoformat() if order.paid_at else None
        }
    )
