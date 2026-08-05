"""数据库写入器

将解析后的商品 / 详情 / 库存数据 upsert 到现有数据模型：
- SPU: 一级商品（LV 用 article_no 作为业务主键）
- SKU: 商品下的具体规格（颜色/尺码等变体）
- SKUPrice: 不同国家的价格（LV Japan → JP/JPY）
- LvInventory: 各门店的库存状态（新增表）

设计：
- 所有 upsert 按业务唯一键查询：spu_id、sku_id、(sku_id, country)
- 已存在则更新（价格/库存/门店刷新），不存在则新增
- 失败的单条记录不会中断整体抓取
"""
from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from config import DEBUG
from models import Brand, Category, SPU, SKU, SKUPrice
from models.lv import LvInventory
from crawler.config import (
    LV_BRAND_ID,
    LV_BRAND_NAME,
    LV_BRAND_NAME_CN,
    LV_COUNTRY,
    LV_CURRENCY,
    LV_DEFAULT_CATEGORY_ID,
)
from crawler.translator import translate_batch

logger = logging.getLogger("lv_crawler")


# ==================== 工具 ====================

def _spu_id_from_article(article_no: str) -> str:
    """以 LV 货号 (如 M2A454) 作为 SPU 业务主键，加前缀避免与其他品牌冲突。"""
    if not article_no:
        return ""
    return f"spu-lv-{article_no.strip().lower()}"


def _sku_id(spu_id: str, raw_sku: str, color: str, size: str,
            article_no: str = "") -> str:
    """生成稳定的 SKU 业务主键。

    优先级：
    1. raw_sku（API 返回的 skuId，如 M2A099）
    2. article_no（货号，从 SPU 中提取）
    3. 退化方案：spu_id + color + size
    """
    if raw_sku:
        cleaned = raw_sku.strip().lower()
        if cleaned and cleaned not in ("default", ""):
            return f"sku-lv-{cleaned}"
    if article_no:
        cleaned = article_no.strip().lower()
        if cleaned:
            return f"sku-lv-{cleaned}"
    # 退化方案：用 spu_id + 颜色 + 尺寸 拼接
    parts = [spu_id, color or "default", size or "default"]
    slug = "-".join(p.strip().lower().replace(" ", "-") for p in parts if p)
    return f"sku-lv-{re.sub(r'[^a-z0-9-]', '', slug)}"


def _ensure_brand(db: Session) -> bool:
    """确保 LV 品牌记录存在，返回是否需要新增。"""
    existing = db.query(Brand).filter(Brand.brand_id == LV_BRAND_ID).first()
    if existing:
        return False
    db.add(Brand(
        brand_id=LV_BRAND_ID,
        name=LV_BRAND_NAME,
        name_cn=LV_BRAND_NAME_CN,
        logo="",
        category="luxury",
    ))
    return True


def _ensure_category(db: Session, category_id: str, name: str) -> bool:
    existing = db.query(Category).filter(Category.category_id == category_id).first()
    if existing:
        return False
    db.add(Category(category_id=category_id, name=name, icon=""))
    return True


# ==================== 单条 upsert ====================

def _is_bad_image_url(url: str) -> bool:
    """判断是否为无效/广告图片URL。"""
    if not url:
        return True
    lower = url.lower()
    bad_patterns = [
        "teads.tv", "mpulse.net", "linkedin.com", "doubleclick.net",
        "googletagservices", "google-analytics", "adservice",
        "track?", "pixel", "beacon", "collect?",
        "/error/", "404.jpg", "maintenance_page",
        "example.com",
    ]
    return any(p in lower for p in bad_patterns)


def _is_lv_product_image(url: str) -> bool:
    """判断是否为有效的LV官方产品图片。"""
    if not url or _is_bad_image_url(url):
        return False
    lower = url.lower()
    if "louisvuitton.com" not in lower:
        return False
    if "/images/is/image/lv/" in lower:
        return True
    if "/images/" in lower and any(ext in lower for ext in ('.jpg', '.jpeg', '.png', '.webp')):
        return True
    return False


# 无意义的名称黑名单（DOM 提取时可能误抓到的页脚/导航文字）
_BAD_NAMES = {
    "ヘルプ", "帮助", "メニュー", "検索", "すべて", "ホーム",
    "アクセス拒否", "access denied", "error", "エラー",
    "无法访问此网站", "ページが見つかりません",
}


