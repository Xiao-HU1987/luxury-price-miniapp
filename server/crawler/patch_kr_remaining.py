"""补抓韩国LV剩余4个URL的数据。

复用 lv_crawl_urls.py 的完整解析器 + Akamai 检测器，
但去掉四态状态机（4条 URL 手动控制节奏即可）。

用法:
  cd server
  venv/bin/python3.11 -m crawler.patch_kr_remaining
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import random
import sys
from datetime import datetime
from pathlib import Path

for _proxy_var in ("http_proxy", "https_proxy", "HTTP_PROXY", "HTTPS_PROXY",
                    "all_proxy", "ALL_PROXY"):
    os.environ.pop(_proxy_var, None)

from playwright.async_api import async_playwright

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from crawler import config as crawler_config
from crawler.brands import get_brand
from crawler.lv_crawler_multi import (
    ResponseCapture, _extract_product, _extract_inventories,
    _ensure_dirs, _append_jsonl,
)
from crawler.lv_crawl_urls import (
    _ensure_browser_and_page, _is_page_alive, _detect_akamai_block, _safe_navigate,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("patch_kr_remaining")

# 剩余4个 URL（2026-08-02 21:21 确认未抓取）
REMAINING_URLS = [
    "https://kr.louisvuitton.com/kor-kr/products/georges-tote-mm-autres-cuirs-nvprod4680081v/M23154",
    "https://kr.louisvuitton.com/kor-kr/products/hobo-cargo-monogram-shadow-leather-nvprod6210031v/M14778",
    "https://kr.louisvuitton.com/kor-kr/products/low-key-hobo-mm-h31-nvprod7540220v/M29144",
    "https://kr.louisvuitton.com/kor-kr/products/pochette-accessoires-autres-toiles-monogram-nvprod7310102v/M29148",
]

COUNTRY = "KR"


async def crawl_one(page, product_url, adapter, dirs, existing_skus):
    """单条 URL 抓取，复用完整解析器 + Akamai 检测。
    返回 (success: bool, sku_id|None)
    """
    try:
        if not await _is_page_alive(page):
            logger.warning("[RECOVER] page 失效，重建...")
            browser, ctx, page = await _ensure_browser_and_page(pw)  # noqa
    except Exception as e:
        logger.warning("[RECOVER] page 检测异常，重建...: %s", e)

    antibot_detected = False
    try:
        async with ResponseCapture(page, COUNTRY, dirs["raw"]) as cap:
            ok = await _safe_navigate(page, product_url, wait_ms=crawler_config.DETAIL_PAGE_WAIT_MS)
            if await _detect_akamai_block(cap):
                logger.error("[ANTI-BOT] ⛔ Akamai 拦截 URL: %s", product_url[-60:])
                antibot_detected = True
                ok = False

        result = _extract_product(COUNTRY, adapter, cap, product_url)
        parsed_ok = bool(result and result.get("sku_id"))

        if parsed_ok:
            sku_lc = result["sku_id"].lower()
            if sku_lc not in existing_skus:
                _append_jsonl(dirs["products"], result)
                existing_skus.add(sku_lc)
                logger.info("  ✅ sku=%s name=%s price=%s",
                            result["sku_id"],
                            (result.get("name_local", "") or "")[:30],
                            result.get("price", 0))

                try:
                    inventories = _extract_inventories(COUNTRY, adapter, cap, product_url, result)
                    if inventories:
                        for inv in inventories:
                            _append_jsonl(dirs["inventories"], inv)
                        logger.info("  📦 库存记录 %d 条", len(inventories))
                except Exception as e:
                    logger.debug("  库存解析跳过: %s", e)
                return True, result["sku_id"]
            else:
                logger.info("  ✅ sku=%s 已存在，跳过写入", result["sku_id"])
                return True, result["sku_id"]

        # 解析失败
        if antibot_detected:
            logger.warning("  ⚠️ Akamai 拦截，解析失败")
        else:
            logger.warning("  ⚠️ 解析空（未触发Akamai），OK=%s", ok)
        return False, None

    except Exception as e:
        logger.error("  ❌ 异常: %s", e)
        return False, None


async def main():
    adapter = get_brand("LV", COUNTRY)
    dirs = _ensure_dirs(COUNTRY)

    # 加载已存在的 sku
    existing_skus: set[str] = set()
    products_path = dirs["products"]
    if products_path.exists():
        with open(products_path) as f:
            for line in f:
                try:
                    d = json.loads(line)
                    sid = d.get("sku_id", "")
                    if sid:
                        existing_skus.add(sid.lower())
                except:
                    pass
    logger.info("已加载 %d 个既有 SKU", len(existing_skus))

    # 过滤掉已经抓到的（以防重跑）
    to_crawl = []
    for url in REMAINING_URLS:
        sku = url.rstrip("/").split("/")[-1]
        if sku.lower() in existing_skus:
            logger.info("  跳过已存在: %s", sku)
        else:
            to_crawl.append(url)
    logger.info("需要补抓 %d 个 URL", len(to_crawl))

    if not to_crawl:
        logger.info("✅ 全部已完成，退出")
        return

    async with async_playwright() as pw:
        browser, ctx, page = await _ensure_browser_and_page(pw)

        success = 0
        failed_urls = []
        for i, url in enumerate(to_crawl):
            logger.info("[%d/%d] %s", i + 1, len(to_crawl), url.split("/")[-1])
            ok, sku = await crawl_one(page, url, adapter, dirs, existing_skus)
            if ok:
                success += 1
            else:
                failed_urls.append(url)

            # 手动节奏：每条间隔 15-30s，加上批次冷却 60s
            if i < len(to_crawl) - 1:
                inter = random.uniform(15, 30)
                logger.info("  间隔 %.1f 秒...", inter)
                await asyncio.sleep(inter)

        # 批次冷却（补抓4条，最后不需要）

    logger.info("\n=== 补抓完成 ===")
    logger.info("成功: %d/%d", success, len(to_crawl))
    if failed_urls:
        logger.warning("失败 %d 个 URL:", len(failed_urls))
        for u in failed_urls:
            logger.warning("  %s", u)


if __name__ == "__main__":
    asyncio.run(main())
