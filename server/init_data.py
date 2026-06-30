import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from database import SessionLocal, engine, Base
from models import (
    Brand, Category, SPU, SKU, SKUPrice,
    Store, Coupon, Buyer, Demand, ExchangeRate, Rebate
)

Base.metadata.create_all(bind=engine)

BRANDS_DATA = [
    {"brand_id": "b001", "name": "Louis Vuitton", "name_cn": "路易威登", "logo": "LV", "category": "箱包"},
    {"brand_id": "b002", "name": "Gucci", "name_cn": "古驰", "logo": "G", "category": "箱包服饰"},
    {"brand_id": "b003", "name": "Hermès", "name_cn": "爱马仕", "logo": "H", "category": "箱包"},
    {"brand_id": "b004", "name": "Chanel", "name_cn": "香奈儿", "logo": "C", "category": "箱包服饰"},
    {"brand_id": "b005", "name": "Dior", "name_cn": "迪奥", "logo": "D", "category": "服饰箱包"},
    {"brand_id": "b006", "name": "Rolex", "name_cn": "劳力士", "logo": "R", "category": "腕表"},
    {"brand_id": "b007", "name": "Cartier", "name_cn": "卡地亚", "logo": "Ca", "category": "珠宝腕表"},
    {"brand_id": "b008", "name": "Prada", "name_cn": "普拉达", "logo": "P", "category": "箱包"},
]

CATEGORIES_DATA = [
    {"category_id": "c001", "name": "箱包", "icon": "👜"},
    {"category_id": "c002", "name": "腕表", "icon": "⌚"},
    {"category_id": "c003", "name": "珠宝", "icon": "💎"},
    {"category_id": "c004", "name": "服饰", "icon": "👗"},
    {"category_id": "c005", "name": "鞋履", "icon": "👠"},
    {"category_id": "c006", "name": "配饰", "icon": "🕶️"},
]

