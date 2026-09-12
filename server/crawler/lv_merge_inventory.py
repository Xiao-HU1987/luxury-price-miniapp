"""
LV JP 库存数据与商品信息关联合并
输入：products_JP.jsonl + inventories_JP_api.jsonl + inventories_JP_stores.jsonl
输出：merged_JP.jsonl
"""
import json
import logging
from collections import defaultdict
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("lv_merge")

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / "data" / "lv" / "JP"

PRODUCTS_FILE = DATA_DIR / "products_JP.jsonl"
API_INV_FILE = DATA_DIR / "inventories_JP_api.jsonl"
STORES_INV_FILE = DATA_DIR / "inventories_JP_stores.jsonl"
OUTPUT_FILE = DATA_DIR / "merged_JP.jsonl"


def load_products():
    """加载商品信息，以 sku_id 为 key"""
    products = {}
    with open(PRODUCTS_FILE, "r") as f:
        for line in f:
            r = json.loads(line.strip())
            sid = r.get("sku_id", r.get("sku", ""))
            if sid:
                products[sid] = r
    logger.info(f"加载商品: {len(products)} 个")
    return products


def load_inventory(filepath, source_label):
    """加载库存记录，按 sku_id 分组"""
    inv = defaultdict(list)
    count = 0
    with open(filepath, "r") as f:
        for line in f:
            r = json.loads(line.strip())
            sid = r.get("sku_id", r.get("sku", ""))
            if sid:
                inv[sid].append(r)
                count += 1
    logger.info(f"加载 {source_label}: {count} 条记录, {len(inv)} 个 SKU")
    return inv


def merge_stores(api_records, stores_records):
    """合并两个来源的门店记录，去重（按 store_name）"""
    seen = set()
    merged = []

    for rec in api_records + stores_records:
        name = rec.get("store_name", "")
        if name and name not in seen:
            seen.add(name)
            merged.append(rec)

    return merged


def compute_summary(stores):
    """计算库存汇总"""
    in_stock_stores = []
    out_of_stock_stores = []
    unknown_stores = []

    for s in stores:
        status = s.get("stock_status", "")
        is_in = s.get("in_stock", False)
        if is_in:
            in_stock_stores.append(s)
        elif status == "out_of_stock":
            out_of_stock_stores.append(s)
        else:
            unknown_stores.append(s)

    return {
        "total_stores": len(stores),
        "stores_in_stock": len(in_stock_stores),
        "stores_out_of_stock": len(out_of_stock_stores),
        "stores_unknown": len(unknown_stores),
        "has_store_channel": len(stores) > 0,
        "has_in_stock": len(in_stock_stores) > 0,
    }


def extract_store_details(stores):
    """提取门店明细列表"""
    details = []
    for s in stores:
        details.append({
            "store_name": s.get("store_name", ""),
            "store_address": s.get("store_address", ""),
            "store_city": s.get("store_city", ""),
            "store_telephone": s.get("store_telephone", ""),
            "in_stock": s.get("in_stock", False),
            "stock_status": s.get("stock_status", ""),
        })
    return details


def main():
    # 1. 加载数据
    products = load_products()
    api_inv = load_inventory(API_INV_FILE, "API 库存")
    stores_inv = load_inventory(STORES_INV_FILE, "旧爬虫库存")

    # 2. 合并
    merged_count = 0
    skipped = 0

    with open(OUTPUT_FILE, "w", encoding="utf-8") as fout:
        for sku_id, product in products.items():
            # 合并两个来源的门店
            api_records = api_inv.get(sku_id, [])
            stores_records = stores_inv.get(sku_id, [])
            all_stores = merge_stores(api_records, stores_records)

            if not all_stores:
                logger.warning(f"SKU {sku_id} 无库存记录，跳过")
                skipped += 1
                continue

            # 汇总
            summary = compute_summary(all_stores)

            # 渠道状态
            if summary["has_store_channel"] and summary["has_in_stock"]:
                channel_status = "门店有售且有库存"
            elif summary["has_store_channel"] and not summary["has_in_stock"]:
                channel_status = "门店有售无库存"
            else:
                channel_status = "仅官网有售"

            # 构建输出
            output = {
                # 商品基本信息
                "sku_id": sku_id,
                "name_local": product.get("name_local", ""),
                "price": product.get("price", 0),
                "currency": product.get("currency", "JPY"),
                "sellable": product.get("sellable", False),
                "source_url": product.get("source_url", ""),
                "images": product.get("images", []),
                "country": product.get("country", "JP"),
                # 库存汇总
                "total_stores": summary["total_stores"],
                "stores_in_stock": summary["stores_in_stock"],
                "stores_out_of_stock": summary["stores_out_of_stock"],
                "stores_unknown": summary["stores_unknown"],
                "channel_status": channel_status,
                # 门店明细
                "stores": extract_store_details(all_stores),
            }

            fout.write(json.dumps(output, ensure_ascii=False) + "\n")
            merged_count += 1

    logger.info(f"合并完成: {merged_count} 个 SKU, 跳过 {skipped} 个")
    logger.info(f"输出文件: {OUTPUT_FILE}")

    # 统计
    channel_stats = defaultdict(int)
    with open(OUTPUT_FILE, "r") as f:
        for line in f:
            r = json.loads(line.strip())
            channel_stats[r["channel_status"]] += 1

    logger.info("渠道分布:")
    for status, count in sorted(channel_stats.items()):
        logger.info(f"  {status}: {count}")


if __name__ == "__main__":
    main()