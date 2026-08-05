"""解析爬虫原始捕获数据，生成可导入云数据库的 JSON 文件

用法：
    python3 scripts/import_crawler_data.py

输出：
    data/import_products.json  - 商品数据
    data/import_price_stock.json - 价格库存数据
"""
import json
import os
import re
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).resolve().parent.parent
CAPTURES_DIR = BASE_DIR / 'server' / 'crawler' / 'raw_captures'
OUTPUT_DIR = BASE_DIR / 'data'

# 汇率（JPY -> CNY）
JPY_RATE = 0.0462  # 1日元 ≈ 0.0462人民币

# 品牌映射
BRAND_MAP = {
    'lv': {'brandId': 'b001', 'brandName': 'Louis Vuitton', 'brandNameCn': '路易威登'},
}

# 分类映射
CATEGORY_MAP = {
    'handbag': 'handbag',
    'bag': 'handbag',
    'wallet': 'wallet',
    'small-leather-goods': 'slg',
    'accessories': 'accessories',
    'shoes': 'shoes',
    'ready-to-wear': 'rtw',
    'jewelry': 'jewelry',
    'watch': 'watch',
}

# 只抓取包包类商品，非包包类直接跳过
ALLOWED_CATEGORIES = {'handbag'}

# 非包包类商品关键词黑名单（slug/url 中包含这些词的都不是包包）
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


def extract_sku_captures():
    """提取所有 SKU 详情捕获文件"""
    sku_files = []
    for f in CAPTURES_DIR.iterdir():
        if f.is_file() and 'skus_' in f.name and f.suffix == '.json':
            sku_files.append(f)
    return sku_files


def parse_product_name_jp(name_jp):
    """从日文商品名提取信息（简单映射）"""
    return {
        'nameCn': name_jp,  # 暂时用日文名，后续可翻译
        'nameEn': '',
    }


