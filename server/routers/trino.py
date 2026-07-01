from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from database import get_db
from schemas import ApiResponse
from utils.trino_db import TrinoClient, TrinoUnavailableError

router = APIRouter(prefix="/api/trino", tags=["Trino数据"])
trino_client = TrinoClient()


@router.get("/health", response_model=ApiResponse)
def get_trino_health():
    if not trino_client.is_enabled():
        return ApiResponse(
            code=0,
            message="success",
            data={
                "enabled": False,
                "status": "disabled",
                "host": trino_client.config.host,
                "port": trino_client.config.port,
                "catalog": trino_client.config.catalog,
                "schema": trino_client.config.schema,
            }
        )

    try:
        trino_client.query_one("SELECT 1 AS ok")
        return ApiResponse(
            code=0,
            message="success",
            data={
                "enabled": True,
                "status": "ok",
                "host": trino_client.config.host,
                "port": trino_client.config.port,
                "catalog": trino_client.config.catalog,
                "schema": trino_client.config.schema,
            }
        )
    except TrinoUnavailableError as exc:
        return ApiResponse(
            code=1,
            message=str(exc),
            data={
                "enabled": True,
                "status": "error",
                "host": trino_client.config.host,
                "port": trino_client.config.port,
                "catalog": trino_client.config.catalog,
                "schema": trino_client.config.schema,
            }
        )


@router.get("/summary", response_model=ApiResponse)
def get_trino_summary():
    try:
        data = {
            "health": trino_client.query_one("SELECT 1 AS ok"),
            "exchange_rates": trino_client.get_exchange_rates(),
            "buyers": trino_client.get_buyer_list(page=1, page_size=5),
            "stores": trino_client.get_store_list(page=1, page_size=5),
            "coupons": trino_client.get_coupon_list(page=1, page_size=5),
            "orders": trino_client.get_order_list(page=1, page_size=5),
        }
        return ApiResponse(code=0, message="success", data=data)
    except TrinoUnavailableError as exc:
        return ApiResponse(code=1, message=str(exc), data=None)


@router.get("/buyers", response_model=ApiResponse)
def list_buyers(
    country: str = Query(None),
    city: str = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    try:
        return ApiResponse(code=0, message="success", data=trino_client.get_buyer_list(country=country, city=city, page=page, page_size=page_size))
    except TrinoUnavailableError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc))


@router.get("/buyers/{buyer_id}", response_model=ApiResponse)
def get_buyer(buyer_id: str):
    try:
        buyer = trino_client.get_buyer_detail(buyer_id)
        if not buyer:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="买手不存在")
        return ApiResponse(code=0, message="success", data=buyer)
    except TrinoUnavailableError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc))


@router.get("/stores", response_model=ApiResponse)
def list_stores(
    country: str = Query(None),
    city: str = Query(None),
    type: str = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    try:
        return ApiResponse(code=0, message="success", data=trino_client.get_store_list(country=country, city=city, type=type, page=page, page_size=page_size))
    except TrinoUnavailableError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc))


@router.get("/stores/{store_id}", response_model=ApiResponse)
def get_store(store_id: str):
    try:
        store = trino_client.get_store_detail(store_id)
        if not store:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="店铺不存在")
        return ApiResponse(code=0, message="success", data=store)
    except TrinoUnavailableError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc))


@router.get("/coupons", response_model=ApiResponse)
def list_coupons(
    country: str = Query(None),
    store_id: str = Query(None),
    status_value: str = Query(None, alias="status"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    try:
        return ApiResponse(code=0, message="success", data=trino_client.get_coupon_list(country=country, store_id=store_id, status=status_value, page=page, page_size=page_size))
    except TrinoUnavailableError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc))


@router.get("/coupons/{coupon_id}", response_model=ApiResponse)
def get_coupon(coupon_id: str):
    try:
        coupon = trino_client.get_coupon_detail(coupon_id)
        if not coupon:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="优惠券不存在")
        return ApiResponse(code=0, message="success", data=coupon)
    except TrinoUnavailableError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc))


@router.get("/orders", response_model=ApiResponse)
def list_orders(
    user_id: str = Query(None),
    buyer_id: str = Query(None),
    status_value: str = Query(None, alias="status"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    try:
        return ApiResponse(code=0, message="success", data=trino_client.get_order_list(user_id=user_id, buyer_id=buyer_id, status=status_value, page=page, page_size=page_size))
    except TrinoUnavailableError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc))


@router.get("/orders/{order_id}", response_model=ApiResponse)
def get_order(order_id: str):
    try:
        order = trino_client.get_order_detail(order_id)
        if not order:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="订单不存在")
        return ApiResponse(code=0, message="success", data=order)
    except TrinoUnavailableError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc))
