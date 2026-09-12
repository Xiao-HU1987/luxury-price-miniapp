#!/usr/bin/env python3
"""
将 products_unified.jsonl + merged_JP.jsonl + merged_KR.jsonl
转换为云数据库导入格式（products + price_stock）
"""

import json
import os
import re
import math

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data", "lv")

# 汇率（与云函数 getProductList 保持一致）
JPY_RATE = 21.58
KRW_RATE = 192.5

# 非包包类关键词黑名单
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


def is_handbag(slug):
    """判断是否为包包类商品"""
    slug_lower = (slug or '').lower()
    for kw in NON_BAG_KEYWORDS:
        if kw in slug_lower:
            return False
    return True


def extract_slug(source_url):
    """从 source_url 中提取 slug"""
    if not source_url:
        return ''
    # 匹配 /products/{slug}/{sku_id} 格式
    m = re.search(r'/products/([^/]+)/', source_url)
    return m.group(1) if m else ''


def load_jsonl(path):
    """加载 JSONL 文件"""
    data = []
    if not os.path.exists(path):
        print(f"  [WARN] 文件不存在: {path}")
        return data
    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line:
                data.append(json.loads(line))
    return data


def build_products(unified_data):
    """构建 products 集合数据"""
    products = []
    skipped = 0

    for p in unified_data:
        sku_id = p.get('sku_id', '')
        source_url_cn = p.get('source_url_cn', '')
        slug = extract_slug(source_url_cn)

        if not is_handbag(slug):
            skipped += 1
            continue

        price_cny = p.get('price_cny', 0) or 0
        price_jp = p.get('price_jp', 0) or 0
        price_kr = p.get('price_kr', 0) or 0

        has_cn_price = p.get('source_cn', False) and price_cny > 0
        has_jp_price = p.get('source_jp', False) and price_jp > 0
        has_kr_price = p.get('source_kr', False) and price_kr > 0

        jp_cny_price = round(price_jp / JPY_RATE) if has_jp_price else 0
        kr_cny_price = round(price_kr / KRW_RATE) if has_kr_price else 0

        # 计算最优全球价格
        prices_cny = []
        if has_cn_price:
            prices_cny.append(('CN', price_cny))
        if jp_cny_price > 0:
            prices_cny.append(('JP', jp_cny_price))
        if kr_cny_price > 0:
            prices_cny.append(('KR', kr_cny_price))

        best_country = ''
        best_price = 0
        if prices_cny:
            prices_cny.sort(key=lambda x: x[1])
            best_country = prices_cny[0][0]
            best_price = prices_cny[0][1]

        country_count = len(prices_cny)

        # 图片处理
        main_image = p.get('image', '') or ''
        images = []
        if main_image:
            images.append(main_image)

        # 名称处理
        name_jp = p.get('name_jp', '') or ''
        name_en = p.get('name_en', '') or ''
        name_cn = p.get('name_cn', '') or ''
        name_kr = p.get('name_kr', '') or ''

        product = {
            'productId': sku_id,
            'slug': slug,
            'nameCn': name_cn,
            'nameJp': name_jp,
            'nameEn': name_en,
            'nameKr': name_kr,
            'mainImage': main_image,
            'images': images,
            'cnOfficialPrice': int(price_cny),
            'hasCnPrice': has_cn_price,
            'category': 'handbag',
            'brandId': 'b001',
            'brandName': 'Louis Vuitton',
            'jpPrice': int(price_jp),
            'jpCnyPrice': jp_cny_price,
            'krPrice': int(price_kr),
            'krCnyPrice': kr_cny_price,
            'bestGlobalPrice': best_price,
            'bestCountry': best_country,
            'countryCount': country_count,
            'hasStoreChannel': p.get('has_store_channel', False),
            'onlineOnly': p.get('online_only', False),
            'storeInStock': p.get('store_in_stock', 0),
            'storeOutOfStock': p.get('store_out_of_stock', 0),
            'sourceUrlCn': source_url_cn,
            'sourceUrlJp': p.get('source_url_jp', '') or '',
            'sourceUrlKr': p.get('source_url_kr', '') or '',
        }
        products.append(product)

    print(f"  商品总数: {len(products)}, 跳过非包包: {skipped}")
    return products