def process_sku_file(filepath):
    """处理单个 SKU 文件，返回商品和价格数据"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except (json.JSONDecodeError, IOError):
        return [], []

    products = []
    price_stocks = []

    if not isinstance(data, list):
        return products, price_stocks

    for item in data:
        if not isinstance(item, dict):
            continue

        sku_id = item.get('skuId', '')
        product_id = item.get('productId', '')
        name_jp = item.get('name', '')
        price_raw = item.get('priceRaw', 0)
        media_url = item.get('mediaUrl', '')
        medias = item.get('medias', [])
        sellable = item.get('sellable', False)
        url_path = item.get('url', '')

        # 生成主图 URL
        main_image = ''
        all_images = []
        if medias and isinstance(medias, list):
            for m in medias:
                if isinstance(m, dict) and m.get('url'):
                    img_url = m['url']
                    # 确保使用 HTTPS
                    if img_url.startswith('//'):
                        img_url = 'https:' + img_url
                    all_images.append(img_url)
            if all_images:
                main_image = all_images[0]
        elif media_url:
            main_image = media_url
            if main_image.startswith('//'):
                main_image = 'https:' + main_image
            all_images = [main_image]

        # 解析商品分类
        category = 'handbag'
        if url_path:
            path_lower = url_path.lower()
            for cat_key, cat_val in CATEGORY_MAP.items():
                if cat_key in path_lower:
                    category = cat_val
                    break

        # 只保留包包类商品，非包包类直接跳过
        if category not in ALLOWED_CATEGORIES:
            continue

        # 提取商品 slug（从 URL）
        slug = ''
        if url_path:
            match = re.search(r'/products/([^/]+)/', url_path)
            if match:
                slug = match.group(1)

        # 构建商品数据
        cn_price = 0  # 暂无中国价格数据
        jp_price = price_raw
        jp_cny = round(price_raw * JPY_RATE) if price_raw else 0

        product = {
            'productId': sku_id,
            'slug': slug,
            'nameCn': name_jp,  # 日文名，后续翻译
            'nameEn': '',
            'mainImage': main_image,
            'images': all_images[:5],  # 最多5张
            'cnOfficialPrice': cn_price,
            'category': category,
            'brandId': 'b001',
            'brandName': 'Louis Vuitton',
            'dimensions': item.get('dimensionsData', [{}])[0] if item.get('dimensionsData') else {},
            'createTime': datetime.now().isoformat() + 'Z',
        }
        products.append(product)

        # 构建日本价格库存
        if price_raw > 0:
            ps_jp = {
                'productId': sku_id,
                'countryCode': 'JP',
                'localPrice': price_raw,
                'currency': 'JPY',
                'cnyPrice': jp_cny,
                'stockStatus': 'available' if sellable else 'out_of_stock',
                'storeInfo': {
                    'city': '东京',
                    'storeName': '日本官网',
                    'address': '',
                },
                'priceUpdateTime': datetime.now().isoformat() + 'Z',
            }
            price_stocks.append(ps_jp)

    return products, price_stocks


def deduplicate_products(products):
    """按 productId 去重，保留最新的"""
    seen = {}
    for p in products:
        pid = p.get('productId', '')
        if pid and pid not in seen:
            seen[pid] = p
        elif pid and pid in seen:
            # 保留有图片的
            if p.get('mainImage') and not seen[pid].get('mainImage'):
                seen[pid] = p
    return list(seen.values())


def deduplicate_price_stocks(price_stocks):
    """按 productId + countryCode 去重"""
    seen = {}
    for ps in price_stocks:
        key = f"{ps.get('productId', '')}_{ps.get('countryCode', '')}"
        if key not in seen:
            seen[key] = ps
    return list(seen.values())


def main():
    print('扫描爬虫捕获文件...')
    sku_files = extract_sku_captures()
    print(f'找到 {len(sku_files)} 个 SKU 捕获文件')

    all_products = []
    all_price_stocks = []

    for f in sku_files:
        products, price_stocks = process_sku_file(f)
        all_products.extend(products)
        all_price_stocks.extend(price_stocks)

    print(f'原始商品数: {len(all_products)}')
    print(f'原始价格库存数: {len(all_price_stocks)}')

    # 去重
    all_products = deduplicate_products(all_products)
    all_price_stocks = deduplicate_price_stocks(all_price_stocks)

    print(f'去重后商品数: {len(all_products)}')
    print(f'去重后价格库存数: {len(all_price_stocks)}')

    # 统计
    has_images = sum(1 for p in all_products if p.get('mainImage'))
    has_prices = sum(1 for ps in all_price_stocks if ps.get('localPrice', 0) > 0)
    print(f'有图片的商品: {has_images}')
    print(f'有价格的库存记录: {has_prices}')

    # 确保输出目录存在
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # 写入输出文件
    products_file = OUTPUT_DIR / 'import_products.json'
    price_stocks_file = OUTPUT_DIR / 'import_price_stock.json'

    with open(products_file, 'w', encoding='utf-8') as f:
        json.dump(all_products, f, ensure_ascii=False, indent=2)
    print(f'商品数据已写入: {products_file}')

    with open(price_stocks_file, 'w', encoding='utf-8') as f:
        json.dump(all_price_stocks, f, ensure_ascii=False, indent=2)
    print(f'价格库存数据已写入: {price_stocks_file}')

    # 生成导入摘要
    summary = {
        'totalProducts': len(all_products),
        'totalPriceStocks': len(all_price_stocks),
        'hasImages': has_images,
        'hasPrices': has_prices,
        'generatedAt': datetime.now().isoformat(),
    }
    summary_file = OUTPUT_DIR / 'import_summary.json'
    with open(summary_file, 'w', encoding='utf-8') as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    print(f'\n=== 导入摘要 ===')
    print(f'商品总数: {summary["totalProducts"]}')
    print(f'价格库存总数: {summary["totalPriceStocks"]}')
    print(f'有图片商品: {summary["hasImages"]}')
    print(f'=================')

    return 0


if __name__ == '__main__':
    exit(main())
