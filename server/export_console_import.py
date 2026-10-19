#!/usr/bin/env python3
"""
从 full_import_data.json 生成云开发控制台数据库导入文件（JSON Lines 格式）

微信云开发控制台数据库导入要求：
- JSON Lines 格式：每行一个 JSON 对象，行间用 \n 分隔（无逗号）
- 自定义 _id 便于 Upsert 去重（P_商品ID / PS_商品ID_国家_序号）
"""

import json
import os
import hashlib

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(BASE_DIR, "data", "lv", "cloud_import", "full_import_data.json")
OUT_DIR = os.path.join(BASE_DIR, "data", "lv", "cloud_import", "console_import")


def make_id(pid, country="", seq=0):
    """生成稳定的 _id"""
    raw = f"{pid}_{country}_{seq}"
    h = hashlib.md5(raw.encode('utf-8')).hexdigest()[:12]
    # 避免字段名首尾是 . 的问题，这里只用作 _id，无此限制
    return f"id_{h}"


def write_jsonl(path, records):
    """以 JSON Lines 写入"""
    with open(path, 'w', encoding='utf-8') as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"  {os.path.basename(path)}: {len(records)} 条, {os.path.getsize(path) / 1024 / 1024:.2f} MB")


def main():
    print("=" * 60)
    print("生成云开发控制台数据库导入文件")
    print("=" * 60)

    with open(SRC, 'r', encoding='utf-8') as f:
        data = json.load(f)

    products = data['products']
    price_stocks = data['priceStocks']
    print(f"读取: {len(products)} 商品, {len(price_stocks)} 价格库存")

    os.makedirs(OUT_DIR, exist_ok=True)

    # ============ products ============
    print("\n[1] 生成 products JSONL ...")
    # 按 productId 去重（同一商品保留第一条）
    seen = {}
    for p in products:
        pid = p.get('productId', '')
        if pid and pid not in seen:
            seen[pid] = p
    products_dedup = list(seen.values())
    print(f"  去重后: {len(products_dedup)} 条")

    product_records = []
    for p in products_dedup:
        pid = p.get('productId', '')
        record = {
            '_id': make_id("P", pid),
            'productId': pid,
            'slug': p.get('slug', ''),
            'nameCn': p.get('nameCn', ''),
            'nameJp': p.get('nameJp', ''),
            'nameEn': p.get('nameEn', ''),
            'nameKr': p.get('nameKr', ''),
            'mainImage': p.get('mainImage', ''),
            'images': p.get('images', []),
            'cnOfficialPrice': p.get('cnOfficialPrice', 0),
            'hasCnPrice': bool(p.get('hasCnPrice')),
            'category': p.get('category', ''),
            'brandId': p.get('brandId', ''),
            'brandName': p.get('brandName', ''),
            'jpPrice': p.get('jpPrice', 0),
            'jpCnyPrice': p.get('jpCnyPrice', 0),
            'krPrice': p.get('krPrice', 0),
            'krCnyPrice': p.get('krCnyPrice', 0),
            'bestGlobalPrice': p.get('bestGlobalPrice', 0),
            'bestCountry': p.get('bestCountry', ''),
            'countryCount': p.get('countryCount', 0),
            'hasStoreChannel': bool(p.get('hasStoreChannel')),
            'onlineOnly': bool(p.get('onlineOnly')),
            'storeInStock': p.get('storeInStock', 0),
            'storeOutOfStock': p.get('storeOutOfStock', 0),
            'sourceUrlCn': p.get('sourceUrlCn', ''),
            'sourceUrlJp': p.get('sourceUrlJp', ''),
            'sourceUrlKr': p.get('sourceUrlKr', ''),
        }
        product_records.append(record)

    write_jsonl(os.path.join(OUT_DIR, 'products.jsonl'), product_records)

    # ============ price_stock ============
    print("\n[2] 生成 price_stock JSONL（分片）...")
    # 按 productId 统计 + 生成记录，带稳定 _id（含序号）
    ps_records = []
    pid_seq = {}
    for ps in price_stocks:
        pid = ps.get('productId', '')
        seq = pid_seq.get(pid, 0)
        pid_seq[pid] = seq + 1
        record = {
            '_id': make_id("PS", pid, seq),
            'productId': pid,
            'countryCode': ps.get('countryCode', ''),
            'localPrice': ps.get('localPrice', 0),
            'currency': ps.get('currency', ''),
            'cnyPrice': ps.get('cnyPrice', 0),
            'stockStatus': ps.get('stockStatus', ''),
            'storeInfo': {
                'city': (ps.get('storeInfo') or {}).get('city', ''),
                'storeName': (ps.get('storeInfo') or {}).get('storeName', ''),
                'address': (ps.get('storeInfo') or {}).get('address', ''),
            },
        }
        ps_records.append(record)

    print(f"  总计: {len(ps_records)} 条")

    # 分片：每片 10000 条，避免文件过大
    CHUNK_SIZE = 10000
    for idx in range(0, len(ps_records), CHUNK_SIZE):
        chunk = ps_records[idx:idx + CHUNK_SIZE]
        write_jsonl(os.path.join(OUT_DIR, f'price_stock_{idx // CHUNK_SIZE:02d}.jsonl'), chunk)

    print("\n" + "=" * 60)
    print("生成完成！文件在:")
    print(f"  {OUT_DIR}")
    print("=" * 60)


if __name__ == '__main__':
    main()