def build_price_stocks(merged_jp, merged_kr, unified_data):
    """构建 price_stock 集合数据（价格 + 库存）"""
    price_stocks = []

    # 从 unified 构建价格 price_stock（CN/JP/KR价格各一条）
    sku_id_set = set()
    for p in unified_data:
        sku_id = p.get('sku_id', '')
        source_url_cn = p.get('source_url_cn', '')
        slug = extract_slug(source_url_cn)
        if not is_handbag(slug):
            continue

        price_cny = p.get('price_cny', 0) or 0
        price_jp = p.get('price_jp', 0) or 0
        price_kr = p.get('price_kr', 0) or 0

        # CN 价格
        if p.get('source_cn') and price_cny > 0:
            price_stocks.append({
                'productId': sku_id,
                'countryCode': 'CN',
                'localPrice': int(price_cny),
                'currency': 'CNY',
                'cnyPrice': int(price_cny),
                'stockStatus': 'available',
                'storeInfo': {
                    'city': '',
                    'storeName': 'Louis Vuitton 中国官网',
                    'address': ''
                }
            })

        # JP 价格
        if p.get('source_jp') and price_jp > 0:
            jp_cny = round(price_jp / JPY_RATE)
            price_stocks.append({
                'productId': sku_id,
                'countryCode': 'JP',
                'localPrice': int(price_jp),
                'currency': 'JPY',
                'cnyPrice': jp_cny,
                'stockStatus': 'available',
                'storeInfo': {
                    'city': '',
                    'storeName': '日本官网',
                    'address': ''
                }
            })

        # KR 价格
        if p.get('source_kr') and price_kr > 0:
            kr_cny = round(price_kr / KRW_RATE)
            price_stocks.append({
                'productId': sku_id,
                'countryCode': 'KR',
                'localPrice': int(price_kr),
                'currency': 'KRW',
                'cnyPrice': kr_cny,
                'stockStatus': 'available',
                'storeInfo': {
                    'city': '',
                    'storeName': '韩国官网',
                    'address': ''
                }
            })

        sku_id_set.add(sku_id)

    print(f"  官网价格记录: {len(price_stocks)}")

    # 从 merged_JP 构建 JP 门店库存
    jp_store_count = 0
    for m in merged_jp:
        sku_id = m.get('sku_id', '')
        if sku_id not in sku_id_set:
            continue
        stores = m.get('stores', [])
        for s in stores:
            store_name = s.get('store_name', '')
            if not store_name:
                continue
            # 过滤掉线上客服记录
            if 'オンライン' in store_name or 'カスタマー' in store_name:
                continue

            in_stock = s.get('in_stock', False)
            stock_status = s.get('stock_status', '')
            # 标准化库存状态
            if in_stock:
                status = 'available'
            elif stock_status and ('表示' in stock_status or 'できません' in stock_status):
                status = 'unknown'
            else:
                status = 'out_of_stock'

            price_stocks.append({
                'productId': sku_id,
                'countryCode': 'JP',
                'localPrice': m.get('price', 0) or 0,
                'currency': 'JPY',
                'cnyPrice': round((m.get('price', 0) or 0) / JPY_RATE),
                'stockStatus': status,
                'storeInfo': {
                    'city': s.get('store_city', ''),
                    'storeName': store_name,
                    'address': s.get('store_address', '')
                }
            })
            jp_store_count += 1

    print(f"  JP门店库存记录: {jp_store_count}")

    # 从 merged_KR 构建 KR 门店库存
    kr_store_count = 0
    for m in merged_kr:
        sku_id = m.get('sku_id', '')
        if sku_id not in sku_id_set:
            continue
        stores = m.get('stores', [])
        for s in stores:
            store_name = s.get('store_name', '')
            if not store_name:
                continue

            in_stock = s.get('in_stock', False)
            stock_status = s.get('stock_status', '')
            if in_stock:
                status = 'available'
            elif stock_status and ('표시' in stock_status or '없습니다' in stock_status):
                status = 'unknown'
            else:
                status = 'out_of_stock'

            price_stocks.append({
                'productId': sku_id,
                'countryCode': 'KR',
                'localPrice': m.get('price', 0) or 0,
                'currency': 'KRW',
                'cnyPrice': round((m.get('price', 0) or 0) / KRW_RATE),
                'stockStatus': status,
                'storeInfo': {
                    'city': s.get('store_city', ''),
                    'storeName': store_name,
                    'address': s.get('store_address', '')
                }
            })
            kr_store_count += 1

    print(f"  KR门店库存记录: {kr_store_count}")
    print(f"  总 price_stock 记录: {len(price_stocks)}")

    return price_stocks


