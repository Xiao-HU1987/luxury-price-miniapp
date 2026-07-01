from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database import engine, Base
from models import *
from config import DEBUG

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="奢侈品比价小程序 API",
    description="全球奢侈品价格比价小程序后端接口",
    version="1.0.0",
    debug=DEBUG,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from routers.auth import router as auth_router
from routers.user import router as user_router
from routers.product import router as product_router
from routers.exchange import router as exchange_router
from routers.coupon import router as coupon_router
from routers.store import router as store_router
from routers.rebate import router as rebate_router
from routers.buyer import router as buyer_router
from routers.demand import router as demand_router
from routers.order import router as order_router
from routers.log import router as log_router
from routers.admin import router as admin_router
from routers.user_feature import router as user_feature_router
from routers.splash_ad import router as splash_ad_router
from routers.vip import router as vip_router

app.include_router(auth_router)
app.include_router(user_router)
app.include_router(product_router)
app.include_router(exchange_router)
app.include_router(coupon_router)
app.include_router(store_router)
app.include_router(rebate_router)
app.include_router(buyer_router)
app.include_router(demand_router)
app.include_router(order_router)
app.include_router(log_router)
app.include_router(admin_router)
app.include_router(user_feature_router)
app.include_router(splash_ad_router)
app.include_router(vip_router)


@app.get("/")
def root():
    return {
        "code": 0,
        "message": "success",
        "data": {
            "name": "奢侈品比价小程序 API",
            "version": "1.0.0",
            "status": "running"
        }
    }


@app.get("/health")
def health_check():
    return {"code": 0, "message": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
