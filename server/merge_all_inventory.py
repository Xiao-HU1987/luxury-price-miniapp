"""
合并 JP/KR 库存数据到 aligned 整合表
- 生成 merged_KR.jsonl（类似 merged_JP.jsonl）
- 更新 products_unified.jsonl 的库存字段
- 更新 price_comparison.jsonl
- 补充 JP 缺失价格
"""
import json
import logging
from pathlib import Path
from collections import defaultdict

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("merge")

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data" / "lv"
ALIGNED_DIR = DATA_DIR / "aligned"


def load_products(country: str) -> dict:
    """加载商品信息，返回 {sku_id: product_info}"""
    products = {}
    f = DATA_DIR / country / f"products_{country}.jsonl"
    if not f.exists():
        f = DATA_DIR / country / f"products_{country}_clean.jsonl"
    if not f.exists():
        logger.warning(f"商品文件不存在: {f}")
        return products

    with open(f) as fh:
        for line in fh:
            r = json.loads(line.strip())
            sid = r.get("sku_id", r.get("sku", ""))
            if sid:
                products[sid] = r
    logger.info(f"加载 {country} 商品: {len(products)} 个")
    return products


def load_inventory_api(country: str) -> dict:
    """加载 API 库存数据，返回 {sku_id: [records]}"""
    inv = defaultdict(list)
    f = DATA_DIR / country / f"inventories_{country}_api.jsonl"
    if not f.exists():
        return inv

    with open(f) as fh:
        for line in fh:
            r = json.loads(line.strip())
            sid = r.get("sku_id", "")
            if sid:
                inv[sid].append(r)
    logger.info(f"加载 {country} API 库存: {len(inv)} SKU, {sum(len(v) for v in inv.values())} 条")
    return inv


def load_inventory_stores(country: str) -> dict:
    """加载旧爬虫库存数据，返回 {sku_id: [records]}"""
    inv = defaultdict(list)
    f = DATA_DIR / country / f"inventories_{country}_stores.jsonl"
    if not f.exists():
        return inv

    with open(f) as fh:
        for line in fh:
            r = json.loads(line.strip())
            sid = r.get("sku_id", "")
            if sid:
                inv[sid].append(r)
    logger.info(f"加载 {country} 旧爬虫库存: {len(inv)} SKU, {sum(len(v) for v in inv.values())} 条")
    return inv


def merge_country(country: str, products: dict, api_inv: dict, stores_inv: dict) -> list:
    """合并商品信息和库存，返回 merged list"""
    results = []

    for sid, product in products.items():
        # 合并库存记录
        all_stores = api_inv.get(sid, []) + stores_inv.get(sid, [])

        # 统计
        stores_in_stock = sum(1 for s in all_stores if s.get("in_stock") is True)
        stores_out_of_stock = sum(1 for s in all_stores if s.get("in_stock") is False)
        stores_unknown = len(all_stores) - stores_in_stock - stores_out_of_stock

        # 渠道判定
        if not all_stores:
            channel_status = "仅官网有售"
        elif stores_in_stock > 0:
            channel_status = "门店有售且有库存"
        else:
            channel_status = "门店有售无库存"

        merged = {
            "sku_id": sid,
            "country": country,
            "name_local": product.get("name", product.get("name_local", "")),
            "price": product.get("price", product.get("price_jp", product.get("price_kr", 0))),
            "currency": "JPY" if country == "JP" else "KRW",
            "sellable": product.get("sellable", True),
            "source_url": product.get("url", ""),
            "images": product.get("images", product.get("image", [])),
            "channel_status": channel_status,
            "total_stores": len(all_stores),
            "stores_in_stock": stores_in_stock,
            "stores_out_of_stock": stores_out_of_stock,
            "stores_unknown": stores_unknown,
            "stores": [
                {
                    "store_name": s.get("store_name", ""),
                    "store_address": s.get("store_address", ""),
                    "store_city": s.get("store_city", ""),
                    "store_telephone": s.get("store_telephone", ""),
                    "in_stock": s.get("in_stock"),
                    "stock_status": s.get("stock_status", ""),
                }
                for s in all_stores
            ],
        }
        results.append(merged)

    return results


