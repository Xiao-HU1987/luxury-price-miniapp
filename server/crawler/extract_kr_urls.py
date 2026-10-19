"""从韩国LV官网分类页提取完整商品URL列表（女士+男士）。

直接拦截列表页 JSON 响应 → 提取完整商品 URL（含 slug + SKU）。
输出: data/lv/KR/product_urls_KR.json
"""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import random
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

for _proxy_var in ("http_proxy", "https_proxy", "HTTP_PROXY", "HTTPS_PROXY",
                   "all_proxy", "ALL_PROXY"):
    os.environ.pop(_proxy_var, None)

from playwright.async_api import (
    async_playwright,
    Browser,
    BrowserContext,
    Page,
    Response,
)

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from crawler import config as crawler_config
from crawler.brands import get_brand
from crawler.lv_parser import is_lv_response

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("extract_kr_urls")

DATA_ROOT = BASE_DIR.parent / "data" / "lv"


def _data_root_for(country: str) -> Path:
    root = DATA_ROOT / country
    root.mkdir(parents=True, exist_ok=True)
    return root


class JsonCapture:
    def __init__(self, page: Page):
        self.page = page
        self.json_responses: List[Dict[str, Any]] = []
        self._handler = None

    async def __aenter__(self):
        async def _on_response(resp: Response):
            try:
                url = resp.url
                if not is_lv_response(url):
                    return
                status = resp.status
                if status < 200 or status >= 400:
                    return
                ct = (resp.headers.get("content-type") or "").lower()
                try:
                    text = await resp.text()
                except Exception:
                    return
                if not text or len(text) < 50:
                    return
                data = None
                if "json" in ct or text.lstrip().startswith(('{', '[')):
                    try:
                        data = json.loads(text)
                    except Exception:
                        pass
                if data is not None:
                    self.json_responses.append({"url": url, "status": status, "data": data})
            except Exception:
                pass
        self._handler = _on_response
        self.page.on("response", _on_response)
        return self

    async def __aexit__(self, exc_type, exc, tb):
        if self._handler is not None:
            self.page.remove_listener("response", self._handler)


async def _scroll_and_load_more(page: Page, country: str):
    """滚动 + 点击加载更多（5次尝试）。"""
    # 先滚动
    try:
        viewport = page.viewport_size or {"height": 1000}
        height = viewport["height"]
        current = 0
        for _ in range(8):
            current += height // 2
            await page.evaluate(f"window.scrollTo(0, {current})")
            await asyncio.sleep(0.6)
            scrolled = await page.evaluate("window.scrollY")
            max_y = await page.evaluate("document.body.scrollHeight - window.innerHeight")
            if scrolled + 50 >= max_y:
                break
    except Exception:
        pass

    # 找加载更多按钮（多语言关键词：韩文/中文/日文/英文）
    load_more_selectors = [
        # 韩文
        "button:has-text('더 보기')",
        "button:has-text('더보기')",
        # 中文
        "button:has-text('显示更多')",
        "button:has-text('加载更多')",
        "button:has-text('查看更多')",
        # 日文
        "button:has-text('もっと見る')",
        "button:has-text('続きを見る')",
        # 英文
        "button:has-text('Show more')",
        "button:has-text('Load more')",
        "button:has-text('See more')",
        # 通用 class
        "button.lv-load-more",
        "button[aria-label*='더']",
        "button[aria-label*='显示' i]",
        "button[aria-label*='加载' i]",
        "button[aria-label*='more' i]",
    ]
    for attempt in range(6):
        clicked = False
        for sel in load_more_selectors:
            try:
                btn = await page.query_selector(sel)
                if btn:
                    visible = await btn.is_visible()
                    if visible:
                        await btn.click(timeout=8000)
                        logger.info("  [点击%d] 加载更多按钮", attempt + 1)
                        await asyncio.sleep(3.0)
                        # 滚动到底
                        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                        await asyncio.sleep(1.5)
                        clicked = True
                        break
            except Exception:
                continue
        if not clicked:
            break


def _extract_urls_from_responses(json_responses: List[Dict], base_url: str, locale_path: str) -> List[str]:
    """从分类页 JSON 响应中提取完整商品 URL。"""
    urls: List[str] = []
    seen = set()

    def _add_url(url: str):
        if not url:
            return
        if url.startswith("/"):
            url = base_url + url
        url = url.split("#")[0].split("?")[0]
        # 只保留商品详情页
        if "/products/" not in url:
            return
        if url in seen:
            return
        seen.add(url)
        urls.append(url)

    def _walk(node):
        if isinstance(node, dict):
            # 常见字段：url / slug / productUrl / link / href
            for k, v in node.items():
                kl = k.lower()
                if isinstance(v, str):
                    if kl in ("url", "producturl", "link", "href", "slug"):
                        if "/products/" in v or v.startswith(("/" + locale_path, locale_path)):
                            if "/products/" in v:
                                _add_url(v)
                    if v and (v.startswith("M") or v.startswith("N") or v.startswith("G")) and len(v) in (6, 7, 8):
                        # 这是 SKU，尝试从同层的 slugUrl/slug 字段找完整链接
                        pass
                _walk(v)
            # 产品对象数组
            for arr_key in ("products", "items", "hits", "results", "productList", "catalog"):
                arr = node.get(arr_key)
                if isinstance(arr, list):
                    for item in arr:
                        if isinstance(item, dict):
                            # 提取 slug + sku
                            slug = item.get("slug") or item.get("productSlug") or item.get("urlId")
                            sku = item.get("skuId") or item.get("sku") or item.get("articleNumber") or item.get("identifier")
                            if isinstance(slug, str) and isinstance(sku, str):
                                full = f"{base_url}/{locale_path}/products/{slug}/{sku}"
                                _add_url(full)
                            elif isinstance(slug, str):
                                if "/products/" in slug:
                                    _add_url(slug)
        elif isinstance(node, list):
            for item in node:
                _walk(item)

    for jr in json_responses:
        _walk(jr.get("data", {}))

    return sorted(urls)