PRODUCTS_DATA = [
    {
        "spu_id": "spu001",
        "brand_id": "b001",
        "brand_name": "Louis Vuitton",
        "name": "CARRYALL 小号手袋",
        "name_en": "CARRYALL PM",
        "article_no": "M46203",
        "category_id": "c001",
        "image": "",
        "description": "经典CARRYALL小号手袋，Monogram帆布材质。",
        "skus": [
            {
                "sku_id": "sku001-001",
                "name": "Monogram 老花",
                "color": "老花",
                "size": "MM",
                "prices": {
                    "CN": {"price": 23000, "currency": "CNY", "stock": 25, "store": "上海恒隆广场店"},
                    "JP": {"price": 395000, "currency": "JPY", "stock": 20, "store": "东京银座店"},
                    "FR": {"price": 2200, "currency": "EUR", "stock": 42, "store": "巴黎香榭丽舍店"},
                    "US": {"price": 2600, "currency": "USD", "stock": 38, "store": "纽约第五大道店"},
                    "HK": {"price": 24500, "currency": "HKD", "stock": 30, "store": "香港海港城店"}
                }
            }
        ]
    },
    {
        "spu_id": "spu002",
        "brand_id": "b001",
        "brand_name": "Louis Vuitton",
        "name": "法棍 DIANE 手袋",
        "name_en": "DIANE",
        "article_no": "M45985",
        "category_id": "c001",
        "image": "",
        "description": "法棍包，经典复古设计。",
        "skus": [
            {
                "sku_id": "sku002-001",
                "name": "Etoupe 大象灰",
                "color": "大象灰",
                "size": "30",
                "prices": {
                    "CN": {"price": 19600, "currency": "CNY", "stock": 8, "store": "上海恒隆广场店"},
                    "JP": {"price": 337000, "currency": "JPY", "stock": 15, "store": "东京银座店"},
                    "FR": {"price": 1880, "currency": "EUR", "stock": 22, "store": "巴黎福宝总店"},
                    "US": {"price": 2250, "currency": "USD", "stock": 18, "store": "纽约麦迪逊店"}
                }
            }
        ]
    },
    {
        "spu_id": "spu003",
        "brand_id": "b001",
        "brand_name": "Louis Vuitton",
        "name": "allinbb 手袋",
        "name_en": "ALL IN BB",
        "article_no": "M12925",
        "category_id": "c001",
        "image": "",
        "description": "ALL IN BB手袋，精致小巧。",
        "skus": [
            {
                "sku_id": "sku003-001",
                "name": "黑色",
                "color": "黑色",
                "size": "小号",
                "prices": {
                    "CN": {"price": 19400, "currency": "CNY", "stock": 12, "store": "上海恒隆广场店"},
                    "JP": {"price": 334000, "currency": "JPY", "stock": 20, "store": "东京银座店"},
                    "IT": {"price": 1850, "currency": "EUR", "stock": 28, "store": "米兰蒙特拿破仑店"},
                    "US": {"price": 2100, "currency": "USD", "stock": 35, "store": "纽约第五大道店"}
                }
            }
        ]
    },
    {
        "spu_id": "spu004",
        "brand_id": "b001",
        "brand_name": "Louis Vuitton",
        "name": "法棍 NANO DIANE 手袋",
        "name_en": "NANO DIANE",
        "article_no": "M83298",
        "category_id": "c001",
        "image": "",
        "description": "NANO DIANE迷你法棍包。",
        "skus": [
            {
                "sku_id": "sku004-001",
                "name": "蓝面钢款",
                "color": "蓝色表盘",
                "size": "41mm",
                "prices": {
                    "CN": {"price": 15300, "currency": "CNY", "stock": 10, "store": "上海恒隆广场店"},
                    "JP": {"price": 263000, "currency": "JPY", "stock": 8, "store": "东京银座店"},
                    "US": {"price": 1850, "currency": "USD", "stock": 12, "store": "纽约第五大道店"}
                }
            }
        ]
    },
    {
        "spu_id": "spu005",
        "brand_id": "b007",
        "brand_name": "Cartier",
        "name": "LOVE系列戒指",
        "name_en": "LOVE Ring",
        "article_no": "B4085000",
        "category_id": "c003",
        "image": "",
        "description": "卡地亚LOVE系列18K黄金戒指，经典螺丝设计。",
        "skus": [
            {
                "sku_id": "sku005-001",
                "name": "黄金款",
                "color": "黄金",
                "size": "50",
                "prices": {
                    "CN": {"price": 17800, "currency": "CNY", "stock": 15, "store": "上海恒隆广场店"},
                    "FR": {"price": 1950, "currency": "EUR", "stock": 30, "store": "巴黎旺多姆店"},
                    "US": {"price": 2310, "currency": "USD", "stock": 40, "store": "纽约第五大道店"},
                    "JP": {"price": 310000, "currency": "JPY", "stock": 25, "store": "东京银座店"},
                    "HK": {"price": 18500, "currency": "HKD", "stock": 20, "store": "香港半岛酒店店"}
                }
            },
            {
                "sku_id": "sku005-002",
                "name": "玫瑰金款",
                "color": "玫瑰金",
                "size": "50",
                "prices": {
                    "CN": {"price": 19200, "currency": "CNY", "stock": 12, "store": "上海恒隆广场店"},
                    "FR": {"price": 2100, "currency": "EUR", "stock": 28, "store": "巴黎旺多姆店"},
                    "US": {"price": 2490, "currency": "USD", "stock": 35, "store": "纽约第五大道店"}
                }
            }
        ]
    },
    {
        "spu_id": "spu006",
        "brand_id": "b004",
        "brand_name": "Chanel",
        "name": "Classic Flap 中号",
        "name_en": "Classic Flap Medium",
        "article_no": "A01112",
        "category_id": "c001",
        "image": "",
        "description": "香奈儿经典口盖包，小羊皮，金扣，中号。",
        "skus": [
            {
                "sku_id": "sku006-001",
                "name": "黑色金扣",
                "color": "黑色",
                "size": "中号",
                "prices": {
                    "CN": {"price": 62700, "currency": "CNY", "stock": 0, "store": "上海恒隆广场店"},
                    "FR": {"price": 7100, "currency": "EUR", "stock": 3, "store": "巴黎康朋街31号"},
                    "US": {"price": 8800, "currency": "USD", "stock": 0, "store": "纽约麦迪逊店"},
                    "JP": {"price": 1230000, "currency": "JPY", "stock": 2, "store": "东京银座店"},
                    "HK": {"price": 66000, "currency": "HKD", "stock": 0, "store": "香港置地广场店"}
                }
            }
        ]
    },
    {
        "spu_id": "spu007",
        "brand_id": "b005",
        "brand_name": "Dior",
        "name": "Lady Dior 戴妃包",
        "name_en": "Lady Dior",
        "article_no": "M0565",
        "category_id": "c001",
        "image": "",
        "description": "Lady Dior手袋，经典藤格纹，金属字母吊饰。",
        "skus": [
            {
                "sku_id": "sku007-001",
                "name": "黑色小羊皮",
                "color": "黑色",
                "size": "中号",
                "prices": {
                    "CN": {"price": 43000, "currency": "CNY", "stock": 6, "store": "上海恒隆广场店"},
                    "FR": {"price": 4500, "currency": "EUR", "stock": 15, "store": "巴黎蒙田大道店"},
                    "US": {"price": 5600, "currency": "USD", "stock": 12, "store": "纽约第五大道店"},
                    "JP": {"price": 780000, "currency": "JPY", "stock": 8, "store": "东京银座店"},
                    "HK": {"price": 45000, "currency": "HKD", "stock": 10, "store": "香港海港城店"}
                }
            }
        ]
    },
    {
        "spu_id": "spu008",
        "brand_id": "b008",
        "brand_name": "Prada",
        "name": "Re-Edition 2005",
        "name_en": "Re-Edition 2005",
        "article_no": "1BH204",
        "category_id": "c001",
        "image": "",
        "description": "Prada Re-Edition 2005 再生尼龙单肩包。",
        "skus": [
            {
                "sku_id": "sku008-001",
                "name": "黑色",
                "color": "黑色",
                "size": "均码",
                "prices": {
                    "CN": {"price": 11800, "currency": "CNY", "stock": 20, "store": "上海恒隆广场店"},
                    "IT": {"price": 1200, "currency": "EUR", "stock": 45, "store": "米兰蒙特拿破仑店"},
                    "US": {"price": 1450, "currency": "USD", "stock": 50, "store": "纽约第五大道店"},
                    "KR": {"price": 1850000, "currency": "KRW", "stock": 30, "store": "首尔现代百货店"}
                }
            }
        ]
    }
]

