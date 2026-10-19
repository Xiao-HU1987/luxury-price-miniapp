"""LV 三站（CN/JP/KR）商品数据对齐脚本 v3

变更说明（vs v2）：
1. 汇率：移除 price_jp_to_cny / price_kr_to_cny 固定汇率字段，
   改为关联 exchange_rates 表，由 API / 前端实时换算。
2. 图片锚点：增加 image_phash + image_match_confidence 字段，
   用感知哈希比对三站同 SKU 图片是否一致。相似度在 [0.70, 0.90) 区间
   的记录会写入 image_manual_review.jsonl，等待人工校验。
3. 数据锚点升级：sku_id (主键) + brand + image_phash (辅助)

整合数据库字段顺序（用户指定）：
  brand | sku_id | name_en | name_cn | name_kr | name_jp |
  price_cny | price_jp | price_kr |           # 移除了to_cny固定字段
  image | image_phash | image_match_confidence |  # 新增图片哈希
  category | source_cn/jp/kr | store_cities

数据流：
  products_XX.jsonl → products_XX_clean.jsonl → products_unified.jsonl
                                    ↘ image_manual_review.jsonl（不确定项）

用法：
    python3 -m crawler.lv_align_three_sites           # 用 DB 汇率 + 图片比对
    python3 -m crawler.lv_align_three_sites --skip-image  # 跳过图片哈希(更快)
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

DATA_ROOT = BASE_DIR.parent / "data" / "lv"

# 品牌统一标识
BRAND_NAME = "Louis Vuitton"

# 默认兜底汇率（DB不可用时最后一道防线，不写入整合数据，仅日志打印）
FALLBACK_RATES = {"JPY": 0.048, "KRW": 0.0053, "USD": 7.25}

# 图片比对阈值
PHASH_HIGH_CONF = 0.90   # >= 判定为同图
PHASH_LOW_CONF = 0.70    # <  判定为不同图
# 介于 LOW~HIGH 之间 → 需人工校验


# ==================================================================
# 工具函数
# ==================================================================

def _load_jsonl(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    records = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def _save_jsonl(path: Path, records: List[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


# ==================================================================
# 汇率：关联 exchange_rates 表
# ==================================================================

def get_exchange_rates_from_db() -> Tuple[Dict[str, float], Optional[str]]:
    """
    从数据库读取最新汇率。
    返回 (rates_dict, update_time_iso)
    rates_dict: { "JPY": x.xx, "KRW": x.xx, "USD": x.xx }，基准 CNY
    """
    try:
        from database import SessionLocal
        from models import ExchangeRate

        db = SessionLocal()
        try:
            latest = db.query(ExchangeRate).order_by(ExchangeRate.update_time.desc()).first()
            if latest:
                rates = {k: float(v) for k, v in latest.rates.items()}
                upd = latest.update_time.isoformat() if latest.update_time else None
                return rates, upd
        finally:
            db.close()
    except Exception as e:
        print(f"[WARN] 读取DB汇率失败，使用兜底值: {e}")
    return FALLBACK_RATES.copy(), None


# ==================================================================
# 名称提取
# ==================================================================

def _has_chinese(text: str) -> bool:
    return bool(re.search(r'[\u4e00-\u9fff]', text))


def _has_korean(text: str) -> bool:
    return bool(re.search(r'[\uac00-\ud7af]', text))


def _extract_english_name(name_local: str, name: str = "") -> str:
    if name and not _has_korean(name) and not _has_chinese(name):
        return name.strip()
    if not name_local:
        return ""
    m = re.search(r'[（(]([^()（）]+)[)）]', name_local)
    if m:
        inner = m.group(1).strip()
        if not _has_chinese(inner) and not _has_korean(inner):
            return inner
    if _has_chinese(name_local):
        m = re.match(r'^([A-Za-z][A-Za-z0-9éèêëàâîïùôî][\s\-\']+?)(?:\s*[\u4e00-\u9fff])', name_local)
        if m:
            return m.group(1).strip()
    return ""


def _extract_chinese_name(name_local: str) -> str:
    if not name_local:
        return ""
    if _has_chinese(name_local):
        parts = re.findall(r'[\u4e00-\u9fff]+', name_local)
        if parts:
            return ''.join(parts)
    return ""


# ==================================================================
# 门店城市解析
# ==================================================================

JP_CITY_KEYWORDS = ["東京", "大阪", "京都", "横浜", "名古屋", "神戸", "福岡",
                    "札幌", "仙台", "埼玉", "千葉", "広島", "沖縄"]
KR_CITY_KEYWORDS = ["서울", "부산", "대구", "인천", "광주", "대전", "울산", "제주"]


def _parse_city_from_address(address: str, country: str) -> str:
    if not address:
        return ""
    keywords = JP_CITY_KEYWORDS if country == "JP" else KR_CITY_KEYWORDS
    for kw in keywords:
        if kw in address:
            return kw
    if country == "JP":
        m = re.search(r'([\u3040-\u30ff\u4e00-\u9fff]+[都府県市])', address)
    else:
        m = re.search(r'([\uac00-\ud7af]+[시도])', address)
    return m.group(1) if m else ""


def _parse_city_from_store_name(store_name: str, country: str) -> str:
    if not store_name:
        return ""
    keywords = JP_CITY_KEYWORDS if country == "JP" else KR_CITY_KEYWORDS
    for kw in keywords:
        if kw in store_name:
            return kw
    if country == "JP":
        m = {
            "表参道": "東京", "新宿": "東京", "銀座": "東京", "六本木": "東京",
            "池袋": "東京", "渋谷": "東京", "丸の内": "東京", "日本橋": "東京",
            "梅田": "大阪", "心斎橋": "大阪", "難波": "大阪",
            "博多": "福岡", "天神": "福岡",
            "栄": "名古屋", "三宮": "神戸", "河原町": "京都",
        }
    else:
        m = {"강남": "서울", "신세계 강남": "서울", "압구정": "서울",
             "센텀": "부산", "해운대": "부산"}
    for area, city in m.items():
        if area in store_name:
            return city
    return ""


# ==================================================================
# 图片感知哈希 (pHash, DCT based, Pillow 可用时)
# ==================================================================

def _phash_available() -> bool:
    try:
        from PIL import Image  # noqa: F401
        return True
    except Exception:
        return False


# 图片下载设置
# CN官网(www.louisvuitton.cn)不被Akamai拦截，是最佳图片源
# 策略：1）替换为CN官网域名（优先）；2）原始URL；3）代理
_CN_IMAGE_DOMAIN = "https://www.louisvuitton.cn"
_ALT_DOMAINS = [
    # 替换为CN官网域名（优先，不被Akamai拦截）
    lambda u: re.sub(r'https?://[^/]*louisvuitton\.(com|cn|jp|kr)', _CN_IMAGE_DOMAIN, u),
    # 保持原域（JP/KR图片CDN，可能被Akamai拦截）
    lambda u: u,
]


def _build_openers() -> List:
    """构造多种下载 opener：直连 → 代理 → 带Referer直连"""
    import urllib.request
    openers = []
    # 1) 直连
    openers.append(urllib.request.build_opener())
    # 2) 代理（如果有配置）
    proxy = (os.environ.get("IMG_PROXY")
             or os.environ.get("HTTPS_PROXY") or os.environ.get("https_proxy")
             or os.environ.get("HTTP_PROXY") or os.environ.get("http_proxy"))
    try:
        from crawler import config as ccfg
        proxy = getattr(ccfg, "IMAGE_PROXY", None) or proxy
    except Exception:
        pass
    if proxy:
        ph = urllib.request.ProxyHandler({"https": proxy, "http": proxy})
        openers.append(urllib.request.build_opener(ph))
    return openers


def _download_image_bytes(full_url: str) -> Optional[bytes]:
    """多策略下载图片（直连+换CN域名+代理），返回 bytes 或 None"""
    import urllib.request

    openers = _build_openers()
    base_headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)",
        "Accept": "image/webp,image/apng,image/*,*/*;q=0.8",
    }

    # 遍历: 每个URL变体 × 每个opener
    for url_variant in (fn(full_url) for fn in _ALT_DOMAINS):
        for ref in ("https://jp.louisvuitton.com/", "https://kr.louisvuitton.com/",
                    "https://www.louisvuitton.cn/", None):
            headers = dict(base_headers)
            if ref:
                headers["Referer"] = ref
            req = urllib.request.Request(url_variant, headers=headers)
            for opener in openers:
                try:
                    with opener.open(req, timeout=10) as resp:
                        data = resp.read()
                        if len(data) >= 500 and resp.status == 200:
                            return data
                except Exception:
                    continue
    return None


def _compute_phash(img_url: str, sku_id: str = "") -> str:
    """
    计算 64bit pHash（16进制字符串，如 "a1b2c3d4e5f60708"）。
    优先从本地已下载图片读取，避免重复网络下载。失败返回空串。
    """
    if not img_url:
        return ""
    try:
        from PIL import Image
        import io

        # 1. 优先从本地文件读取（如果图片已下载到 server/static/images/lv/）
        img_bytes = None
        if sku_id:
            local_path = BASE_DIR / "static" / "images" / "lv" / f"{sku_id}.jpg"
            if local_path.exists() and local_path.stat().st_size > 500:
                img_bytes = local_path.read_bytes()

        # 2. 本地无缓存则从网络下载
        if img_bytes is None:
            full_url = img_url
            if full_url.startswith("//"):
                full_url = "https:" + full_url
            elif full_url.startswith("/") and not full_url.startswith("http"):
                full_url = "https://jp.louisvuitton.com" + full_url
            # URL编码空格
            full_url = full_url.replace(" ", "%20")
            img_bytes = _download_image_bytes(full_url)

        if img_bytes is None or len(img_bytes) < 500:
            return ""

        # 3. DCT简化版pHash: 32x32灰度 → 8x8块均值 → 64bit
        img = Image.open(io.BytesIO(img_bytes))
        img = img.convert("L").resize((32, 32), Image.LANCZOS)
        pixels = list(img.getdata())
        total_avg = sum(pixels) / len(pixels)
        bits = []
        for by in range(8):
            for bx in range(8):
                s = 0
                for dy in range(4):
                    for dx in range(4):
                        s += pixels[(by * 4 + dy) * 32 + (bx * 4 + dx)]
                bits.append("1" if (s / 16) >= total_avg else "0")
        return f"{int(''.join(bits), 2):016x}"
    except Exception:
        return ""


def _hamming_similarity(h1: str, h2: str) -> float:
    """两个 64bit pHash 的相似度（0~1）"""
    if not h1 or not h2 or len(h1) != len(h2):
        return 0.0
    if h1 == h2:
        return 1.0
    xor = int(h1, 16) ^ int(h2, 16)
    hamming = bin(xor).count("1")
    return 1.0 - (hamming / 64.0)


# ==================================================================
# 主逻辑
# ==================================================================

def load_clean_products() -> Dict[str, List[Dict[str, Any]]]:
    products = {}
    for country in ["CN", "JP", "KR"]:
        clean_file = DATA_ROOT / country / f"products_{country}_clean.jsonl"
        products[country] = _load_jsonl(clean_file)
        print(f"加载 {country} 清理后数据: {len(products[country])} 条")
    return products


def load_inventories() -> Dict[str, Dict[str, List[Dict[str, Any]]]]:
    inventories: Dict[str, Dict[str, List[Dict[str, Any]]]] = {}
    for country in ["CN", "JP", "KR"]:
        inv_file = DATA_ROOT / country / f"inventories_{country}_stores.jsonl"
        records = _load_jsonl(inv_file)
        by_sku: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        for r in records:
            sku = r.get("sku_id", "").upper()
            if sku:
                by_sku[sku].append(r)
        inventories[country] = dict(by_sku)
        print(f"加载 {country} 门店库存: {len(records)} 条, {len(by_sku)} SKU")
    return inventories


def build_unified(products: Dict[str, List[Dict[str, Any]]],
                  inventories: Dict[str, Dict[str, List[Dict[str, Any]]]],
                  rates: Dict[str, float],
                  skip_image: bool = False) -> Tuple[List[Dict[str, Any]],
                                                     List[Dict[str, Any]]]:
    """
    返回 (unified_records, manual_review_records)
    manual_review_records: 图片相似度不确定，需人工校验的条目
    """

    merged: Dict[str, Dict[str, Any]] = {}
    # 暂存三站各自 image url，用于合并后做交叉哈希比对
    per_sku_images: Dict[str, Dict[str, str]] = defaultdict(dict)

    def _ensure_sku(sku: str) -> Dict[str, Any]:
        if sku not in merged:
            merged[sku] = {
                "brand": BRAND_NAME,
                "sku_id": sku,
                "name_en": "",
                "name_cn": "",
                "name_kr": "",
                "name_jp": "",
                "price_cny": None,       # 人民币原始价格
                "price_jp": None,        # 日元原始价格
                "price_kr": None,        # 韩币原始价格
                "image": "",             # 主图 URL
                "image_phash": "",       # 主图感知哈希（新增锚点）
                "image_match_confidence": 0.0,  # 三站图片交叉置信度
                "category": "",          # 分类（未提取到）
                "source_cn": False,      # CN官网有售
                "source_jp": False,      # JP官网有售
                "source_kr": False,      # KR官网有售
                "source_url_cn": "",
                "source_url_jp": "",
                "source_url_kr": "",
                # 门店渠道与库存状态（新增）
                "has_store_channel": False,   # 门店有售（有门店库存面板，区别于线上专属）
                "online_only": False,          # 仅官网有售（无门店渠道）
                "store_in_stock": False,       # 门店有售且有库存（至少1家门店有货）
                "store_out_of_stock": False,   # 门店有售但无库存（所有门店均无货）
                "store_names": [],             # 门店名称列表
                "store_addresses": [],         # 门店地址列表
                "store_cities": [],            # 门店城市列表
                "store_count": 0,              # 门店总数
                "store_stock_count": 0,        # 有库存的门店数
                "has_store_stock": False,      # 兼容旧字段：是否有门店有库存
            }
        return merged[sku]

    # 1. CN
    for p in products.get("CN", []):
        sku = p.get("sku_id", "").upper()
        if not sku:
            continue
        m = _ensure_sku(sku)
        m["source_cn"] = True
        m["source_url_cn"] = p.get("source_url", "")
        m["price_cny"] = p.get("price")
        m["name_cn"] = _extract_chinese_name(p.get("name_local", ""))
        imgs = p.get("images") or []
        if imgs:
            per_sku_images[sku]["CN"] = imgs[0]

    # 2. JP
    for p in products.get("JP", []):
        sku = p.get("sku_id", "").upper()
        if not sku:
            continue
        m = _ensure_sku(sku)
        m["source_jp"] = True
        m["source_url_jp"] = p.get("source_url", "")
        m["price_jp"] = p.get("price")
        m["name_jp"] = p.get("name_local", "")
        imgs = p.get("images") or []
        if imgs:
            per_sku_images[sku]["JP"] = imgs[0]
            if not m["image"]:
                m["image"] = imgs[0]

    # 3. KR
    for p in products.get("KR", []):
        sku = p.get("sku_id", "").upper()
        if not sku:
            continue
        m = _ensure_sku(sku)
        m["source_kr"] = True
        m["source_url_kr"] = p.get("source_url", "")
        m["price_kr"] = p.get("price")
        m["name_kr"] = p.get("name_local", "") or p.get("name", "")
        imgs = p.get("images") or []
        if imgs:
            per_sku_images[sku]["KR"] = imgs[0]
            if not m["image"]:
                m["image"] = imgs[0]

    print(f"\n合并后 SKU 总数: {len(merged)}")

    # 4. 补全英文名/中文名
    for sku, m in merged.items():
        if m["name_kr"]:
            m["name_en"] = _extract_english_name(m["name_kr"])
        if not m["name_en"] and m["name_cn"]:
            m["name_en"] = _extract_english_name(m.get("source_url_cn", ""))
        if not m["name_cn"] and m["source_cn"]:
            m["name_cn"] = _extract_chinese_name(m.get("source_url_cn", ""))

    # 5. 图片 pHash 锚点 + 交叉比对
    manual_review: List[Dict[str, Any]] = []
    if not skip_image and _phash_available():
        print(f"\n[图片锚点] Pillow 可用，开始计算 pHash ...")
        phash_cache: Dict[str, str] = {}  # url → hash，三站共用同一URL不重复下载
        processed = 0
        for sku, m in merged.items():
            imgs_dict = per_sku_images.get(sku, {})
            if not imgs_dict:
                continue
            # 计算每站图片哈希
            phashes: Dict[str, str] = {}
            for country_, url_ in imgs_dict.items():
                if url_ not in phash_cache:
                    phash_cache[url_] = _compute_phash(url_, sku)
                phashes[country_] = phash_cache[url_]
            # 主图哈希
            main_url = m["image"]
            if main_url:
                if main_url not in phash_cache:
                    phash_cache[main_url] = _compute_phash(main_url, sku)
                m["image_phash"] = phash_cache[main_url]
            # 交叉比对置信度（多站图片的最小对相似度）
            sims = []
            cs = list(phashes.keys())
            for i in range(len(cs)):
                for j in range(i + 1, len(cs)):
                    s = _hamming_similarity(phashes[cs[i]], phashes[cs[j]])
                    if s > 0:
                        sims.append(s)
            if sims:
                m["image_match_confidence"] = round(min(sims), 3)
                # 落入 [LOW, HIGH) → 人工校验
                if PHASH_LOW_CONF <= m["image_match_confidence"] < PHASH_HIGH_CONF:
                    manual_review.append({
                        "sku_id": sku,
                        "image_match_confidence": m["image_match_confidence"],
                        "images": imgs_dict,
                        "phashes": phashes,
                        "note": f"相似度 {m['image_match_confidence']:.2f} 介于 {PHASH_LOW_CONF}-{PHASH_HIGH_CONF}，需人工校验是否为同一商品图片",
                    })
            processed += 1
            if processed % 50 == 0:
                print(f"[图片锚点] 已处理 {processed}/{len(merged)}")
        print(f"[图片锚点] 完成: {processed} SKU, 人工校验: {len(manual_review)} 条")
    elif skip_image:
        print(f"\n[图片锚点] 已跳过 (--skip-image)")
    else:
        print(f"\n[图片锚点] Pillow 未安装，跳过 (pip install Pillow 可启用)")

    # 6. 门店渠道与库存状态（JP/KR），聚合门店名称/地址/城市
    IN_STOCK_KEYWORDS = ("in_stock", "available", "재고 있음", "在庫あり", "残りわずか")
    for sku, m in merged.items():
        all_cities = set()
        store_names = []
        store_addresses = []
        store_count = 0
        stock_count = 0
        has_stock = False

        for country in ["JP", "KR"]:
            for inv in inventories.get(country, {}).get(sku, []):
                store_count += 1
                name = (inv.get("store_name", "") or inv.get("store_id", "")).strip()
                address = (inv.get("store_address", "") or "").strip()
                # 优先使用库存数据中已有的 store_city 字段，避免重复解析丢精度
                city = (inv.get("store_city", "") or "").strip()
                if not city:
                    city = _parse_city_from_address(address, country)
                if not city:
                    city = _parse_city_from_store_name(name, country)

                if name and name not in store_names:
                    store_names.append(name)
                if address and address not in store_addresses:
                    store_addresses.append(address)
                if city:
                    all_cities.add(city)

                # 判定该门店是否有库存
                in_stock = inv.get("in_stock", False)
                status = inv.get("stock_status", "") or ""
                if in_stock or any(k in status for k in IN_STOCK_KEYWORDS):
                    stock_count += 1
                    has_stock = True

        m["store_cities"] = sorted(all_cities)
        m["store_names"] = store_names
        m["store_addresses"] = store_addresses
        m["store_count"] = store_count
        m["store_stock_count"] = stock_count
        m["has_store_stock"] = has_stock

        # 渠道与库存状态四字段
        # has_store_channel: 门店有售（采集到门店库存记录）
        # online_only: 仅官网有售（无门店渠道，即线上专属）
        # store_in_stock: 门店有售且有库存
        # store_out_of_stock: 门店有售但当前无库存
        m["has_store_channel"] = store_count > 0
        m["online_only"] = (not m["has_store_channel"]) and (
            m["source_cn"] or m["source_jp"] or m["source_kr"])
        m["store_in_stock"] = m["has_store_channel"] and has_stock
        m["store_out_of_stock"] = m["has_store_channel"] and (not has_stock)

    # 7. 排序
    result = list(merged.values())
    result.sort(key=lambda x: (
        -(x["source_cn"] + x["source_jp"] + x["source_kr"]),
        -x["store_count"],
        x["sku_id"],
    ))
    return result, manual_review


def generate_stats(unified: List[Dict[str, Any]],
                   manual_review: List[Dict[str, Any]],
                   rates: Dict[str, float],
                   rates_update_time: Optional[str]) -> Dict[str, Any]:
    total = len(unified)
    return {
        "generated_at": datetime.now().isoformat(),
        "total_skus": total,
        "brand": BRAND_NAME,
        "field_order": [
            "brand", "sku_id", "name_en", "name_cn", "name_kr", "name_jp",
            "price_cny", "price_jp", "price_kr",
            "image", "image_phash", "image_match_confidence",
            "category",
            "source_cn/jp/kr",                        # 官网是否有售
            "has_store_channel", "online_only",       # 门店渠道
            "store_in_stock", "store_out_of_stock",   # 门店库存状态
            "store_names", "store_addresses", "store_cities",  # 门店明细
            "store_count", "store_stock_count",        # 门店数量统计
        ],
        "data_anchor_points": "sku_id (primary) + image_phash (auxiliary)",
        "exchange_rates_note": "price_jp_to_cny/price_kr_to_cny 字段已移除。"
                               " 外币→CNY 请调用 POST /api/exchange/convert 或"
                               " 使用 exchange_rates 表最新记录实时换算。",
        "exchange_rates_db": {
            "source": "exchange_rates 表 (基准 CNY)",
            "rates": rates,
            "update_time": rates_update_time,
        },
        "image_match": {
            "threshold_high_confidence": PHASH_HIGH_CONF,
            "threshold_manual_review_range_min": PHASH_LOW_CONF,
            "threshold_manual_review_range_max_exclusive": PHASH_HIGH_CONF,
            "manual_review_count": len(manual_review),
        },
        "coverage": {
            "cn": sum(1 for u in unified if u["source_cn"]),
            "jp": sum(1 for u in unified if u["source_jp"]),
            "kr": sum(1 for u in unified if u["source_kr"]),
            "all_three": sum(1 for u in unified if u["source_cn"] and u["source_jp"] and u["source_kr"]),
            "cn_jp_only": sum(1 for u in unified if u["source_cn"] and u["source_jp"] and not u["source_kr"]),
            "has_store_data": sum(1 for u in unified if u["store_count"] > 0),
            "has_store_stock": sum(1 for u in unified if u["has_store_stock"]),
            "has_image": sum(1 for u in unified if u["image"]),
            "has_phash": sum(1 for u in unified if u["image_phash"]),
            "has_name_en": sum(1 for u in unified if u["name_en"]),
            "has_name_cn": sum(1 for u in unified if u["name_cn"]),
            # 新增门店渠道与库存状态统计
            "has_store_channel": sum(1 for u in unified if u["has_store_channel"]),
            "online_only": sum(1 for u in unified if u["online_only"]),
            "store_in_stock": sum(1 for u in unified if u["store_in_stock"]),
            "store_out_of_stock": sum(1 for u in unified if u["store_out_of_stock"]),
        },
    }


def main():
    parser = argparse.ArgumentParser(description="LV 三站商品数据对齐 v3 (汇率DB版+图片锚点)")
    parser.add_argument("--skip-image", action="store_true", help="跳过图片 pHash 计算（更快）")
    args = parser.parse_args()

    # 1. 取汇率（从DB）
    print("[0/4] 从 exchange_rates 表读取汇率...")
    rates, rates_upd = get_exchange_rates_from_db()
    print(f"  汇率: JPY={rates.get('JPY', '?')}, KRW={rates.get('KRW', '?')}")
    print(f"  更新时间: {rates_upd or 'N/A'}")

    print(f"\n品牌: {BRAND_NAME}")
    print(f"字段顺序: brand | sku_id | name_en | name_cn | name_kr | name_jp")
    print(f"          price_cny | price_jp | price_kr (移除固定 to_cny，用汇率表实时换算)")
    print(f"          image | image_phash | image_match_confidence | category")
    print(f"          source_cn/jp/kr | store_cities")

    # 2. 商品/库存
    print("\n[1/4] 加载清理后商品数据...")
    products = load_clean_products()
    print("\n[2/4] 加载门店库存数据...")
    inventories = load_inventories()

    # 3. 构建整合
    print("\n[3/4] 构建统一商品数据库 + 图片比对...")
    unified, manual_review = build_unified(products, inventories, rates,
                                           skip_image=args.skip_image)

    # 4. 输出
    print("\n[4/4] 输出文件...")
    output_dir = DATA_ROOT / "aligned"
    output_dir.mkdir(parents=True, exist_ok=True)
    _save_jsonl(output_dir / "products_unified.jsonl", unified)
    _save_jsonl(output_dir / "image_manual_review.jsonl", manual_review)

    stats = generate_stats(unified, manual_review, rates, rates_upd)
    with open(output_dir / "alignment_stats.json", "w", encoding="utf-8") as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)

    print(f"\n{'='*60}")
    print(f"✅ 数据对齐 v3 完成")
    print(f"{'='*60}")
    print(f"整合数据库: products_unified.jsonl ({len(unified)} 条)")
    print(f"人工校验:   image_manual_review.jsonl ({len(manual_review)} 条)")
    print(f"统计文件:   alignment_stats.json")
    print(f"\n汇率: 使用 exchange_rates 表(基准CNY)，{rates_upd or '兜底'}")
    print(f"      JPY→CNY={rates.get('JPY','?')}, KRW→CNY={rates.get('KRW','?')}")
    print(f"      * price_jp_to_cny / price_kr_to_cny 字段已从整合表移除")
    print(f"      * 换算请调用 POST /api/exchange/convert")
    print(f"\n图片锚点: 相似度>=0.90 同图 / <0.70 不同图 / 中间 {len(manual_review)} 条需人工校验")
    print(f"\n覆盖统计:")
    for k, v in stats["coverage"].items():
        print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