def update_aligned(merged_jp: dict, merged_kr: dict):
    """更新 products_unified.jsonl 和 price_comparison.jsonl"""
    # 加载现有 unified 数据
    unified = {}
    if (ALIGNED_DIR / "products_unified.jsonl").exists():
        with open(ALIGNED_DIR / "products_unified.jsonl") as f:
            for line in f:
                r = json.loads(line.strip())
                unified[r["sku_id"]] = r

    updated = 0
    for sid, u in unified.items():
        modified = False

        # 更新 JP 库存
        if sid in merged_jp:
            jp = merged_jp[sid]
            u["source_jp"] = True
            u["source_url_jp"] = jp.get("source_url", "")
            u["name_jp"] = jp.get("name_local", "")
            u["price_jp"] = jp.get("price", 0)
            u["has_store_channel"] = jp.get("channel_status") != "仅官网有售"
            u["has_store_stock"] = jp.get("stores_in_stock", 0) > 0
            u["online_only"] = jp.get("channel_status") == "仅官网有售"
            u["store_names"] = [s["store_name"] for s in jp.get("stores", [])]
            u["store_addresses"] = [s["store_address"] for s in jp.get("stores", [])]
            u["store_cities"] = list(set(s["store_city"] for s in jp.get("stores", []) if s["store_city"]))
            u["store_count"] = jp.get("total_stores", 0)
            u["store_in_stock"] = jp.get("stores_in_stock", 0)
            u["store_out_of_stock"] = jp.get("stores_out_of_stock", 0)
            u["store_stock_count"] = jp.get("stores_in_stock", 0) + jp.get("stores_out_of_stock", 0)
            modified = True

        # 更新 KR 库存
        if sid in merged_kr:
            kr = merged_kr[sid]
            u["source_kr"] = True
            u["source_url_kr"] = kr.get("source_url", "")
            u["name_kr"] = kr.get("name_local", "")
            u["price_kr"] = kr.get("price", 0)
            if not u.get("has_store_channel"):
                u["has_store_channel"] = kr.get("channel_status") != "仅官网有售"
            if not u.get("has_store_stock"):
                u["has_store_stock"] = kr.get("stores_in_stock", 0) > 0
            if not u.get("online_only"):
                u["online_only"] = kr.get("channel_status") == "仅官网有售"
            # KR store data
            if kr.get("stores"):
                u["store_names"] = u.get("store_names", []) + [s["store_name"] for s in kr.get("stores", [])]
                u["store_addresses"] = u.get("store_addresses", []) + [s["store_address"] for s in kr.get("stores", [])]
                u["store_cities"] = list(set(u.get("store_cities", []) + [s["store_city"] for s in kr.get("stores", []) if s["store_city"]]))
            if not u.get("store_count"):
                u["store_count"] = kr.get("total_stores", 0)
            modified = True

        if modified:
            updated += 1

    # 保存
    with open(ALIGNED_DIR / "products_unified.jsonl", "w") as f:
        for u in unified.values():
            f.write(json.dumps(u, ensure_ascii=False) + "\n")

    logger.info(f"更新 products_unified: {updated}/{len(unified)} 条")
    return unified


def fix_jp_prices(unified: dict):
    """补充 JP 5 个 SKU 缺失的价格，从其他国价格推算"""
    # 使用实时汇率: 1 JPY ≈ 0.048 CNY, 1 KRW ≈ 0.0052 CNY
    # 从 CN 价格反推 JPY: JPY = CNY / 0.048
    # 从 KR 价格反推 JPY: JPY = KRW * 0.0052 / 0.048

    fixed = []
    for sid, u in unified.items():
        price_jp = u.get("price_jp", 0) or 0
        if price_jp == 0:
            inferred = None
            price_cny = u.get("price_cny", 0) or 0
            price_kr = u.get("price_kr", 0) or 0
            if price_cny > 0:
                inferred = round(price_cny / 0.048)
                logger.info(f"{sid}: 从 CN ¥{price_cny} 推算 JPY ¥{inferred}")
            elif price_kr > 0:
                inferred = round(u["price_kr"] * 0.0052 / 0.048)
                logger.info(f"{sid}: 从 KR ₩{u['price_kr']} 推算 JPY ¥{inferred}")

            if inferred:
                u["price_jp"] = inferred
                fixed.append(sid)

    if fixed:
        # 保存
        with open(ALIGNED_DIR / "products_unified.jsonl", "w") as f:
            for u in unified.values():
                f.write(json.dumps(u, ensure_ascii=False) + "\n")
        logger.info(f"补充 JP 价格: {len(fixed)} SKU: {fixed}")


