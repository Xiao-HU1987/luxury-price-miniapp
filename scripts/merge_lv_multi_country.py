"""将 LV 多国家官网爬虫抓取到的 JSONL 合并到小程序 products / price_stock

支持国家：JP（已存在）/ KR / CN / FR（法国·EUR）/ GB（英国·GBP）/ CH（瑞士·CHF）
        / DE, IT, ES（这三个也是 EUR，与 FR 同价，可选）

工作流程（以 KR 与 FR 为例）：
  1. 读入 data/cloud_import_products.jsonl（products 集合，JSON Lines）
  2. 读入 data/cloud_import_price_stock.jsonl（price_stock 集合）
  3. 读入 data/lv/{country}/products_{country}.jsonl（每个国家的爬虫产物）
  4. 读入 data/lv/{country}/inventories_{country}.jsonl（门店库存，KR 最常见）
  5. 按 sku_id/article_no 匹配（忽略大小写、去掉 spu-lv- 前缀）：
       - 命中 → 更新对应国家字段（如 krPrice / frCnyPrice / cnOfficialPrice）
       - 未命中 → 新增 product 条目（名称用当地语言或英文）
  6. 为每个 SKU 添加 price_stock 条目（官网渠道 + 门店库存）
  7. 重算 bestGlobalPrice / bestCountry / countryCount
  8. 输出 merged 文件（JSON Lines + 数组格式两种）

汇率默认值（近似中间价，可通过 --eur-rate / --gbp-rate / --chf-rate 覆盖）：
  1 CNY = 0.128 EUR  →  即 1 EUR = 7.81 CNY
  1 CNY = 0.109 GBP  →  即 1 GBP = 9.17 CNY
  1 CNY = 0.124 CHF  →  即 1 CHF = 8.06 CNY
  1 CNY = 192.5 KRW
  1 CNY = 21.58 JPY
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
LV_DIR = DATA_DIR / "lv"

# 汇率默认值：1 CNY 兑换的 X 外币金额。
# cny_of_one_local = 1 / rate ，即 1 单位外币 ≈ (1/rate) 人民币
DEFAULT_RATES: Dict[str, float] = {
    "JPY": 21.58,
    "KRW": 192.5,
    "CNY": 1.0,
    "EUR": 0.128,   # 1 CNY = 0.128 EUR
    "GBP": 0.109,   # 1 CNY = 0.109 GBP
    "CHF": 0.124,   # 1 CNY = 0.124 CHF
    "DKK": 0.955,   # 丹麦克朗（备用）
    "SEK": 1.37,    # 瑞典克朗（备用）
}

# 每个国家 → 币种、默认城市、官网渠道显示名称
COUNTRY_META: Dict[str, Dict[str, str]] = {
    "JP": {"currency": "JPY", "city": "东京",   "store_name": "日本官网"},
    "KR": {"currency": "KRW", "city": "首尔",   "store_name": "韩国官网"},
    "CN": {"currency": "CNY", "city": "全国",   "store_name": "中国大陆官网"},
    "FR": {"currency": "EUR", "city": "巴黎",   "store_name": "法国官网"},
    "GB": {"currency": "GBP", "city": "伦敦",   "store_name": "英国官网"},
    "CH": {"currency": "CHF", "city": "日内瓦", "store_name": "瑞士官网"},
    "DE": {"currency": "EUR", "city": "慕尼黑", "store_name": "德国官网"},
    "IT": {"currency": "EUR", "city": "米兰",   "store_name": "意大利官网"},
    "ES": {"currency": "EUR", "city": "马德里", "store_name": "西班牙官网"},
}

# products 集合上存储各国价格的字段（冗余字段，便于小程序直接展示）
#   国家代码 (小写) → (localPrice 字段, cnyPrice 字段)
COUNTRY_PRICE_FIELDS: Dict[str, Tuple[str, str]] = {
    "JP": ("jpPrice", "jpCnyPrice"),
    "KR": ("krPrice", "krCnyPrice"),
    "FR": ("frPrice", "frCnyPrice"),
    "GB": ("gbPrice", "gbCnyPrice"),
    "CH": ("chPrice", "chCnyPrice"),
    "DE": ("dePrice", "deCnyPrice"),
    "IT": ("itPrice", "itCnyPrice"),
    "ES": ("esPrice", "esCnyPrice"),
}
# CN 是个特例：使用 cnOfficialPrice（不叫 cnPrice）
COUNTRY_PRICE_FIELDS["CN"] = ("cnOfficialPrice", "cnCnyPrice")

BRAND_ID = "b001"
BRAND_NAME = "Louis Vuitton"
CATEGORY = "handbag"

ALL_COUNTRIES = list(COUNTRY_META.keys())


# ==================================================================
# I/O
# ==================================================================
def _read_jsonl(path: Path) -> List[Dict]:
    if not path.exists():
        print(f"[WARN] 文件不存在: {path}")
        return []
    arr = []
    with open(path, "r", encoding="utf-8") as f:
        for i, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                arr.append(json.loads(line))
            except Exception as e:
                print(f"[WARN] JSONL 解析失败 {path.name} 第 {i} 行: {e}")
    return arr


def _read_json_or_jsonl(path: Path) -> List[Dict]:
    if not path.exists():
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            return data
        return []
    except Exception:
        return _read_jsonl(path)


def _write_jsonl(path: Path, arr: List[Dict]):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for obj in arr:
            f.write(json.dumps(obj, ensure_ascii=False) + "\n")


def _write_json(path: Path, arr: List[Dict]):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(arr, f, ensure_ascii=False, indent=2)


# ==================================================================
# 工具
# ==================================================================
def _norm_sku(s: str) -> str:
    """归一化 SKU：去前缀、去短横线、小写。
    使得 "spu-lv-m2a099" / "M2A099" / "m2a-099" 都能匹配。"""
    if not s:
        return ""
    s = s.strip().lower()
    for prefix in ("spu-lv-", "sku-lv-"):
        if s.startswith(prefix):
            s = s[len(prefix):]
    s = s.replace("-", "").replace("_", "")
    return s


def _fmt_price(n: float) -> str:
    """格式化价格字符串：千分位。"""
    if not n:
        return ""
    try:
        return f"{int(round(n)):,}"
    except Exception:
        return ""


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")


def _is_bag_like(name: str = "", article_no: str = "", sku_ids: List[str] = None) -> bool:
    """弱判断是否是包包（避免把配饰/鞋等误入库）。"""
    if not name and not article_no:
        return False
    # article_no 格式判断：M/N/S/G + 数字/字母组合 (4-8 chars)，典型 LV 包包货号
    if article_no:
        s = article_no.strip().upper()
        if (len(s) in (5, 6, 7, 8)
                and s[0] in "MNSG"
                and s[1:].isalnum()):
            return True
    if sku_ids:
        for sid in sku_ids:
            s = sid.strip().upper()
            if (len(s) in (5, 6, 7, 8)
                    and s[0] in "MNSG"
                    and s[1:].isalnum()):
                return True
    # 通过名称关键词兜底（韩文/日文/英文/中文）
    NON_BAG_KEYS = [
        'card holder', 'key pouch', 'wallet', 'zippy', 'brazza', 'slender',
        'scarf', 'stole', 'shawl', 'belt', 'hat', 'cap', 'glove',
        'sneaker', 'shoe', 'boot', 'sandal', 'loafer',
        'jewelry', 'ring', 'necklace', 'earring', 'bracelet', 'bangle',
        'watch', 'timepiece',
        'shirt', 't-shirt', 'tshirt', 'jacket', 'coat', 'pant', 'jean',
        'dress', 'skirt', 'sweater', 'knit', 'hoodie',
        'perfume', 'fragrance', 'parfum', 'makeup', 'cosmetic', 'lipstick',
        'sunglass', 'glasses', 'eyewear',
        'umbrella', 'phone case', 'airpods', 'airpod',
        'notebook', 'agenda', 'planner', 'pen', 'book',
        'baby', 'pet', 'toy', 'blanket', 'pillow',
    ]
    text = f"{name} {' '.join(sku_ids or [])}".lower()
    for k in NON_BAG_KEYS:
        if k in text:
            return False
    return True


# ==================================================================
# 合并主逻辑
# ==================================================================
def merge(rates: Dict[str, float], only_countries: List[str] = None):
    """
    Args:
        rates:  货币 → 1 CNY 兑换的外币金额。如 {"JPY": 21.58, "KRW": 192.5, ...}
        only_countries: 只处理指定国家（如 ["KR", "CN", "FR"]）。None = 扫描 LV_DIR 下所有国家
    """
    products_path = DATA_DIR / "cloud_import_products.jsonl"
    ps_path = DATA_DIR / "cloud_import_price_stock.jsonl"

    print(f"[IN] products (基准): {products_path}")
    print(f"[IN] price_stock (基准): {ps_path}")
    print(f"[IN] 爬虫数据根目录: {LV_DIR}")
    print(f"[RATE] " + " / ".join(f"{k}={v}" for k, v in rates.items() if v))

    products = _read_jsonl(products_path)
    price_stock = _read_jsonl(ps_path)
    print(f"  - 基准 products: {len(products)}")
    print(f"  - 基准 price_stock: {len(price_stock)}")

    # ---------- 判定要处理哪些国家 ----------
    if only_countries is None:
        countries_found = []
        if LV_DIR.exists():
            for sub in LV_DIR.iterdir():
                if sub.is_dir() and sub.name in ALL_COUNTRIES:
                    # 存在 products 或 inventories 文件就算
                    prod_f = sub / f"products_{sub.name}.jsonl"
                    inv_f = sub / f"inventories_{sub.name}.jsonl"
                    if prod_f.exists() or inv_f.exists():
                        countries_found.append(sub.name)
        process_countries = countries_found or ["KR", "CN"]
    else:
        process_countries = [c for c in only_countries if c in ALL_COUNTRIES]

    print(f"[PROCESS] 国家列表: {process_countries}")

    # 各国产品/库存输入
    per_country: Dict[str, Dict[str, List[Dict]]] = {}
    for c in process_countries:
        prod_f = LV_DIR / c / f"products_{c}.jsonl"
        inv_f = LV_DIR / c / f"inventories_{c}.jsonl"
        prods = _read_jsonl(prod_f)
        invs = _read_jsonl(inv_f)
        per_country[c] = {"products": prods, "inventories": invs}
        print(f"  - {c}: products={len(prods)}  inventories={len(invs)}")

    # 构建索引：norm_sku → product
    prod_index: Dict[str, Dict[str, Any]] = {}
    for p in products:
        key = _norm_sku(p.get("productId") or p.get("sku_id") or "")
        if key:
            prod_index[key] = p

    # price_stock 去重键：(norm_product_id, countryCode, storeName)
    ps_keys = set()
    for ps in price_stock:
        k = (_norm_sku(ps.get("productId", "")),
             ps.get("countryCode", ""),
             (ps.get("storeInfo") or {}).get("storeName", ""))
        ps_keys.add(k)

    now = _now_iso()

    # ---------- 单国家处理函数 ----------
    def _process_country(items: List[Dict], country: str):
        added_products = 0
        updated_products = 0
        added_ps_entries = 0

        meta = COUNTRY_META[country]
        currency = meta["currency"]
        city_def = meta["city"]
        store_def = meta["store_name"]
        fx_to_cny = rates.get(currency, 0)  # 1 CNY = fx_to_cny 外币

        price_local_field, price_cny_field = COUNTRY_PRICE_FIELDS.get(
            country, (f"{country.lower()}Price", f"{country.lower()}CnyPrice")
        )

        for item in items:
            # 1. 提取 sku
            article_list = item.get("article_nos") or item.get("articleNos")
            if isinstance(article_list, list) and article_list:
                sku_id = article_list[0]
            else:
                sku_id = item.get("sku_id")
                if not sku_id and isinstance(item.get("sku_ids"), list):
                    sku_id = item["sku_ids"][0] if item["sku_ids"] else ""
            article_no = sku_id
            name_local = item.get("name_local") or ""
            names = item.get("names") or {}
            price = item.get("price") or 0
            images = item.get("images") or []
            main_image = images[0] if images else ""
            sku_ids = item.get("sku_ids") or []

            if not sku_id:
                continue
            if not _is_bag_like(name=name_local, article_no=article_no, sku_ids=sku_ids):
                continue
            if price <= 0 and not name_local:
                continue

            product_id = f"spu-lv-{sku_id.lower()}"
            cny_price = round(price / fx_to_cny) if (price and fx_to_cny) else 0
            norm_key = _norm_sku(sku_id)

            product = prod_index.get(norm_key)
            if product is None:
                # 新增 product
                added_products += 1
                product = {
                    "productId": product_id,
                    "slug": sku_id.lower(),
                    "nameCn": "",
                    "nameJp": "",
                    "nameEn": names.get("en") if isinstance(names, dict) else "",
                    "mainImage": main_image,
                    "images": images[:15],
                    "cnOfficialPrice": 0,
                    "hasCnPrice": False,
                    "jpPrice": 0,
                    "jpCnyPrice": 0,
                    "krPrice": 0,
                    "krCnyPrice": 0,
                    "cnyPrice": 0,
                    "bestGlobalPrice": 0,
                    "bestCountry": "",
                    "countryCount": 0,
                    "category": CATEGORY,
                    "brandId": BRAND_ID,
                    "brandName": BRAND_NAME,
                    "description": "",
                    "createTime": now,
                    "updateTime": now,
                }
                # 初始化其它国家价格字段（默认 0）
                for c2 in ALL_COUNTRIES:
                    if c2 in ("JP", "KR", "CN"):
                        continue
                    lf, cf = COUNTRY_PRICE_FIELDS[c2]
                    product.setdefault(lf, 0)
                    product.setdefault(cf, 0)
                # 名称补全
                if country == "KR":
                    product["_nameKr"] = name_local
                elif country == "CN":
                    product["nameCn"] = name_local
                elif country == "JP":
                    product["nameJp"] = name_local
                elif country in ("FR", "GB", "CH", "DE", "IT", "ES"):
                    # 欧洲语言的商品名，先塞 nameEn 或 _nameEU 备用
                    if isinstance(names, dict) and names.get("en"):
                        if not product["nameEn"]:
                            product["nameEn"] = names["en"]
                    product.setdefault("_nameLocal", name_local)
                products.append(product)
                prod_index[norm_key] = product
            else:
                updated_products += 1
                product["updateTime"] = now
                if main_image and not product.get("mainImage"):
                    product["mainImage"] = main_image
                if images:
                    merged_imgs = list(product.get("images") or [])
                    for im in images:
                        if im not in merged_imgs:
                            merged_imgs.append(im)
                    product["images"] = merged_imgs[:30]
                # 名称补全
                if country == "CN" and name_local and not product.get("nameCn"):
                    product["nameCn"] = name_local
                elif country == "KR" and name_local and "_nameKr" not in product:
                    product["_nameKr"] = name_local
                elif country == "JP" and name_local and not product.get("nameJp"):
                    product["nameJp"] = name_local

            # 写国家价格字段
            if price:
                product[price_local_field] = price
                product[price_cny_field] = cny_price
                if country == "CN":
                    product["hasCnPrice"] = True

            # price_stock（官网渠道）
            if price:
                ps_key = (_norm_sku(product["productId"]), country, store_def)
                if ps_key not in ps_keys:
                    price_stock.append({
                        "productId": product["productId"],
                        "countryCode": country,
                        "localPrice": price,
                        "currency": currency,
                        "cnyPrice": cny_price,
                        "stockStatus": "available",
                        "storeInfo": {"city": city_def, "storeName": store_def, "address": ""},
                        "priceUpdateTime": now,
                    })
                    ps_keys.add(ps_key)
                    added_ps_entries += 1
        return added_products, updated_products, added_ps_entries

    # ---------- 逐国处理 ----------
    total_add = total_upd = total_ps = 0
    for c in process_countries:
        items = per_country[c]["products"]
        if items:
            a, u, p = _process_country(items, c)
            print(f"[{c}] 新增产品={a}  更新产品={u}  新增官网价格行={p}")
            total_add += a; total_upd += u; total_ps += p

    # ---------- 处理各国门店库存 ----------
    total_inv_added = 0
    for c in process_countries:
        inv_list = per_country[c]["inventories"]
        if not inv_list:
            continue
        meta = COUNTRY_META[c]
        currency = meta["currency"]
        fx_to_cny = rates.get(currency, 0)
        added = 0

        local_field, cny_field = COUNTRY_PRICE_FIELDS[c]

        for inv in inv_list:
            sku_id = inv.get("sku_id") or inv.get("article_no") or ""
            if not sku_id:
                continue
            norm_key = _norm_sku(sku_id)
            prod = prod_index.get(norm_key)
            if not prod:
                continue
            store_name = inv.get("storeName") or (inv.get("storeInfo") or {}).get("storeName") or ""
            city = inv.get("city") or (inv.get("storeInfo") or {}).get("city") or ""
            if not store_name:
                continue
            status = inv.get("stockStatus") or inv.get("availability") or inv.get("status") or "inquired"
            if isinstance(status, str):
                s = status.lower()
                if s in ("in_stock", "instock", "in stock", "available", "true", "有货",
                         "재고있음", "판매중", "disponible", "auf lager", "en stock"):
                    status = "available"
                elif s in ("out_of_stock", "oos", "soldout", "sold out", "none", "false",
                           "无货", "품절", "épuisé", "ausverkauft", "agotado", "sold out"):
                    status = "oos"
                else:
                    status = "inquired"
            ps_key = (_norm_sku(prod["productId"]), c, store_name)
            if ps_key in ps_keys:
                continue
            local_price = inv.get("localPrice") or prod.get(local_field, 0) or 0
            cny_price_val = round(local_price / fx_to_cny) if (local_price and fx_to_cny) else prod.get(cny_field, 0)
            price_stock.append({
                "productId": prod["productId"],
                "countryCode": c,
                "localPrice": local_price,
                "currency": currency,
                "cnyPrice": cny_price_val,
                "stockStatus": status,
                "storeInfo": {
                    "city": city,
                    "storeName": store_name,
                    "address": inv.get("address") or (inv.get("storeInfo") or {}).get("address") or "",
                },
                "priceUpdateTime": inv.get("crawled_at") or now,
            })
            ps_keys.add(ps_key)
            added += 1
        print(f"[{c}-INV] 新增门店库存行: {added}")
        total_inv_added += added

    # ---------- 重算 bestGlobalPrice / bestCountry / countryCount ----------
    for p in products:
        country_set = set()
        best = 0
        best_country = ""
        # 遍历所有国家
        for c2 in ALL_COUNTRIES:
            lf, cf = COUNTRY_PRICE_FIELDS[c2]
            if c2 == "CN":
                val = p.get(lf) or 0
                cny_ref = val
            else:
                cny_ref = p.get(cf) or 0
                val = p.get(lf) or 0
            if not val:
                continue
            country_set.add(c2)
            # 以人民币口径比较
            compare_val = cny_ref if cny_ref else (val / rates.get(COUNTRY_META[c2]["currency"], 1) if val and COUNTRY_META[c2]["currency"] in rates else 0)
            if compare_val and (best == 0 or compare_val < best):
                best = compare_val
                best_country = c2
        p["countryCount"] = len(country_set)
        p["bestGlobalPrice"] = best
        p["bestCountry"] = best_country
        p["cnyPrice"] = p.get("jpCnyPrice") or best
        p["updateTime"] = now

    # ---------- 输出 ----------
    merged_prod_jsonl = DATA_DIR / "cloud_import_products.merged.jsonl"
    merged_ps_jsonl = DATA_DIR / "cloud_import_price_stock.merged.jsonl"
    merged_prod_json = DATA_DIR / "import_products.merged.json"
    merged_ps_json = DATA_DIR / "import_price_stock.merged.json"

    _write_jsonl(merged_prod_jsonl, products)
    _write_jsonl(merged_ps_jsonl, price_stock)
    _write_json(merged_prod_json, products)
    _write_json(merged_ps_json, price_stock)

    print()
    print("============= 合并完成 =============")
    print(f"[统计] 总产品数: {len(products)}  (新增 {total_add}, 更新 {total_upd})")
    print(f"[统计] 总 price_stock 行数: {len(price_stock)}  (新增官网渠道 {total_ps} + 门店库存 {total_inv_added})")
    for c in ["JP", "KR", "CN", "FR", "GB", "CH"]:
        lf, _ = COUNTRY_PRICE_FIELDS[c]
        n = sum(1 for p in products if p.get(lf))
        print(f"[统计]   {c} 价格已填充产品数: {n}")
    n_multi = sum(1 for p in products if p.get("countryCount", 0) >= 2)
    print(f"[统计] 有 >=2 个国家比价的产品数: {n_multi}")
    print()
    print("[输出] 云数据库导入（JSON Lines）→ 微信云开发控制台 → 数据库 → 导入（覆盖原集合）")
    print(f"  1) products 集合:     {merged_prod_jsonl}")
    print(f"  2) price_stock 集合:  {merged_ps_jsonl}")
    print()
    print("[输出] 数组格式（备份 / 脚本再处理用）:")
    print(f"  1) {merged_prod_json}")
    print(f"  2) {merged_ps_json}")


def main():
    ap = argparse.ArgumentParser(
        description="合并 LV 多国家（KR/CN/FR/GB/CH/DE/IT/ES）爬虫数据到 products / price_stock"
    )
    ap.add_argument("--countries", default="",
                    help="只处理指定国家，逗号分隔。如 KR,CN,FR。留空=自动扫描 data/lv/ 下存在的国家。")
    # 各国汇率 CLI 覆盖（1 CNY = X 外币）
    for cur, default in DEFAULT_RATES.items():
        ap.add_argument(f"--{cur.lower()}-rate", type=float, default=default,
                        help=f"1 CNY = ? {cur}，默认 {default}")
    args = ap.parse_args()

    # 收集 rates
    rates: Dict[str, float] = {}
    for cur in DEFAULT_RATES:
        rates[cur] = getattr(args, f"{cur.lower()}_rate", DEFAULT_RATES[cur])

    only = None
    if args.countries:
        only = [c.strip().upper() for c in args.countries.split(",") if c.strip()]

    merge(rates, only_countries=only)


if __name__ == "__main__":
    main()