STORES_DATA = [
    {"store_id": "s001", "name": "上海恒隆广场", "type": "mall", "country": "CN", "city": "上海", "address": "静安区南京西路1266号", "rating": 4.8, "image": ""},
    {"store_id": "s002", "name": "北京SKP", "type": "mall", "country": "CN", "city": "北京", "address": "朝阳区建国路87号", "rating": 4.9, "image": ""},
    {"store_id": "s003", "name": "巴黎香榭丽舍大街", "type": "street", "country": "FR", "city": "巴黎", "address": "Avenue des Champs-Élysées", "rating": 4.7, "image": ""},
    {"store_id": "s004", "name": "纽约第五大道", "type": "street", "country": "US", "city": "纽约", "address": "Fifth Avenue, Manhattan", "rating": 4.8, "image": ""},
    {"store_id": "s005", "name": "东京银座", "type": "street", "country": "JP", "city": "东京", "address": "中央区銀座", "rating": 4.9, "image": ""},
    {"store_id": "s006", "name": "香港海港城", "type": "mall", "country": "HK", "city": "香港", "address": "九龙尖沙咀广东道3号", "rating": 4.7, "image": ""},
    {"store_id": "s007", "name": "首尔乐天免税店", "type": "dutyfree", "country": "KR", "city": "首尔", "address": "中区乙支路30街83", "rating": 4.6, "image": ""},
    {"store_id": "s008", "name": "米兰蒙特拿破仑大街", "type": "street", "country": "IT", "city": "米兰", "address": "Via Montenapoleone", "rating": 4.8, "image": ""},
    {"store_id": "s009", "name": "苏黎世班霍夫大街", "type": "street", "country": "CH", "city": "苏黎世", "address": "Bahnhofstrasse", "rating": 4.7, "image": ""},
    {"store_id": "s010", "name": "新加坡乌节路", "type": "street", "country": "SG", "city": "新加坡", "address": "Orchard Road", "rating": 4.6, "image": ""},
]