def split_into_chunks(products, price_stocks, chunk_size=10):
    """将数据分成多个 chunk，每个 chunk 含约 chunk_size 个商品"""
    chunks = []
    for i in range(0, len(products), chunk_size):
        chunk_products = products[i:i + chunk_size]
        product_ids = set(p['productId'] for p in chunk_products)
        chunk_price_stocks = [ps for ps in price_stocks if ps['productId'] in product_ids]
        chunks.append({
            'products': chunk_products,
            'priceStocks': chunk_price_stocks
        })
    return chunks


def main():
    print("=" * 60)
    print("数据转换脚本：products_unified.jsonl → 云数据库格式")
    print("=" * 60)

    # 加载数据
    print("\n[1] 加载数据文件...")
    unified_path = os.path.join(DATA_DIR, "aligned", "products_unified.jsonl")
    merged_jp_path = os.path.join(DATA_DIR, "JP", "merged_JP.jsonl")
    merged_kr_path = os.path.join(DATA_DIR, "KR", "merged_KR.jsonl")

    unified_data = load_jsonl(unified_path)
    merged_jp = load_jsonl(merged_jp_path)
    merged_kr = load_jsonl(merged_kr_path)

    print(f"  products_unified: {len(unified_data)} 条")
    print(f"  merged_JP: {len(merged_jp)} 条")
    print(f"  merged_KR: {len(merged_kr)} 条")

    # 构建 products
    print("\n[2] 构建 products 集合...")
    products = build_products(unified_data)

    # 构建 price_stocks
    print("\n[3] 构建 price_stock 集合...")
    price_stocks = build_price_stocks(merged_jp, merged_kr, unified_data)

    # 分成 chunks
    print("\n[4] 分割数据...")
    chunks = split_into_chunks(products, price_stocks, chunk_size=10)
    print(f"  共 {len(chunks)} 个 chunk")

    # 输出
    output_dir = os.path.join(DATA_DIR, "cloud_import")
    os.makedirs(output_dir, exist_ok=True)

    # 保存完整数据（用于参考）
    print("\n[5] 保存数据...")
    full_path = os.path.join(output_dir, "full_import_data.json")
    with open(full_path, 'w', encoding='utf-8') as f:
        json.dump({
            'products': products,
            'priceStocks': price_stocks
        }, f, ensure_ascii=False, indent=2)
    print(f"  完整数据: {full_path}")

    # 保存分片数据
    for idx, chunk in enumerate(chunks):
        chunk_path = os.path.join(output_dir, f"import_chunk_{idx:03d}.json")
        with open(chunk_path, 'w', encoding='utf-8') as f:
            json.dump(chunk, f, ensure_ascii=False, indent=2)
        print(f"  Chunk {idx}: {chunk_path} "
              f"({len(chunk['products'])} products, "
              f"{len(chunk['priceStocks'])} price_stocks)")

    # 保存 JS 模块（可直接被云函数 require）
    print("\n[6] 生成 JS 模块...")
    for idx, chunk in enumerate(chunks):
        js_path = os.path.join(output_dir, f"import_chunk_{idx:03d}.js")
        js_content = "module.exports = " + json.dumps(chunk, ensure_ascii=False, indent=2) + ";"
        with open(js_path, 'w', encoding='utf-8') as f:
            f.write(js_content)

    # 生成汇总报告
    print("\n" + "=" * 60)
    print("转换完成！")
    print(f"  商品总数: {len(products)}")
    print(f"  价格库存总数: {len(price_stocks)}")
    print(f"  分片数: {len(chunks)}")
    print(f"  输出目录: {output_dir}")
    print("=" * 60)

    # 统计信息
    cn_count = sum(1 for p in products if p['hasCnPrice'])
    jp_count = sum(1 for p in products if p['jpCnyPrice'] > 0)
    kr_count = sum(1 for p in products if p['krCnyPrice'] > 0)
    jp_store_skus = len(set(ps['productId'] for ps in price_stocks
                            if ps['countryCode'] == 'JP' and ps['storeInfo']['storeName'] != '日本官网'))
    kr_store_skus = len(set(ps['productId'] for ps in price_stocks
                            if ps['countryCode'] == 'KR' and ps['storeInfo']['storeName'] != '韩国官网'))

    print(f"\n数据统计:")
    print(f"  有CN价格: {cn_count}")
    print(f"  有JP价格: {jp_count}")
    print(f"  有KR价格: {kr_count}")
    print(f"  有JP门店库存的SKU: {jp_store_skus}")
    print(f"  有KR门店库存的SKU: {kr_store_skus}")


if __name__ == '__main__':
    main()