def _is_valid_name(name: str) -> bool:
    """判断抓取到的商品名称是否合理。"""
    if not name or not name.strip():
        return False
    name = name.strip()
    # 黑名单直接拒绝
    if name.lower() in {n.lower() for n in _BAD_NAMES}:
        return False
    # 太短的名称（少于2个字符）可能是误抓
    if len(name) < 2:
        return False
    # 太长的名称（超过200字符）可能是误抓了整段文字
    if len(name) > 200:
        return False
    # 包含明显的导航/页脚关键词
    if any(kw in name for kw in ["メインコンテンツへスキップ", "ウィッシュリスト", "ショッピングバッグ"]):
        return False
    return True


def _is_valid_description(desc: str) -> bool:
    """判断抓取到的描述是否合理。"""
    if not desc or not desc.strip():
        return False
    desc = desc.strip()
    # 太短的描述
    if len(desc) < 10:
        return False
    # 包含明显的导航/页脚关键词
    if any(kw in desc for kw in ["メインコンテンツへスキップ", "ショッピングバッグに追加"]):
        return False
    return True


def _pick_best_image(images: List[str]) -> str:
    """从图片列表中选一张最好的（LV 官方图优先）。"""
    if not images:
        return ""
    # 优先选 LV 官方图片
    for img in images:
        if img and "louisvuitton.com" in img and "/images/is/image/lv/" in img:
            return img
    # 其次选非广告的 jpg/png
    for img in images:
        if img and not _is_bad_image_url(img):
            return img
    # 最后返回第一张（即使是坏的）
    return images[0] if images else ""


def upsert_spu(db: Session, detail: Dict[str, Any],
               translations: Optional[Dict[str, str]] = None) -> Optional[SPU]:
    """upsert SPU。返回实例（新增或更新）。

    translations 参数为预翻译结果，避免重复调用翻译 API。
    """
    article_no = (detail.get("article_no") or "").strip()
    if not article_no:
        # 退化：用 name + 随机后缀
        name = (detail.get("name") or "").strip()
        if not name:
            return None
        article_no = re.sub(r"\s+", "-", name)[:32]

    spu_id = _spu_id_from_article(article_no)
    spu = db.query(SPU).filter(SPU.spu_id == spu_id).first()

    # 翻译
    name_cn = ""
    desc_cn = ""
    if translations:
        name_cn = translations.get(detail.get("name", ""), "")
        desc_cn = translations.get(detail.get("description", ""), "")

    now = datetime.now(timezone.utc)

    # 收集所有图片候选并去重
    all_images: List[str] = []
    seen_img = set()
    for img_list in (detail.get("images") or [], [detail.get("image", "")]):
        if isinstance(img_list, list):
            for img in img_list:
                if img and img not in seen_img:
                    seen_img.add(img)
                    all_images.append(img)
        elif isinstance(img_list, str) and img_list and img_list not in seen_img:
            seen_img.add(img_list)
            all_images.append(img_list)

    # 过滤掉坏图片，只保留有效图片
    valid_images = [img for img in all_images if not _is_bad_image_url(img)]
    best_image = _pick_best_image(valid_images) if valid_images else ""
    images_json = ""
    if valid_images:
        import json as _json
        images_json = _json.dumps(valid_images[:20], ensure_ascii=False)

    if not spu:
        spu = SPU(
            spu_id=spu_id,
            brand_id=LV_BRAND_ID,
            brand_name=LV_BRAND_NAME_CN,
            name=detail.get("name") or article_no,
            name_cn=name_cn,
            name_en="",
            article_no=article_no,
            category_id=detail.get("category_id") or LV_DEFAULT_CATEGORY_ID,
            image=best_image or (all_images[0] if all_images else ""),
            images=images_json,
            description=detail.get("description", "") or detail.get("material", ""),
            description_cn=desc_cn,
            translate_status="translated" if name_cn else "pending",
            translated_at=now if name_cn else None,
            source_url=detail.get("url", ""),
        )
        db.add(spu)
    else:
        # 更新可变字段
        # 名称：只在合理时才覆盖（防止抓到页脚的"ヘルプ"等无意义内容）
        new_name = detail.get("name", "")
        if new_name and _is_valid_name(new_name):
            spu.name = new_name
        # 描述：只在合理时才覆盖
        new_desc = detail.get("description", "")
        if new_desc and _is_valid_description(new_desc):
            spu.description = new_desc
        if detail.get("url") and not spu.source_url:
            spu.source_url = detail["url"]

        # 图片更新策略：
        # 1. 新图是LV产品图 && 旧图不是 → 必更新
        # 2. 旧图是坏图 → 必更新
        # 3. 旧图为空 → 必更新
        new_is_lv = _is_lv_product_image(best_image) if best_image else False
        old_is_lv = _is_lv_product_image(spu.image or "")
        old_is_bad = _is_bad_image_url(spu.image or "")
        should_update_image = False
        if best_image:
            if not spu.image or old_is_bad:
                should_update_image = True
            elif new_is_lv and not old_is_lv:
                should_update_image = True
        if should_update_image:
            spu.image = best_image
        # 多图：新图是LV产品图或旧图为空/坏图时更新
        if images_json:
            old_img_bad = _is_bad_image_url(spu.image or "")
            should_update_images = (
                not spu.images
                or old_img_bad
                or (new_is_lv and not old_is_lv)
            )
            if should_update_images:
                spu.images = images_json

        # 翻译字段：已校对(approved)的不覆盖，否则更新翻译
        if spu.translate_status != "approved":
            if name_cn:
                spu.name_cn = name_cn
            if desc_cn:
                spu.description_cn = desc_cn
            if name_cn or desc_cn:
                spu.translate_status = "translated"
                spu.translated_at = now
    return spu