def update_price_comparison(unified: dict):
    """更新价格对比表"""
    # 汇率
    JPY_TO_CNY = 0.048
    KRW_TO_CNY = 0.0052

    comparisons = []
    for sid, u in unified.items():
        price_cn = u.get("price_cny", 0) or 0
        price_jp = u.get("price_jp", 0) or 0
        price_kr = u.get("price_kr", 0) or 0

        # 换算为人民币
        jp_cny = round(price_jp * JPY_TO_CNY) if price_jp > 0 else None
        kr_cny = round(price_kr * KRW_TO_CNY) if price_kr > 0 else None

        # 三国都有价格才对比
        if not (price_cn > 0 and jp_cny and kr_cny):
            continue

        prices = [
            ("CN", price_cn),
            ("JP", jp_cny),
            ("KR", kr_cny),
        ]
        prices.sort(key=lambda x: x[1])
        cheapest_site, cheapest_price = prices[0]
        most_expensive_site, most_expensive_price = prices[-1]

        price_diff_pct = round((most_expensive_price - cheapest_price) / cheapest_price * 100, 1) if cheapest_price > 0 else 0

        comp = {
            "sku_id": sid,
            "name_cn": u.get("name_cn", ""),
            "name_en": u.get("name_en", ""),
            "price_cny": price_cn,
            "price_cn": price_cn,
            "price_jp": price_jp,
            "price_kr": price_kr,
            "price_cn_cny": price_cn,
            "price_jp_cny": jp_cny,
            "price_kr_cny": kr_cny,
            "cheapest_site": cheapest_site,
            "cheapest_price_cny": cheapest_price,
            "most_expensive_site": most_expensive_site,
            "most_expensive_price_cny": most_expensive_price,
            "price_diff_pct": price_diff_pct,
        }
        comparisons.append(comp)

    # 保存
    with open(ALIGNED_DIR / "price_comparison.jsonl", "w") as f:
        for c in comparisons:
            f.write(json.dumps(c, ensure_ascii=False) + "\n")

    logger.info(f"更新 price_comparison: {len(comparisons)} 条")


def main():
    logger.info("=" * 60)
    logger.info("开始合并库存数据")
    logger.info("=" * 60)

    # 1. 加载数据
    products_jp = load_products("JP")
    products_kr = load_products("KR")

    api_jp = load_inventory_api("JP")
    api_kr = load_inventory_api("KR")

    stores_jp = load_inventory_stores("JP")
    stores_kr = load_inventory_stores("KR")

    # 2. 合并各国数据
    logger.info("\n--- 合并 JP ---")
    merged_jp = merge_country("JP", products_jp, api_jp, stores_jp)

    with open(DATA_DIR / "JP" / "merged_JP.jsonl", "w") as f:
        for r in merged_jp:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    # 统计
    jp_in_stock = sum(1 for r in merged_jp if r["stores_in_stock"] > 0)
    jp_no_stock = sum(1 for r in merged_jp if r["stores_in_stock"] == 0 and r["total_stores"] > 0)
    jp_no_store = sum(1 for r in merged_jp if r["total_stores"] == 0)
    logger.info(f"JP: {len(merged_jp)} SKU, 有库存 {jp_in_stock}, 无库存 {jp_no_stock}, 无门店 {jp_no_store}")

    logger.info("\n--- 合并 KR ---")
    merged_kr = merge_country("KR", products_kr, api_kr, stores_kr)

    with open(DATA_DIR / "KR" / "merged_KR.jsonl", "w") as f:
        for r in merged_kr:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    kr_in_stock = sum(1 for r in merged_kr if r["stores_in_stock"] > 0)
    kr_no_stock = sum(1 for r in merged_kr if r["stores_in_stock"] == 0 and r["total_stores"] > 0)
    kr_no_store = sum(1 for r in merged_kr if r["total_stores"] == 0)
    logger.info(f"KR: {len(merged_kr)} SKU, 有库存 {kr_in_stock}, 无库存 {kr_no_stock}, 无门店 {kr_no_store}")

    # 3. 转为 {sku_id: merged} 便于后续更新
    merged_jp_map = {r["sku_id"]: r for r in merged_jp}
    merged_kr_map = {r["sku_id"]: r for r in merged_kr}

    # 4. 更新 aligned 表
    logger.info("\n--- 更新 products_unified ---")
    unified = update_aligned(merged_jp_map, merged_kr_map)

    # 5. 补充 JP 缺失价格
    logger.info("\n--- 补充 JP 缺失价格 ---")
    fix_jp_prices(unified)

    # 6. 更新价格对比
    logger.info("\n--- 更新 price_comparison ---")
    update_price_comparison(unified)

    logger.info("\n" + "=" * 60)
    logger.info("合并完成！")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()