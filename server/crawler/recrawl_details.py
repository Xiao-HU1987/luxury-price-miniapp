"""重新抓取所有LV商品详情（修复图片、价格等数据）

改进点：
- 每次抓取前检查page是否存活，被关则重建
- 使用响应拦截 + DOM提取双重策略
- 只更新空字段，不覆盖已有的好数据

使用方式：
    venv/bin/python3.11 -m crawler.recrawl_details
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

# 清空代理环境变量，避免 CDP 连接被系统代理拦截
for _proxy_var in ("http_proxy", "https_proxy", "HTTP_PROXY", "HTTPS_PROXY",
                    "all_proxy", "ALL_PROXY"):
    os.environ.pop(_proxy_var, None)

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from playwright.async_api import async_playwright, Page, Browser, BrowserContext
from database import SessionLocal
from crawler import config as crawler_config
from crawler.lv_crawler import (
    _extract_detail_from_dom,
    _ensure_country_selected,
    simulate_user_scroll,
)
from crawler.lv_parser import parse_response, is_lv_response, looks_like_product_data
from crawler.lv_writer import persist_detail, persist_inventory
from playwright.async_api import Response

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("recrawl")


async def _is_page_alive(page: Page) -> bool:
    """检查 page 是否还存活。"""
    try:
        await page.evaluate("1+1")
        return True
    except Exception:
        return False


async def _create_page(context: BrowserContext) -> Page:
    """创建新页面。"""
    page = await context.new_page()
    await _ensure_country_selected(page)
    return page


async def _fetch_with_capture(page: Page, url: str, wait_ms: int) -> List[Dict]:
    """访问URL并拦截所有LV响应。"""
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
            captured.append({"url": resp_url, "status": response.status, "payload": payload})

    handler = lambda r: asyncio.create_task(on_response(r))
    page.on("response", handler)

    try:
        logger.info("Navigating: %s", url[:80])
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=60000)
        except Exception as e:
            logger.warning("goto failed: %s", e)

        try:
            await simulate_user_scroll(page)
        except Exception:
            pass
        try:
            await page.wait_for_timeout(wait_ms)
        except Exception:
            pass
        try:
            await simulate_user_scroll(page)
        except Exception:
            pass
        try:
            await page.wait_for_timeout(min(wait_ms, 2000))
        except Exception:
            pass
    finally:
        try:
            page.remove_listener("response", handler)
        except Exception:
            pass

    return captured


async def recrawl_single(page: Page, url: str, article_no: str) -> Dict:
    """重新抓取单个商品详情。"""
    result = {"success": False, "images": 0, "price": None, "name": ""}

    try:
        payloads = await _fetch_with_capture(
            page, url, crawler_config.DETAIL_PAGE_WAIT_MS
        )

        # DOM 提取
        detail = await _extract_detail_from_dom(page, url)
        if not detail:
            detail = {
                "article_no": article_no,
                "sku": article_no,
                "url": url,
            }

        # 从 API 响应补充信息（图片、价格等）
        for entry in payloads:
            parsed = parse_response(entry["url"], entry["payload"])
            for d in parsed.get("details", []):
                for k, v in d.items():
                    if v and (not detail.get(k) or (k == "images" and not detail.get("images"))):
                        detail[k] = v

        # 确保 article_no 存在
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
                result["price"] = persist_result.get("price")
                result["images"] = len(detail.get("images", []))
                result["name"] = detail.get("name", "")
        except Exception as e:
            logger.exception("写入数据库失败: %s", e)
        finally:
            db.close()

    except Exception as e:
        logger.exception("抓取失败: %s", e)

    return result


async def main():
    # 从文件读取商品列表
    products_file = Path("/tmp/lv_products.json")
    if not products_file.exists():
        logger.error("商品列表文件不存在: %s", products_file)
        return

    with open(products_file, "r", encoding="utf-8") as f:
        products = json.load(f)

    products = [p for p in products if p.get("article_no")]
    logger.info("共 %d 个LV商品需要重新抓取", len(products))

    async with async_playwright() as p:
        logger.info("连接 CDP: %s", crawler_config.CDP_ENDPOINT)
        browser: Browser = await p.chromium.connect_over_cdp(crawler_config.CDP_ENDPOINT)
        if not browser.contexts:
            logger.error("没有找到浏览器上下文")
            return
        context: BrowserContext = browser.contexts[0]

        # 创建初始page
        page = await _create_page(context)

        success_count = 0
        total_images = 0
        failed = []

        for idx, product in enumerate(products):
            url = product["url"]
            article_no = product["article_no"]

            logger.info("=" * 60)
            logger.info("[%d/%d] 抓取 %s", idx + 1, len(products), article_no)
            logger.info("URL: %s", url[:80])

            # 检查page是否存活，如果被关了就重建
            if not await _is_page_alive(page):
                logger.warning("页面已关闭，重新创建...")
                try:
                    page = await _create_page(context)
                    logger.info("新页面已创建")
                except Exception as e:
                    logger.error("无法创建新页面: %s", e)
                    failed.append(article_no)
                    continue

            # 抓取
            result = await recrawl_single(page, url, article_no)

            if result["success"]:
                success_count += 1
                total_images += result["images"]
                logger.info("✅ 成功: 图片%d张, 价格%s, 名称: %s",
                           result["images"],
                           f"¥{result['price']:,.0f}" if result.get("price") else "无",
                           result.get("name", "")[:30])
            else:
                failed.append(article_no)
                logger.warning("❌ 失败")

            # 间隔
            if idx < len(products) - 1:
                await asyncio.sleep(crawler_config.REQUEST_INTERVAL_SEC)

        try:
            await page.close()
        except Exception:
            pass

    logger.info("=" * 60)
    logger.info("重新抓取完成:")
    logger.info("  成功: %d / %d", success_count, len(products))
    logger.info("  总图片数: %d", total_images)
    if failed:
        logger.warning("  失败: %s", ", ".join(failed))


if __name__ == "__main__":
    start = time.time()
    asyncio.run(main())
    elapsed = time.time() - start
    logger.info("总耗时: %.1f 分钟", elapsed / 60)
