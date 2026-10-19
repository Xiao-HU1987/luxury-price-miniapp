"""爬虫数据 → 云数据库 一键导入脚本

从本地数据库读取爬虫结果，过滤非包包商品，生成云数据库可直接导入的 JSON 文件。

用法：
    cd server && venv/bin/python3.11 -m scripts.crawl_to_cloud

输出：
    data/cloud_import_products.json    - 商品数据（云数据库 products 集合）
    data/cloud_import_price_stock.json  - 价格库存数据（云数据库 price_stock 集合）
"""
import json
import sys
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
SERVER_DIR = BASE_DIR / "server"
if str(SERVER_DIR) not in sys.path:
    sys.path.insert(0, str(SERVER_DIR))

from database import SessionLocal
from models import SPU, SKU, SKUPrice
from models.lv import LvInventory

OUTPUT_DIR = BASE_DIR / "data"

JPY_TO_CNY_RATE = 0.0462

NON_BAG_KEYWORDS = [
    'sunglass', 'sneaker', 'jacket', 'knit-top', 'blanket',
    'card-holder', 'key-pouch', 'babies', 'wallet-on-chain',
    'scarf', 'belt', 'hat', 'glove', 'jewelry', 'watch',
    'ring', 'necklace', 'earring', 'bracelet',
    'shoe', 'sandal', 'boot', 'shirt', 'pant', 'dress',
    'skirt', 'coat', 'swimwear', 'umbrella', 'phone-case',
    'airpods', 'mask', 'pet', 'baby', 'toy', 'book',
    'pen', 'notebook', 'agenda', 'planner',
]


def is_bag_product(article_no: str, name: str) -> bool:
    text = f"{article_no} {name}".lower()
    return not any(kw in text for kw in NON_BAG_KEYWORDS)