def upsert_sku(db: Session, detail: Dict[str, Any], spu_id: str,
               translations: Optional[Dict[str, str]] = None) -> Optional[SKU]:
    """upsert SKU（默认一条/商品，color/size 取自详情）。

    如果之前有 default 退化 SKU，且现在有了真实 SKU ID，则迁移旧数据并更新。
    """
    article_no = detail.get("article_no", "")
    new_sku_id = _sku_id(spu_id, detail.get("sku", ""),
                         detail.get("color", ""), detail.get("size", ""),
                         article_no=article_no)

    # 检查是否需要从旧的 default SKU 迁移
    old_sku_id_default = _sku_id(spu_id, "", "", "", article_no="")
    old_sku = None
    new_sku = db.query(SKU).filter(SKU.sku_id == new_sku_id).first()

    if not new_sku and new_sku_id != old_sku_id_default:
        # 尝试找旧的退化 SKU，迁移数据
        old_sku = db.query(SKU).filter(
            SKU.spu_id == spu_id,
            SKU.sku_id.like("sku-lv-%-default%"),
        ).first()
        if old_sku:
            old_sku.sku_id = new_sku_id
            new_sku = old_sku
            db.flush()

    color_cn = ""
    if translations:
        color_cn = translations.get(detail.get("color", ""), "")

    if not new_sku:
        new_sku = SKU(
            sku_id=new_sku_id,
            spu_id=spu_id,
            name=detail.get("name") or new_sku_id,
            color=detail.get("color", ""),
            color_cn=color_cn,
            size=detail.get("size", ""),
        )
        db.add(new_sku)
    else:
        if detail.get("color"):
            new_sku.color = detail["color"]
        if color_cn:
            new_sku.color_cn = color_cn
        if detail.get("size"):
            new_sku.size = detail["size"]
        if detail.get("name") and new_sku.name.startswith("sku-lv-"):
            new_sku.name = detail["name"]
    return new_sku


def upsert_sku_price(db: Session, sku_id: str, price: Optional[float],
                      currency: str, country: str = LV_COUNTRY,
                      store: str = LV_BRAND_NAME) -> Optional[SKUPrice]:
    if price is None or price <= 0:
        return None
    sp = db.query(SKUPrice).filter(
        SKUPrice.sku_id == sku_id, SKUPrice.country == country
    ).first()
    if not sp:
        sp = SKUPrice(
            sku_id=sku_id, country=country,
            currency=currency or LV_CURRENCY,
            price=float(price), stock=0, store=store,
        )
        db.add(sp)
    else:
        sp.price = float(price)
        if currency:
            sp.currency = currency
        if store:
            sp.store = store
    return sp