COUPONS_DATA = [
    {"coupon_id": "cp001", "title": "新用户首单立减200元", "type": "discount", "discount": 200, "threshold": 2000, "country": "CN", "store_id": "s001", "store_name": "上海恒隆广场", "expire_date": "2026-12-31", "status": "available"},
    {"coupon_id": "cp002", "title": "满1000欧享9折", "type": "percent", "discount": 10, "threshold": 1000, "country": "FR", "store_id": "s003", "store_name": "巴黎香榭丽舍", "expire_date": "2026-08-31", "status": "available"},
    {"coupon_id": "cp003", "title": "腕表品类95折", "type": "percent", "discount": 5, "threshold": 0, "country": "JP", "store_id": "s005", "store_name": "东京银座", "expire_date": "2026-07-31", "status": "available"},
    {"coupon_id": "cp004", "title": "免税店额外返现5%", "type": "cashback", "discount": 5, "threshold": 0, "country": "KR", "store_id": "s007", "store_name": "首尔乐天免税店", "expire_date": "2026-09-30", "status": "available"},
    {"coupon_id": "cp005", "title": "会员专享满5000减500", "type": "discount", "discount": 500, "threshold": 5000, "country": "HK", "store_id": "s006", "store_name": "香港海港城", "expire_date": "2026-10-31", "status": "available"},
    {"coupon_id": "cp006", "title": "夏季特惠 全场85折", "type": "percent", "discount": 15, "threshold": 0, "country": "IT", "store_id": "s008", "store_name": "米兰蒙特拿破仑", "expire_date": "2026-07-15", "status": "available"},
]

BUYERS_DATA = [
    {"buyer_id": "by001", "name": "巴黎代购Lily", "avatar": "", "country": "FR", "city": "巴黎", "rating": 4.9, "orders": 1286, "fee_rate": 8, "delivery_days": 15, "intro": "常驻巴黎8年，专注一线奢侈品代购，支持专柜验货。"},
    {"buyer_id": "by002", "name": "东京买手Kenji", "avatar": "", "country": "JP", "city": "东京", "rating": 4.8, "orders": 956, "fee_rate": 10, "delivery_days": 10, "intro": "日本东京资深买手，精通腕表珠宝，速度快价格优。"},
    {"buyer_id": "by003", "name": "首尔欧尼小铺", "avatar": "", "country": "KR", "city": "首尔", "rating": 4.7, "orders": 2034, "fee_rate": 6, "delivery_days": 7, "intro": "韩国免税店代购，价格全网最低，量大优惠更多。"},
    {"buyer_id": "by004", "name": "米兰时尚买手", "avatar": "", "country": "IT", "city": "米兰", "rating": 4.9, "orders": 678, "fee_rate": 9, "delivery_days": 18, "intro": "意大利时尚之都买手，品牌合作直供，正品保障。"},
    {"buyer_id": "by005", "name": "香港代购小王", "avatar": "", "country": "HK", "city": "香港", "rating": 4.6, "orders": 3200, "fee_rate": 5, "delivery_days": 5, "intro": "香港本地代购，当天发货，最快次日达。"},
    {"buyer_id": "by006", "name": "纽约奢侈品顾问", "avatar": "", "country": "US", "city": "纽约", "rating": 4.8, "orders": 890, "fee_rate": 12, "delivery_days": 20, "intro": "纽约资深奢侈品顾问，稀有款定制，专业靠谱。"},
]

DEMANDS_DATA = [
    {
        "demand_id": "d001",
        "user_id": "U001",
        "product_name": "Hermès Birkin 30 大象灰",
        "brand_id": "b003",
        "country": "FR",
        "deadline": "2026-07-15",
        "budget": 160000,
        "budget_currency": "CNY",
        "quantity": 1,
        "status": "bidding",
        "bids": 3,
        "matched_buyer_id": "",
        "description": "要银扣，全新全套，支持鉴定。"
    },
    {
        "demand_id": "d002",
        "user_id": "U002",
        "product_name": "Chanel Classic Flap 中号黑金牛",
        "brand_id": "b004",
        "country": "JP",
        "deadline": "2026-07-05",
        "budget": 70000,
        "budget_currency": "CNY",
        "quantity": 1,
        "status": "bidding",
        "bids": 5,
        "matched_buyer_id": "",
        "description": "全新未使用，全套包装。"
    },
    {
        "demand_id": "d003",
        "user_id": "U003",
        "product_name": "Rolex Datejust 41 蓝面",
        "brand_id": "b006",
        "country": "CH",
        "deadline": "2026-08-01",
        "budget": 85000,
        "budget_currency": "CNY",
        "quantity": 1,
        "status": "matched",
        "bids": 8,
        "matched_buyer_id": "by002",
        "description": "全新全套，全球联保。"
    }
]

EXCHANGE_RATES_DATA = {
    "base": "CNY",
    "rates": {
        "CNY": 1,
        "USD": 0.138,
        "EUR": 0.128,
        "GBP": 0.109,
        "JPY": 21.58,
        "KRW": 192.5,
        "HKD": 1.075,
        "SGD": 0.186,
        "AUD": 0.215,
        "CHF": 0.123,
        "CAD": 0.192,
        "THB": 4.95
    }
}

