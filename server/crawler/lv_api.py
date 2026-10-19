"""LV 爬虫高级 API — 封装稳定、易用的抓取接口

提供高层 API，内部处理：
- CDP 连接管理
- 重试与错误恢复
- 健康检查与告警
- 数据库写入
- 日志记录

使用方式：
```python
from crawler.lv_api import crawl_product_detail, crawl_store_inventory

# 抓取单个商品详情 + 库存
result = crawl_product_detail(
    url="https://jp.louisvuitton.com/.../M2A099",
    store_inventory=True,
    dry_run=False,
)
print(result.success, result.detail, len(result.inventories))
```
"""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from playwright.async_api import async_playwright, Page

from . import config as crawler_config
from .lv_crawler import (
    _extract_detail_from_dom,
    collect_store_inventories,
    fetch_page_payloads,
    parse_response,
    _extract_inventory_from_captures,
)
from .lv_writer import persist_detail, persist_inventory
from .health import (
    CrawlHealthReport,
    validate_detail,
    validate_inventories,
    check_page_structure,
    send_alert,
)
from .utils import retry_async
from database import SessionLocal

logger = logging.getLogger("lv_crawler.api")


@dataclass
class CrawlResult:
    """单次抓取结果。"""
    success: bool = False
    detail: Optional[Dict[str, Any]] = None
    inventories: List[Dict[str, Any]] = field(default_factory=list)
    health_report: Optional[CrawlHealthReport] = None
    error_message: str = ""
    spu_id: str = ""
    sku_id: str = ""


