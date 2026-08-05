"""修复缺失图片/价格的LV商品

功能：
1. 从列表页获取正确的URL
2. 对缺失图片或价格的商品进行重新抓取
3. 确保每个商品都有完整的名称、图片、价格、库存

使用方式：
    venv/bin/python3.11 -m crawler.fix_missing
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional

for _proxy_var in ("http_proxy", "https_proxy", "HTTP_PROXY", "HTTPS_PROXY",
                    "all_proxy", "ALL_PROXY"):
    os.environ.pop(_proxy_var, None)

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from playwright.async_api import async_playwright, Page, Browser, BrowserContext, Response
from database import SessionLocal
from crawler import config as crawler_config
from crawler.lv_crawler import (
    _extract_detail_from_dom,
    _ensure_country_selected,
    simulate_user_scroll,
)
from crawler.lv_parser import parse_response, is_lv_response, looks_like_product_data
from crawler.lv_writer import persist_detail, _is_valid_name, _is_valid_description, _is_bad_image_url

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("fix_missing")


async def _is_page_alive(page: Page) -> bool:
    try:
        await page.evaluate("1+1")
        return True
    except Exception:
        return False


async def _create_page(context: BrowserContext) -> Page:
    page = await context.new_page()
    await _ensure_country_selected(page)
    return page


def has_good_image(spu: Dict) -> bool:
    """判断SPU是否有有效的LV官方主图。"""
    img = spu.get("image") or ""
    if not img:
        return False
    if _is_bad_image_url(img):
        return False
    return "louisvuitton.com" in img and "/images/is/image/lv/" in img


def get_missing_products() -> List[Dict]:
    """从数据库获取缺失图片或价格的LV商品。"""
    db = SessionLocal()
    try:
        from models.sku import SPU
        from sqlalchemy import text
        spus = db.query(SPU).filter(SPU.brand_id == "LV").all()
        
        # 批量查询每个SPU是否有日元价格
        spu_ids = [s.spu_id for s in spus]
        price_map = {}
        if spu_ids:
            from models.sku import SKU, SKUPrice
            from sqlalchemy import distinct
            rows = db.query(distinct(SKU.spu_id)).join(
                SKUPrice, SKU.sku_id == SKUPrice.sku_id
            ).filter(
                SKUPrice.price > 0,
                SKUPrice.currency == "JPY",
                SKU.spu_id.in_(spu_ids)
            ).all()
            for row in rows:
                price_map[row[0]] = True
        
        missing = []
        for spu in spus:
            spu_dict = {
                "spu_id": spu.spu_id,
                "article_no": spu.article_no or "",
                "name_cn": spu.name_cn or "",
                "image": spu.image or "",
                "source_url": spu.source_url or "",
                "has_good_image": has_good_image({"image": spu.image}),
                "has_price": price_map.get(spu.spu_id, False),
            }
            missing.append(spu_dict)
        return [s for s in missing if not s["has_good_image"] or not s["has_price"]]
    finally:
        db.close()


async def fetch_from_listing_page(context: BrowserContext) -> Dict[str, str]:
    """从列表页获取所有商品的正确URL。"""
    page = None
    for p in context.pages:
        if "N-tfr7qdp" in p.url:
            page = p
            break
    if not page:
        page = await context.new_page()
        await page.goto(crawler_config.CATEGORY_URL, wait_until="domcontentloaded", timeout=60000)
        await page.wait_for_timeout(3000)

    items = await page.evaluate(r"""
        () => {
            const map = {};
            document.querySelectorAll('a[href*="/products/"]').forEach(a => {
                const href = a.href || '';
                if (!href.includes('/jpn-jp/products/')) return;
                const m = href.match(/\/([A-Z0-9]{4,8})$/);
                if (m && !map[m[1]]) {
                    map[m[1]] = href;
                }
            });
            return map;
        }
    """)
    return items


async def fetch_single(page: Page, url: str, article_no: str) -> Dict:
    """抓取单个商品详情。"""
    result = {"success": False, "images": 0, "has_price": False, "name": ""}

    captured: List[Dict] = []

    async def on_response(response: Response):
        resp_url = response.url
        if not is_lv_response(resp_url, crawler_config.RESPONSE_DOMAIN_ALLOWLIST):
            return
        try:
            if response.status != 200:
                return
        except Exception:
            return
        try:
            body_text = await response.text()
        except Exception:
            return
        if not body_text:
            return
        try:
            payload = json.loads(body_text)
        except Exception:
            return
        if looks_like_product_data(payload, resp_url) or crawler_config.SAVE_ALL_LV_RESPONSES:
            captured.append({"url": resp_url, "payload": payload})

    handler = lambda r: asyncio.create_task(on_response(r))
    page.on("response", handler)

    try:
        logger.info("Navigating: %s", url[:80])
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=60000)
        except Exception as e:
            logger.warning("goto: %s", e)

        try:
            await simulate_user_scroll(page)
        except Exception:
            pass
        try:
            await page.wait_for_timeout(crawler_config.DETAIL_PAGE_WAIT_MS)
        except Exception:
            pass
        try:
            await simulate_user_scroll(page)
        except Exception:
            pass
        try:
            await page.wait_for_timeout(min(crawler_config.DETAIL_PAGE_WAIT_MS, 2000))
        except Exception:
            pass

        # DOM 提取
        detail = await _extract_detail_from_dom(page, url)
        if not detail:
            detail = {"article_no": article_no, "sku": article_no, "url": url}

        # 从 API 响应补充
        for entry in captured:
            parsed = parse_response(entry["url"], entry["payload"])
            for d in parsed.get("details", []):
                for k, v in d.items():
                    if v:
                        if k == "images":
                            if not detail.get("images"):
                                detail[k] = v
                        elif k == "name":
                            if _is_valid_name(str(v)):
                                detail[k] = v
                        elif k == "description":
                            if _is_valid_description(str(v)):
                                detail[k] = v
                        elif not detail.get(k):
                            detail[k] = v

        if not detail.get("article_no"):
            detail["article_no"] = article_no
        if not detail.get("sku"):
            detail["sku"] = article_no

        # 写入数据库
        db = SessionLocal()
        try:
            persist_result = persist_detail(db, detail, dry_run=False)
            db.commit()
            if persist_result["spu_id"]:
                result["success"] = True
                result["has_price"] = bool(persist_result.get("price"))
                result["images"] = len(detail.get("images", []))
                result["name"] = detail.get("name", "")
        except Exception as e:
            logger.exception("写入失败: %s", e)
        finally:
            db.close()

    except Exception as e:
        logger.exception("抓取失败: %s", e)
    finally:
        try:
            page.remove_listener("response", handler)
        except Exception:
            pass

    return result


async def main():
    missing = get_missing_products()
    logger.info("需要修复的商品: %d 个", len(missing))
    for m in missing:
        logger.info("  %s: 图片%s 价格%s - %s",
                    m["article_no"],
                    "✓" if m["has_good_image"] else "✗",
                    "✓" if m["has_price"] else "✗",
                    m["name_cn"])

    async with async_playwright() as p:
        logger.info("连接 CDP...")
        browser: Browser = await p.chromium.connect_over_cdp(crawler_config.CDP_ENDPOINT)
        if not browser.contexts:
            logger.error("没有浏览器上下文")
            return
        context: BrowserContext = browser.contexts[0]

        # 从列表页获取正确的URL
        logger.info("从列表页获取商品URL...")
        url_map = await fetch_from_listing_page(context)
        logger.info("获取到 %d 个商品URL", len(url_map))

        # 构建待抓取列表
        to_fetch = []
        for m in missing:
            art = m["article_no"]
            if art in url_map:
                to_fetch.append({"article_no": art, "url": url_map[art]})
            elif m["source_url"] and "louisvuitton.com" in m["source_url"] and "/products/" in m["source_url"]:
                # 用已有的source_url（排除404的短路径）
                if m["source_url"].count("/") > 5:  # 正确URL有较多路径段
                    to_fetch.append({"article_no": art, "url": m["source_url"]})
                else:
                    logger.warning("URL可能不正确（短路径）: %s - %s", art, m["source_url"])
            else:
                logger.warning("找不到URL: %s", art)

        logger.info("待抓取: %d 个", len(to_fetch))

        # 创建page
        page = await _create_page(context)

        success = 0
        for idx, item in enumerate(to_fetch):
            logger.info("=" * 60)
            logger.info("[%d/%d] 修复 %s", idx + 1, len(to_fetch), item["article_no"])

            if not await _is_page_alive(page):
                logger.warning("页面已关闭，重建...")
                try:
                    page = await _create_page(context)
                except Exception as e:
                    logger.error("重建失败: %s", e)
                    continue

            result = await fetch_single(page, item["url"], item["article_no"])
            if result["success"]:
                success += 1
                logger.info("✅ 成功: 图片%d张, 价格%s, 名称: %s",
                            result["images"],
                            "有" if result["has_price"] else "无",
                            result.get("name", "")[:30])
            else:
                logger.warning("❌ 失败")

            if idx < len(to_fetch) - 1:
                await asyncio.sleep(crawler_config.REQUEST_INTERVAL_SEC)

        try:
            await page.close()
        except Exception:
            pass

    logger.info("=" * 60)
    logger.info("修复完成: %d/%d 成功", success, len(to_fetch))

    # 验证结果
    missing2 = get_missing_products()
    if missing2:
        logger.warning("仍有 %d 个商品缺失信息:", len(missing2))
        for m in missing2:
            logger.warning("  %s: 图%s 价%s",
                           m["article_no"],
                           "✗" if not m["has_good_image"] else "✓",
                           "✗" if not m["has_price"] else "✓")
    else:
        logger.info("所有商品数据完整！")


if __name__ == "__main__":
    start = time.time()
    asyncio.run(main())
    logger.info("总耗时: %.1f 分钟", (time.time() - start) / 60)