REBATES_DATA = [
    {"rebate_id": "r001", "title": "日本近铁百货返点3.1%", "brand_id": "", "brand_name": "", "store_id": "", "store_name": "近铁百货", "country": "JP", "rate": 3.1, "is_vip_only": False, "status": "available", "start_date": "2026-06-10", "end_date": "2026-06-28", "description": "免税+当天返3.1%(LV卡地亚等可用)"},
    {"rebate_id": "r002", "title": "Bic Camera 最大17%折扣", "brand_id": "", "brand_name": "", "store_id": "", "store_name": "Bic Camera", "country": "JP", "rate": 17, "is_vip_only": False, "status": "available", "start_date": "2026-06-01", "end_date": "2026-07-31", "description": "最大17%折扣+免税"},
]


def init_brands(db):
    if db.query(Brand).count() > 0:
        print("品牌数据已存在，跳过")
        return
    for data in BRANDS_DATA:
        db.add(Brand(**data))
    db.commit()
    print(f"✅ 品牌数据初始化完成，共 {len(BRANDS_DATA)} 条")


def init_categories(db):
    if db.query(Category).count() > 0:
        print("品类数据已存在，跳过")
        return
    for data in CATEGORIES_DATA:
        db.add(Category(**data))
    db.commit()
    print(f"✅ 品类数据初始化完成，共 {len(CATEGORIES_DATA)} 条")


def init_products(db):
    if db.query(SPU).count() > 0:
        print("商品数据已存在，跳过")
        return
    for spu_data in PRODUCTS_DATA:
        skus_data = spu_data.pop("skus", [])
        spu = SPU(**spu_data)
        db.add(spu)
        db.flush()
        
        for sku_data in skus_data:
            prices_data = sku_data.pop("prices", {})
            sku_data["spu_id"] = spu_data["spu_id"]
            sku = SKU(**sku_data)
            db.add(sku)
            db.flush()
            
            for country, price_data in prices_data.items():
                price_data["sku_id"] = sku_data["sku_id"]
                price_data["country"] = country
                db.add(SKUPrice(**price_data))
    
    db.commit()
    print(f"✅ 商品数据初始化完成，共 {len(PRODUCTS_DATA)} 个SPU")


def init_stores(db):
    if db.query(Store).count() > 0:
        print("门店数据已存在，跳过")
        return
    for data in STORES_DATA:
        db.add(Store(**data))
    db.commit()
    print(f"✅ 门店数据初始化完成，共 {len(STORES_DATA)} 条")


def init_coupons(db):
    if db.query(Coupon).count() > 0:
        print("优惠券数据已存在，跳过")
        return
    for data in COUPONS_DATA:
        db.add(Coupon(**data))
    db.commit()
    print(f"✅ 优惠券数据初始化完成，共 {len(COUPONS_DATA)} 条")


def init_buyers(db):
    if db.query(Buyer).count() > 0:
        print("买手数据已存在，跳过")
        return
    for data in BUYERS_DATA:
        db.add(Buyer(**data))
    db.commit()
    print(f"✅ 买手数据初始化完成，共 {len(BUYERS_DATA)} 条")


def init_demands(db):
    if db.query(Demand).count() > 0:
        print("需求数据已存在，跳过")
        return
    for data in DEMANDS_DATA:
        db.add(Demand(**data))
    db.commit()
    print(f"✅ 需求数据初始化完成，共 {len(DEMANDS_DATA)} 条")


def init_exchange_rates(db):
    if db.query(ExchangeRate).count() > 0:
        print("汇率数据已存在，跳过")
        return
    db.add(ExchangeRate(**EXCHANGE_RATES_DATA))
    db.commit()
    print("✅ 汇率数据初始化完成")


def init_rebates(db):
    if db.query(Rebate).count() > 0:
        print("返点数据已存在，跳过")
        return
    for data in REBATES_DATA:
        db.add(Rebate(**data))
    db.commit()
    print(f"✅ 返点数据初始化完成，共 {len(REBATES_DATA)} 条")


def main():
    db = SessionLocal()
    try:
        print("=" * 50)
        print("开始初始化数据库...")
        print("=" * 50)
        
        init_brands(db)
        init_categories(db)
        init_products(db)
        init_stores(db)
        init_coupons(db)
        init_buyers(db)
        init_demands(db)
        init_exchange_rates(db)
        init_rebates(db)
        
        print("=" * 50)
        print("🎉 数据库初始化完成！")
        print("=" * 50)
    except Exception as e:
        print(f"❌ 初始化失败: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
