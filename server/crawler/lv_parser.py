"""JSON 响应解析器

目标：从 Playwright 拦截到的 JSON body 中提取商品列表 / 详情 / 库存数据。

策略：
1. 先用宽松的结构检测判断响应是否可能是「商品列表 / 商品详情 / 库存」
2. 找到候选容器后，按 LV 常见字段名（英、日）递归取值
3. 提取失败时，返回空列表，调用方决定是否落盘到 raw_captures/

字段映射候选（基于 LV 多区域站点经验值，可能与实际不完全一致）：
- 名称:    title / name / productName / displayName / product_name
- 型号:    sku / skuId / reference / articleNumber / LVReference / M{..}
- 价格:    price / amount / value / sellingPrice / listPrice / priceValue
- 货币:    currency / currencyCode
- 图片:    image / imageUrl / thumbnail / picture / mainImage
- 库存:    inStock / stock / available / availability
- 库存原文: stockStatus / availabilityLabel / stockLabel
- 材质:    material / composition / materialDescription
- 门店:    storeName / store_name / boutiqueName
- 门店地址: address / storeAddress / fullAddress
"""
from __future__ import annotations

import re
from typing import Any, Dict, Iterable, List, Optional, Tuple


# ==================== 通用取值工具 ====================

def _dig(obj: Any, *keys: str) -> Optional[Any]:
    """在嵌套 dict/list 中按多个候选 key 顺序取值（fallback 语义）。

    对每个 key：尝试 obj["key"]（或 obj 中下个 dict/list 项的对应 key）。
    一旦命中即返回，不会继续尝试后续 key。
    """
    for key in keys:
        if obj is None:
            return None
        if isinstance(obj, dict):
            if key in obj:
                return obj[key]
            # 不区分大小写
            lower_map = {k.lower(): k for k in obj.keys() if isinstance(k, str)}
            real_key = lower_map.get(key.lower())
            if real_key:
                return obj[real_key]
        elif isinstance(obj, list):
            # 列表里逐项递归
            for item in obj:
                result = _dig(item, key)
                if result is not None:
                    return result
    return None