def crawl_to_cloud():
    print("=" * 60)
    print("爬虫数据 → 云数据库 一键导入")
    print("=" * 60)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    db = SessionLocal()
    try:
        # 1. 从本地数据库读取爬虫结果
        print("\n【1/4】读取本地数据库...")
        spus = db.query(SPU).filter(SPU.brand_id == "LV").all()
        print(f"  读取到 {len(spus)} 个 SPU")

        products = []
        price_stocks = []
        skipped = 0

        for spu in spus:
            # 过滤非包包商品
            if not is_bag_product(spu.article_no or "", spu.name or ""):
                skipped += 1
                continue

            # 解析图片
            images = []
            main_image = ""
            if spu.images:
                try:
                    img_list = json.loads(spu.images) if isinstance(spu.images, str) else spu.images
                    if isinstance(img_list, list):
                        images = [u for u in img_list if u][:5]
                except (json.JSONDecodeError, TypeError):
                    pass
            if spu.image:
                main_image = spu.image
            elif images:
                main_image = images[0]

            # 获取价格信息
            jp_price = 0
            sku = db.query(SKU).filter(SKU.spu_id == spu.spu_id).first()
            if sku:
                sku_price = db.query(SKUPrice).filter(
                    SKUPrice.sku_id == sku.sku_id,
                    SKUPrice.country == "JP"
                ).first()
                if sku_price:
                    jp_price = sku_price.price or 0

            cny_price = round(jp_price * JPY_TO_CNY_RATE) if jp_price else 0

            # 获取真实门店库存数据
            store_inventories = []
            jp_in_stock = False
            if sku:
                store_inventories = db.query(LvInventory).filter(
                    LvInventory.sku_id == sku.sku_id
                ).all()
                jp_in_stock = any(inv.in_stock for inv in store_inventories)

            # 计算聚合价格（冗余存储在 products 中，避免云函数关联查询 100 条限制）
            jp_cny_price = cny_price if jp_price > 0 else 0
            kr_cny_price = 0
            cn_official = 0
            
            # 计算全球最优价
            all_prices = []
            if cn_official > 0: all_prices.append((cn_official, 'CN'))
            if jp_cny_price > 0: all_prices.append((jp_cny_price, 'JP'))
            if kr_cny_price > 0: all_prices.append((kr_cny_price, 'KR'))
            all_prices.sort(key=lambda x: x[0])
            best_global_price = all_prices[0][0] if all_prices else 0
            best_country = all_prices[0][1] if all_prices else ''
            country_count = len(all_prices)

            # 构建商品数据（冗余存储所有价格字段）
            product = {
                "productId": spu.spu_id,
                "slug": (spu.article_no or "").lower(),
                "nameCn": spu.name_cn or spu.name or "",
                "nameJp": spu.name or "",
                "nameEn": spu.name_en or "",
                "mainImage": main_image,
                "images": images,
                "cnOfficialPrice": cn_official,
                "hasCnPrice": cn_official > 0,
                "jpPrice": jp_price,
                "jpCnyPrice": jp_cny_price,
                "krPrice": 0,
                "krCnyPrice": kr_cny_price,
                "cnyPrice": cny_price,
                "bestGlobalPrice": best_global_price,
                "bestCountry": best_country,
                "countryCount": country_count,
                "category": "handbag",
                "brandId": spu.brand_id or "LV",
                "brandName": "Louis Vuitton",
                "description": spu.description or "",
                "createTime": spu.created_at.isoformat() if spu.created_at else datetime.now().isoformat() + "Z",
                "updateTime": datetime.now().isoformat() + "Z",
            }
            products.append(product)

            # 构建价格库存：先加官方渠道
            if jp_price > 0:
                ps = {
                    "productId": spu.spu_id,
                    "countryCode": "JP",
                    "localPrice": jp_price,
                    "currency": "JPY",
                    "cnyPrice": cny_price,
                    "stockStatus": "available",
                    "storeInfo": {
                        "city": "",
                        "storeName": "日本官网",
                        "address": "",
                    },
                    "priceUpdateTime": datetime.now().isoformat() + "Z",
                }
                price_stocks.append(ps)

            # 添加真实门店库存（去重）
            seen_stores = set()
            for inv in store_inventories:
                store_name = inv.store_name or ""
                store_city = inv.store_city or ""
                # 使用中文名（如果有翻译）
                display_name = inv.store_name_cn or store_name
                display_city = inv.store_city_cn or store_city
                
                # 去重：同一门店只保留一条
                store_key = f"{display_city}_{display_name}"
                if store_key in seen_stores:
                    continue
                seen_stores.add(store_key)

                stock_status = "available" if inv.in_stock else "out_of_stock"
                ps = {
                    "productId": spu.spu_id,
                    "countryCode": "JP",
                    "localPrice": jp_price,
                    "currency": "JPY",
                    "cnyPrice": cny_price,
                    "stockStatus": stock_status,
                    "storeInfo": {
                        "city": display_city,
                        "storeName": display_name,
                        "address": inv.store_address_cn or inv.store_address or "",
                    },
                    "priceUpdateTime": datetime.now().isoformat() + "Z",
                }
                price_stocks.append(ps)

        print(f"\n【2/4】过滤非包包商品...")
        print(f"  跳过: {skipped} 个非包包商品")
        print(f"  保留: {len(products)} 个包包商品")

        # 2. 统计
        has_images = sum(1 for p in products if p["mainImage"])
        has_prices = sum(1 for ps in price_stocks if ps["localPrice"] > 0)
        print(f"\n【3/4】数据统计...")
        print(f"  有图片商品: {has_images} ({has_images/max(len(products),1)*100:.0f}%)")
        print(f"  有价格库存: {has_prices} ({has_prices/max(len(price_stocks),1)*100:.0f}%)")

        # 3. 写入 JSON 文件（云数据库导入要求 JSON Lines 格式：每行一条 JSON）
        print(f"\n【4/4】生成导入文件...")
        products_file = OUTPUT_DIR / "cloud_import_products.json"
        ps_file = OUTPUT_DIR / "cloud_import_price_stock.json"

        with open(products_file, "w", encoding="utf-8") as f:
            for p in products:
                f.write(json.dumps(p, ensure_ascii=False))
                f.write("\n")
        print(f"  商品数据: {products_file} ({len(products)} 个)")

        with open(ps_file, "w", encoding="utf-8") as f:
            for ps in price_stocks:
                f.write(json.dumps(ps, ensure_ascii=False))
                f.write("\n")
        print(f"  价格库存: {ps_file} ({len(price_stocks)} 条)")

        # 生成导入摘要
        summary = {
            "totalProducts": len(products),
            "totalPriceStocks": len(price_stocks),
            "hasImages": has_images,
            "hasPrices": has_prices,
            "skippedNonBag": skipped,
            "generatedAt": datetime.now().isoformat(),
            "importInstructions": [
                "方式1（推荐）: 在小程序「我的→数据管理」点击「一键导入数据」",
                "方式2: 使用云开发控制台导入 cloud_import_products.json 和 cloud_import_price_stock.json",
                "方式3: 运行 node scripts/import_to_cloud.js（需配置 cloud_config.json）",
            ],
        }
        summary_file = OUTPUT_DIR / "cloud_import_summary.json"
        with open(summary_file, "w", encoding="utf-8") as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)

        print(f"\n{'='*60}")
        print("✅ 导入文件生成完成！")
        print(f"{'='*60}")
        print(f"\n下一步：")
        print(f"  1. 在微信开发者工具中打开云开发控制台")
        print(f"  2. 或在小程序「我的→数据管理」点击「一键导入」")
        print(f"  3. 或运行: node scripts/import_to_cloud.js")
        print()

        return 0

    except Exception as e:
        print(f"\n❌ 导入失败: {e}")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(crawl_to_cloud())