async def _crawl_single_async(
    url: str,
    store_inventory: bool = False,
    dry_run: bool = False,
    launch_mode: bool = False,
) -> CrawlResult:
    """异步实现：抓取单个商品详情 + 可选门店库存。"""
    result = CrawlResult()
    report = CrawlHealthReport()

    async with async_playwright() as p:
        # 1. 连接浏览器
        if launch_mode:
            logger.info("🚀 launch 模式启动浏览器...")
            browser = await p.chromium.launch(
                headless=False,
                executable_path=crawler_config.CHROME_EXECUTABLE,
                args=crawler_config.CHROME_STEALTH_ARGS,
            )
            context = await browser.new_context(
                viewport=crawler_config.VIEWPORT,
                user_agent=crawler_config.USER_AGENT,
                locale=crawler_config.LOCALE,
                timezone_id=crawler_config.TIMEZONE_ID,
            )
            await context.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
                window.chrome = { runtime: {} };
                Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
                Object.defineProperty(navigator, 'languages', { get: () => ['ja-JP', 'ja'] });
            """)
            page = await context.new_page()
        else:
            logger.info("🔌 连接 CDP: %s", crawler_config.CDP_ENDPOINT)
            browser = await p.chromium.connect_over_cdp(crawler_config.CDP_ENDPOINT)
            if not browser.contexts:
                result.error_message = "未找到浏览器上下文，请先打开 Chrome 并访问 LV"
                logger.error(result.error_message)
                return result
            context = browser.contexts[0]
            page = await context.new_page()
            logger.info("✅ CDP 连接成功")

        try:
            # 2. 访问页面
            logger.info("🌐 访问: %s", url)
            payloads, api_images = await fetch_page_payloads(
                page, url, crawler_config.DETAIL_PAGE_WAIT_MS
            )
            logger.info("📦 捕获 %d 个 API 响应, %d 张图片", len(payloads), len(api_images))

            # 3. 提取详情
            detail = await _extract_detail_from_dom(page, url)
            if not detail:
                result.error_message = "未能从 DOM 提取商品详情"
                logger.error(result.error_message)
                return result

            # 从 API 响应补充
            for entry in payloads:
                parsed = parse_response(entry["url"], entry["payload"])
                for d in parsed.get("details", []):
                    for k, v in d.items():
                        if v and (not detail.get(k) or (k == "images" and not detail["images"])):
                            detail[k] = v

            # 图片后备：网络拦截捕获的图片
            article_no = detail.get("article_no") or ""
            dom_images = detail.get("images") or []
            if len(dom_images) < 2 and api_images:
                net_imgs = [u for u in api_images
                             if article_no and article_no.lower() in u.lower()]
                if not net_imgs:
                    net_imgs = [u for u in api_images if '/images/is/image/lv/' in u.lower()]
                if net_imgs:
                    logger.info("  补充 %d 张网络图片 (DOM仅 %d 张)", len(net_imgs), len(dom_images))
                    existing = set(dom_images)
                    merged = list(dom_images)
                    for u in net_imgs:
                        if u not in existing:
                            merged.append(u)
                            existing.add(u)
                    detail["images"] = merged
                    if not detail.get("image") and merged:
                        detail["image"] = merged[0]

            result.detail = detail
            logger.info("✅ 商品详情: %s (%s)", detail.get("name"), detail.get("article_no"))

            # 4. 提取库存（API + 门店）
            sku_id = detail.get("article_no") or detail.get("sku", "")
            inventories: List[Dict[str, Any]] = []

            if sku_id:
                # API 库存
                api_inv = await _extract_inventory_from_captures(payloads, sku_id)
                inventories.extend(api_inv)

                # 门店库存
                if store_inventory:
                    logger.info("🏪 开始抓取门店库存...")
                    store_inv = await retry_async(
                        collect_store_inventories,
                        page, sku_id,
                        retries=2,
                        delay=3.0,
                        name="门店库存抓取",
                    )
                    if store_inv:
                        inventories.extend(store_inv)
                        logger.info("✅ 门店库存: %d 家", len(store_inv))
                    else:
                        logger.warning("⚠️  门店库存抓取失败")

            result.inventories = inventories

            # 5. 健康检查
            for check in validate_detail(detail):
                report.add(check)
            if store_inventory and inventories:
                for check in validate_inventories(inventories, min_expected=10):
                    report.add(check)
                try:
                    dom_checks = await check_page_structure(page)
                    for check in dom_checks:
                        report.add(check)
                except Exception as e:
                    logger.debug("DOM 结构检查异常: %s", e)

            result.health_report = report

            if report.has_errors:
                send_alert(
                    f"商品 {detail.get('article_no', 'unknown')} 健康检查失败: {report.summary()}",
                    level="error",
                )

            logger.info("📊 %s", report.summary())

            # 6. 写入数据库
            if not dry_run and detail:
                db = SessionLocal()
                try:
                    wr = persist_detail(db, detail, dry_run=False)
                    db.commit()
                    result.spu_id = wr.get("spu_id", "")
                    result.sku_id = wr.get("sku_id", "")

                    for inv in inventories:
                        inv["sku_id"] = result.sku_id
                        inv["spu_id"] = result.spu_id
                    inv_count = persist_inventory(db, inventories, dry_run=False)
                    db.commit()

                    logger.info("💾 已写入数据库: spu=%s, inv=%d", result.spu_id, inv_count)
                    result.success = True
                except Exception as e:
                    logger.exception("数据库写入失败: %s", e)
                    result.error_message = f"数据库写入失败: {e}"
                    db.rollback()
                finally:
                    db.close()
            else:
                result.success = True  # dry-run 也算成功

        except Exception as e:
            logger.exception("抓取异常: %s", e)
            result.error_message = str(e)
        finally:
            if not launch_mode:
                # CDP 模式：关闭我们新开的 tab，不关闭浏览器
                try:
                    await page.close()
                except Exception:
                    pass
            else:
                await browser.close()

    return result


def crawl_product_detail(
    url: str,
    store_inventory: bool = False,
    dry_run: bool = False,
    launch_mode: bool = False,
) -> CrawlResult:
    """抓取单个商品详情（同步入口）。

    Args:
        url: 商品详情页 URL
        store_inventory: 是否抓取门店库存（较慢，约 60-90 秒）
        dry_run: 只抓取不写入数据库
        launch_mode: True=启动独立浏览器，False=CDP 接管（推荐）

    Returns:
        CrawlResult 对象，包含详情、库存、健康报告等
    """
    return asyncio.run(_crawl_single_async(url, store_inventory, dry_run, launch_mode))


def crawl_inventory_only(
    url: str,
    dry_run: bool = False,
) -> CrawlResult:
    """仅抓取门店库存（需要页面已在浏览器中打开）。

    Args:
        url: 商品详情页 URL（用于定位商品）
        dry_run: 只抓取不写入

    Returns:
        CrawlResult 对象
    """
    return crawl_product_detail(url, store_inventory=True, dry_run=dry_run)