def upsert_inventory(db: Session, item: Dict[str, Any],
                     translations: Optional[Dict[str, str]] = None) -> Optional[LvInventory]:
    """upsert 库存记录。"""
    sku_id = item.get("sku_id") or item.get("sku", "")
    if not sku_id:
        return None
    store_id = (item.get("store_id") or "").strip()
    store_name = (item.get("store_name") or "").strip()
    if not (store_id or store_name):
        return None

    # 翻译门店信息
    store_name_cn = ""
    store_address_cn = ""
    store_city_cn = ""
    if translations:
        store_name_cn = translations.get(store_name, "")
        store_address_cn = translations.get(item.get("store_address", ""), "")
        store_city_cn = translations.get(item.get("store_city", ""), "")

    now = datetime.now(timezone.utc)

    inv = db.query(LvInventory).filter(
        LvInventory.sku_id == sku_id,
        LvInventory.store_id == store_id,
    ).first()
    if not inv:
        inv = LvInventory(
            sku_id=sku_id,
            spu_id=item.get("spu_id", ""),
            store_id=store_id,
            store_name=store_name,
            store_name_cn=store_name_cn,
            store_address=item.get("store_address", ""),
            store_address_cn=store_address_cn,
            store_city=item.get("store_city", ""),
            store_city_cn=store_city_cn,
            in_stock=bool(item.get("in_stock", False)),
            stock_status=item.get("stock_status", ""),
            translate_status="translated" if store_name_cn else "pending",
            translated_at=now if store_name_cn else None,
        )
        db.add(inv)
    else:
        # 日文原文始终更新
        if store_name:
            inv.store_name = store_name
        if item.get("store_address"):
            inv.store_address = item["store_address"]
        if item.get("store_city"):
            inv.store_city = item["store_city"]
        inv.in_stock = bool(item.get("in_stock", False))
        if item.get("stock_status"):
            inv.stock_status = item["stock_status"]

        # 翻译字段：已校对(approved)的不覆盖
        if inv.translate_status != "approved":
            if store_name_cn:
                inv.store_name_cn = store_name_cn
            if store_address_cn:
                inv.store_address_cn = store_address_cn
            if store_city_cn:
                inv.store_city_cn = store_city_cn
            if store_name_cn or store_address_cn or store_city_cn:
                inv.translate_status = "translated"
                inv.translated_at = now
    return inv


# ==================== 批量入口 ====================

def persist_detail(db: Session, detail: Dict[str, Any],
                    dry_run: bool = False) -> Dict[str, Any]:
    """处理单条商品详情：写 SPU + SKU + SKUPrice。返回写入摘要。

    自动翻译商品名称、描述、颜色等日文字段。
    """
    summary = {"spu_id": "", "sku_id": "", "price": None,
                "created_spu": False, "created_sku": False}

    if dry_run:
        logger.info("[DRY-RUN] detail=%s", detail)
        return summary

    _ensure_brand(db)
    _ensure_category(db, LV_DEFAULT_CATEGORY_ID, "手袋")

    # 批量翻译：收集所有需要翻译的日文字段
    texts_to_translate: List[str] = []
    if detail.get("name"):
        texts_to_translate.append(detail["name"])
    if detail.get("description"):
        texts_to_translate.append(detail["description"])
    if detail.get("color"):
        texts_to_translate.append(detail["color"])

    translations: Dict[str, str] = {}
    if texts_to_translate:
        try:
            logger.info("开始翻译 %d 条商品文本...", len(texts_to_translate))
            translations = translate_batch(texts_to_translate)
            for orig, cn in translations.items():
                if cn != orig:
                    logger.info("  翻译: %s → %s", orig[:40], cn[:40])
        except Exception as e:
            logger.warning("翻译失败（不影响写入）: %s", e)

    spu = upsert_spu(db, detail, translations)
    if not spu:
        return summary
    db.flush()
    summary["spu_id"] = spu.spu_id

    sku = upsert_sku(db, detail, spu.spu_id, translations)
    if not sku:
        return summary
    db.flush()
    summary["sku_id"] = sku.sku_id

    price = upsert_sku_price(db, sku.sku_id, detail.get("price"),
                              detail.get("currency", LV_CURRENCY))
    if price:
        summary["price"] = price.price

    return summary


def persist_inventory(db: Session, items: List[Dict[str, Any]],
                       dry_run: bool = False) -> int:
    """批量写入库存。返回成功条数。

    自动翻译门店名称、地址、城市等日文字段。
    """
    if dry_run:
        for it in items:
            logger.info("[DRY-RUN] inventory=%s", it)
        return len(items)

    # 批量翻译：收集所有需要翻译的门店信息
    texts_to_translate: List[str] = []
    seen = set()
    for it in items:
        for field in ("store_name", "store_address", "store_city"):
            val = (it.get(field) or "").strip()
            if val and val not in seen:
                seen.add(val)
                texts_to_translate.append(val)

    translations: Dict[str, str] = {}
    if texts_to_translate:
        try:
            logger.info("开始翻译 %d 条门店文本...", len(texts_to_translate))
            translations = translate_batch(texts_to_translate)
        except Exception as e:
            logger.warning("门店翻译失败（不影响写入）: %s", e)

    count = 0
    for it in items:
        try:
            if upsert_inventory(db, it, translations):
                count += 1
        except Exception as e:
            logger.warning("upsert_inventory failed: %s | item=%s", e, it)
    return count