async def _get_page(pw) -> Page:
    browser = await pw.chromium.connect_over_cdp(crawler_config.CDP_ENDPOINT)
    contexts = browser.contexts
    if not contexts:
        ctx = await browser.new_context()
    else:
        ctx = contexts[0]
    page = await ctx.new_page()
    return page


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--country", default="KR")
    args = parser.parse_args()
    country = args.country

    adapter = get_brand("LV", country)
    category_urls = getattr(adapter, "category_urls", None) or [adapter.get_category_url()]
    # 从 category_urls 第一个样本中提取 locale_path，例如 https://cn.louisvuitton.com/chn-cn/women/... → chn-cn
    sample = category_urls[0] if category_urls else adapter.base_url
    locale_path = ""
    parts = sample.replace(adapter.base_url, "").strip("/").split("/")
    if len(parts) >= 1 and "-" in parts[0]:
        locale_path = parts[0]
    if not locale_path:
        # 回退：第一个分类样本 URL 的 /xxx-xx/ 段
        import re
        m = re.search(r"/([a-z]{2,3}-[a-z]{2,3})/", sample)
        if m:
            locale_path = m.group(1)
    base_url = adapter.base_url

    logger.info("站点: %s  locale_path=%s", base_url, locale_path)
    logger.info("分类页: %d 个", len(category_urls))

    all_urls: List[str] = []
    seen_global = set()

    async with async_playwright() as pw:
        page = await _get_page(pw)
        try:
            # ===== 预热：先访问官网首页，给 Akamai 建立会话，避免一上来就 CONNECTION_CLOSED =====
            try:
                logger.info("[WARMUP] 预热首页: %s", base_url)
                await page.goto(base_url, timeout=90_000, wait_until="domcontentloaded")
                await asyncio.sleep(5.0)
                # 滚动两下
                await page.evaluate("window.scrollTo(0, 200)")
                await asyncio.sleep(0.8)
                await page.evaluate("window.scrollTo(0, 0)")
                await asyncio.sleep(1.5)
                logger.info("[WARMUP] 首页预热完成: title=%s", (await page.title() or "")[:60])
            except Exception as e:
                logger.warning("[WARMUP] 首页预热失败（但继续尝试）: %s", e)

            for ci, cat_url in enumerate(category_urls):
                logger.info("[%d/%d] 分类页: %s", ci + 1, len(category_urls), cat_url)
                json_responses_merged = []
                # 多 3 次重试，对付 CONNECTION_CLOSED / 302 challenge
                for attempt in range(3):
                    async with JsonCapture(page) as cap:
                        ok = False
                        try:
                            await page.goto(cat_url, timeout=90_000, wait_until="domcontentloaded")
                            await asyncio.sleep(6.0)
                            await _scroll_and_load_more(page, country)
                            await asyncio.sleep(4.0)
                            ok = True
                        except Exception as e:
                            logger.warning("  [尝试 %d/3] 页面加载异常: %s", attempt + 1, e)
                        # 尝试合并捕获的 JSON（哪怕goto失败，说不定前面的 302 跳转让 response handler 还是抓到了点）
                        json_responses_merged.extend(cap.json_responses)
                    if ok and len(json_responses_merged) >= 2:
                        break
                    # 失败等一会再试
                    if attempt < 2:
                        wait_s = random.uniform(15, 35) * (attempt + 1)
                        logger.info("  [重试 %d/3] 等 %.0fs 后关旧tab开新tab重试...", attempt + 1, wait_s)
                        await asyncio.sleep(wait_s)
                        try: await page.close()
                        except Exception: pass
                        page = await _get_page(pw)

                extracted = _extract_urls_from_responses(json_responses_merged, base_url, locale_path)
                logger.info("  捕获 %d 条 JSON, 提取 %d 条商品 URL", len(json_responses_merged), len(extracted))
                for u in extracted:
                    if u not in seen_global:
                        seen_global.add(u)
                        all_urls.append(u)

                # 冷却
                await asyncio.sleep(random.uniform(10, 20))
        finally:
            try:
                await page.close()
            except Exception:
                pass

    # 过滤非商品
    filtered: List[str] = []
    for url in all_urls:
        if "/products/" not in url:
            continue
        filtered.append(url)

    logger.info("去重后总商品URL数: %d", len(filtered))

    out_file = _data_root_for(country) / f"product_urls_{country}.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(sorted(filtered), f, ensure_ascii=False, indent=2)
    logger.info("已保存: %s", out_file)


if __name__ == "__main__":
    asyncio.run(main())