def _to_str(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    return str(value).strip()


def _to_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        # 处理 "¥493,900" / "493,900" / "493.900" / "493900"
        cleaned = re.sub(r"[^\d.]", "", value)
        if not cleaned:
            return None
        try:
            return float(cleaned)
        except ValueError:
            return None
    if isinstance(value, dict):
        # 嵌套 price 对象: {"value": 493900, "currencyCode": "JPY"}
        # 或 {"amount": {"value": ...}}
        for path in (
            ("value",),
            ("amount",),
            ("price",),
            ("sellingPrice",),
            ("listPrice",),
            ("priceIncludingTaxes",),
            ("priceIncludingTax",),
            ("amount", "value"),
            ("amount", "amount"),
            ("price", "value"),
        ):
            nested = _dig(value, *path)
            if nested is not None:
                f = _to_float(nested)
                if f is not None:
                    return f
    return None


def _to_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value > 0
    if isinstance(value, str):
        v = value.strip().lower()
        if v in ("true", "1", "yes", "在庫あり", "available", "in_stock", "instock"):
            return True
        if v in ("false", "0", "no", "在庫なし", "unavailable", "out_of_stock", "outofstock", "在庫僅少"):
            return False
    return False


# ==================== 结构检测 ====================

def looks_like_product_data(payload: Any, url: str) -> bool:
    """粗判 payload 是否包含商品信息。"""
    if not isinstance(payload, (dict, list)):
        return False
    blob = str(payload).lower()
    hint_keywords = (
        "product", "sku", "price", "title", "article",
        "stock", "inventory", "availability", "thumbnail",
    )
    return any(k in blob for k in hint_keywords)


def is_lv_response(url: str, allowlist: Iterable[str] | None = None) -> bool:
    if allowlist is None:
        allowlist = ["louisvuitton.com", "api.louisvuitton.com"]
    return any(domain in url for domain in allowlist)


def is_target_url(url: str, keywords: Iterable[str]) -> bool:
    lower = url.lower()
    return any(kw.lower() in lower for kw in keywords)


# ==================== 容器识别 ====================

def _find_product_list(payload: Any) -> Optional[List[Dict[str, Any]]]:
    """尝试在 payload 中找到形如 [{...商品}, ...] 的列表。"""
    # 常见容器键
    container_keys = (
        "products", "items", "results", "data", "hits",
        "plpProducts", "productList", "product_list",
        "catalogProducts", "entries",
    )
    if isinstance(payload, list) and payload and isinstance(payload[0], dict):
        if looks_like_product_data(payload[0], ""):
            return payload
    if isinstance(payload, dict):
        for key in container_keys:
            container = payload.get(key)
            if isinstance(container, list) and container:
                if isinstance(container[0], dict) and looks_like_product_data(container[0], ""):
                    return container
                # 即便首个元素不像商品，整个列表仍然可能有效，留给调用方
                if all(isinstance(x, dict) for x in container):
                    return container
        # 嵌套：{"data": {"products": [...]}}
        for outer_key in ("data", "payload", "result", "response"):
            inner = payload.get(outer_key)
            if isinstance(inner, dict):
                nested = _find_product_list(inner)
                if nested:
                    return nested
    return None


def _find_first_product(payload: Any) -> Optional[Dict[str, Any]]:
    """从 payload 中找到第一个看起来像商品字典的对象。"""
    if isinstance(payload, dict):
        # 形如 {"product": {...}} / {"item": {...}}
        for key in ("product", "item", "data", "result", "response", "payload"):
            inner = payload.get(key)
            if isinstance(inner, dict) and looks_like_product_data(inner, ""):
                return inner
        # 形如 {"products": [{...}]}
        for key in ("products", "items", "results", "hits"):
            arr = payload.get(key)
            if isinstance(arr, list) and arr and isinstance(arr[0], dict):
                return arr[0]
        # 形如 {"LV": {...}} 嵌套
        for value in payload.values():
            if isinstance(value, dict) and looks_like_product_data(value, ""):
                # 进一步递归一层
                deeper = _find_first_product(value)
                if deeper:
                    return deeper
    elif isinstance(payload, list) and payload and isinstance(payload[0], dict):
        return payload[0]
    return None


# ==================== 字段提取 ====================

def _extract_attributes(raw: Dict[str, Any]) -> Dict[str, str]:
    """从 LV 的 attributes 数组提取 {name: value} 字典。

    LV 实际格式: [{"name": "color", "value": "Monogram"}, ...]
    同时也支持扁平化字段。
    """
    attrs: Dict[str, str] = {}
    # 1. 优先处理 attributes 数组
    attr_list = _dig(raw, "attributes", "attribute", "specifications",
                     "specs", "properties")
    if isinstance(attr_list, list):
        for a in attr_list:
            if isinstance(a, dict):
                name = _to_str(_dig(a, "name", "key", "label", "type", "id"))
                value = _to_str(_dig(a, "value", "val", "text", "label"))
                if name and value:
                    attrs[name.lower()] = value
    # 2. 扁平化字段补充
    for field in ("color", "size", "material", "model", "modelNo",
                  "model_no", "reference"):
        v = _to_str(_dig(raw, field))
        if v and field.lower() not in attrs:
            attrs[field.lower()] = v
    return attrs


def extract_listing_items(payload: Any) -> List[Dict[str, Any]]:
    """从商品列表响应中提取 [{name, sku, price, image, url}, ...]"""
    items = _find_product_list(payload) or []
    result = []
    for raw in items:
        if not isinstance(raw, dict):
            continue
        price_raw = _dig(raw, "price", "amount", "value",
                         "sellingPrice", "listPrice", "priceValue",
                         "priceRaw", "price_raw")
        currency_raw = _dig(raw, "currency", "currencyCode", "currency_code")
        if isinstance(price_raw, dict) and not currency_raw:
            currency_raw = _dig(price_raw, "currencyCode", "currency",
                                 "currency_code")
        attrs = _extract_attributes(raw)

        # 图片：尝试多种来源，过滤广告链接
        image_candidates = []
        for key in ("image", "imageUrl", "image_url", "thumbnail",
                    "thumbnailUrl", "picture", "mainImage", "mediaUrl"):
            val = _to_str(_dig(raw, key))
            if val:
                image_candidates.append(val)
        # 尝试 medias 列表
        medias = _dig(raw, "medias", "images", "pictures", "media")
        if isinstance(medias, list):
            for m in medias:
                if isinstance(m, dict):
                    url = _to_str(_dig(m, "url", "src", "imageUrl"))
                    if url:
                        image_candidates.append(url)
                elif isinstance(m, str):
                    image_candidates.append(m)
        # 选第一张有效图片
        image = ""
        for img in image_candidates:
            if _is_valid_product_image(img):
                image = img
                break
        if not image and image_candidates:
            # 没有有效图片的话，就用第一张（即使可能是广告）
            image = image_candidates[0]

        sku_val = _to_str(_dig(raw, "sku", "skuId", "sku_id",
                                "productId", "product_id", "id"))
        article_val = _to_str(_dig(raw, "articleNumber", "article_number",
                                    "reference", "LVReference", "modelNumber",
                                    "skuId", "sku"))
        item = {
            "name": _to_str(_dig(raw, "title", "name", "productName",
                                "displayName", "product_name")),
            "sku": sku_val,
            "article_no": article_val,
            "price": _to_float(price_raw),
            "currency": _to_str(currency_raw) or "JPY",
            "image": image,
            "images": [img for img in image_candidates if _is_valid_product_image(img)],
            "url": _to_str(_dig(raw, "url", "link", "productUrl", "product_url",
                                "slug", "canonicalUrl")),
            "material": attrs.get("material", ""),
            "color": attrs.get("color", ""),
            "size": attrs.get("size", ""),
        }
        # 过滤掉空对象
        if item["name"] or item["sku"] or item["article_no"]:
            result.append(item)
    return result


def _is_valid_product_image(url: str) -> bool:
    """判断是否为真实商品图片（过滤广告/跟踪链接）。"""
    if not url:
        return False
    lower = url.lower()
    # 广告/跟踪域名黑名单
    bad_domains = [
        "teads.tv", "mpulse.net", "linkedin.com", "doubleclick.net",
        "googletagservices.com", "google-analytics.com", "adservice",
        "track", "pixel", "beacon", "collect",
    ]
    if any(d in lower for d in bad_domains):
        return False
    # LV 真实商品图片特征
    if "louisvuitton.com" in lower and "/images/is/image/lv/" in lower:
        return True
    if lower.startswith("/images/is/image/lv/"):
        return True
    # 其他合理的商品图片（相对路径或 CDN 域名）
    if lower.endswith((".jpg", ".jpeg", ".png", ".webp")) and not any(d in lower for d in bad_domains):
        return True
    return False


def extract_product_detail(payload: Any) -> Optional[Dict[str, Any]]:
    """从商品详情响应中提取单个商品的完整信息。"""
    raw = _find_first_product(payload)
    if not raw:
        return None

    # 图片列表（可能是 dict 或 list）
    # LV SKU API 用 medias，其他接口可能用 images/pictures/media 等
    image_candidates = _dig(raw, "images", "pictures", "media", "gallery",
                            "imageList", "image_list", "assets", "medias")
    images: List[str] = []
    # 单独处理 mediaUrl（主图）
    media_url = _to_str(_dig(raw, "mediaUrl", "mainImage", "imageUrl", "image_url"))
    if media_url and _is_valid_product_image(media_url):
        images.append(media_url)

    if isinstance(image_candidates, list):
        for img in image_candidates:
            if isinstance(img, str):
                if _is_valid_product_image(img):
                    images.append(img)
            elif isinstance(img, dict):
                url = _to_str(_dig(img, "url", "src", "imageUrl", "image_url",
                                    "path", "href"))
                if url and _is_valid_product_image(url):
                    images.append(url)
    elif isinstance(image_candidates, dict):
        # 形如 {"main": "...", "alternate": ["..."]}
        for v in image_candidates.values():
            if isinstance(v, str):
                if _is_valid_product_image(v):
                    images.append(v)
            elif isinstance(v, list):
                for x in v:
                    if isinstance(x, str):
                        if _is_valid_product_image(x):
                            images.append(x)
                    elif isinstance(x, dict):
                        url = _to_str(_dig(x, "url", "src", "imageUrl", "image_url"))
                        if url and _is_valid_product_image(url):
                            images.append(url)

    # 去重
    seen_imgs = set()
    unique_images = []
    for img in images:
        if img not in seen_imgs:
            seen_imgs.add(img)
            unique_images.append(img)
    images = unique_images

    # 价格：增加 priceRaw（LV SKU API 用）
    price_raw = _dig(raw, "price", "amount", "value",
                     "sellingPrice", "listPrice", "priceValue",
                     "priceIncludingTax", "priceIncludingTaxes",
                     "priceRaw", "price_raw")
    currency_raw = _dig(raw, "currency", "currencyCode", "currency_code")
    if isinstance(price_raw, dict) and not currency_raw:
        currency_raw = _dig(price_raw, "currencyCode", "currency",
                             "currency_code")

    attrs = _extract_attributes(raw)
    # SKU ID 优先用 skuId（LV API 标准字段）
    sku_val = _to_str(_dig(raw, "sku", "skuId", "sku_id", "id",
                            "productId", "product_id"))
    article_val = _to_str(_dig(raw, "articleNumber", "article_number",
                                "reference", "LVReference", "modelNumber",
                                "skuId", "sku"))
    detail = {
        "name": _to_str(_dig(raw, "title", "name", "productName",
                              "displayName", "longName", "product_name")),
        "sku": sku_val,
        "article_no": article_val,
        "price": _to_float(price_raw),
        "currency": _to_str(currency_raw) or "JPY",
        "material": attrs.get("material", "") or _to_str(
            _dig(raw, "material", "composition",
                 "materialDescription", "madeOf")),
        "description": _to_str(_dig(raw, "description", "longDescription",
                                     "shortDescription", "details")),
        "color": attrs.get("color", "") or _to_str(
            _dig(raw, "color", "colorName", "colorDescription")),
        "size": attrs.get("size", "") or _to_str(
            _dig(raw, "size", "dimensions", "dimension")),
        "images": images,
        "url": _to_str(_dig(raw, "url", "link", "productUrl", "product_url",
                            "slug", "canonicalUrl")),
    }
    if not any([detail["name"], detail["sku"], detail["article_no"]]):
        return None
    return detail


def extract_inventory_items(payload: Any) -> List[Dict[str, Any]]:
    """从库存响应中提取 [{store_name, store_address, in_stock, stock_status, sku}, ...]"""
    # 库存响应容器
    items: List[Dict[str, Any]] = []

    # 形如 { sku: "...", stocks: [{...}, ...] } 或 stores: [{...}, ...]
    sku_guess = _to_str(_dig(payload, "sku", "skuId", "sku_id", "productId",
                              "product_id", "articleNumber"))

    candidate_lists: List[List[Any]] = []
    for key in ("inventory", "inventories", "stocks", "stock", "availability",
                "stores", "boutiques", "storeList", "store_list",
                "results", "items", "data"):
        v = _dig(payload, key)
        if isinstance(v, list):
            candidate_lists.append(v)
        elif isinstance(v, dict):
            # 字典包列表
            for sub in v.values():
                if isinstance(sub, list):
                    candidate_lists.append(sub)

    # 如果 payload 本身就是 list
    if isinstance(payload, list):
        candidate_lists.append(payload)

    seen_keys = set()
    for cand_list in candidate_lists:
        for raw in cand_list:
            if not isinstance(raw, dict):
                # 字符串形式的库存状态
                if isinstance(raw, str):
                    items.append({
                        "sku": sku_guess,
                        "store_id": "",
                        "store_name": "",
                        "store_address": "",
                        "store_city": "",
                        "in_stock": _to_bool(raw),
                        "stock_status": raw,
                    })
                continue
            store_id = _to_str(_dig(raw, "storeId", "store_id", "id",
                                     "boutiqueId", "boutique_id"))
            store_name = _to_str(_dig(raw, "storeName", "store_name",
                                       "boutiqueName", "name", "title"))
            # 同 store_id + store_name 去重
            dedup_key = (store_id, store_name)
            if dedup_key in seen_keys:
                continue
            seen_keys.add(dedup_key)

            item = {
                "sku": sku_guess or _to_str(_dig(raw, "sku", "skuId", "sku_id",
                                                    "articleNumber")),
                "store_id": store_id,
                "store_name": store_name,
                "store_address": _to_str(_dig(raw, "address", "storeAddress",
                                                "store_address", "fullAddress",
                                                "formattedAddress")),
                "store_city": _to_str(_dig(raw, "city", "storeCity", "store_city",
                                            "locality")),
                "in_stock": _to_bool(_dig(raw, "inStock", "in_stock", "available",
                                            "isAvailable", "stock", "status")),
                "stock_status": _to_str(_dig(raw, "stockStatus", "stock_status",
                                                "availabilityLabel", "status",
                                                "stockLabel", "available")),
            }
            if item["store_name"] or item["store_id"]:
                items.append(item)
    return items


# ==================== 一站式分发 ====================

def parse_response(url: str, payload: Any) -> Dict[str, List[Dict[str, Any]]]:
    """根据 URL 关键词判断响应类型，调用对应解析器。

    Returns:
        {
          "listings": [...],
          "details": [...],
          "inventories": [...],
        }
    """
    result = {"listings": [], "details": [], "inventories": []}
    lower = url.lower()

    if any(k in lower for k in ("plp", "searchresult", "search-result",
                                  "catalog/list", "category", "listing",
                                  "products/list", "search", "catalog")):
        result["listings"] = extract_listing_items(payload)
    elif any(k in lower for k in ("pdp", "/product", "detail", "sku/",
                                    "/article")):
        # 优先按详情解析
        detail = extract_product_detail(payload)
        if detail:
            result["details"].append(detail)
        # 同一响应中也可能含库存
        result["inventories"].extend(extract_inventory_items(payload))
    elif any(k in lower for k in ("stock", "inventory", "availability", "store")):
        result["inventories"] = extract_inventory_items(payload)
    else:
        # 通用尝试
        listings = extract_listing_items(payload)
        if listings:
            result["listings"] = listings
        else:
            detail = extract_product_detail(payload)
            if detail:
                result["details"].append(detail)
            invs = extract_inventory_items(payload)
            if invs:
                result["inventories"] = invs
    return result
