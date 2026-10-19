"""LV 日本官网数据采集主入口

⚠️ 重要前提：Akamai WAF 会识别并拦截独立启动的 Chrome 实例（launch 模式），
   因此真正抓取必须使用 **CDP 接管模式**，即接管用户日常使用的 Chrome。

标准启动流程（**第一次必须手动完成，之后可复用同一个 Chrome 会话**）：
    1. 关闭所有 Chrome 窗口（Cmd+Q）
    2. 执行：
       open -n -a "Google Chrome" --args --remote-debugging-port=9333 \\
           --proxy-server="http://127.0.0.1:7890"
    3. 在新开的 Chrome 中手动访问 https://jp.louisvuitton.com
       （如遇验证码/验证，请手动完成）
    4. 在 server/ 目录下执行：
       venv/bin/python3.11 -m crawler.lv_crawler --mode single \\
           --url "https://jp.louisvuitton.com/jpn-jp/products/..."

辅助测试（用于验证脚本逻辑，会被 Akamai 拦截但能确认代码流程）：
    venv/bin/python3.11 -m crawler.lv_crawler --mode single --url "..." --launch

核心思路（详见技术需求文档 §3.1）：
    Playwright 通过 CDP 接管真实 Chrome 进程以绕过 Akamai WAF，
    拦截浏览器发出的所有 louisvuitton.com 响应，从 JSON body 直接
    提取商品/详情/库存数据，不依赖 DOM 解析。
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
from typing import Any, Dict, List, Optional, Tuple

# 关键：清空代理环境变量，避免 CDP 连接（127.0.0.1:9333）被系统代理拦截
# Chrome 浏览器自身已带 --proxy-server 走代理，Playwright 的 CDP 连接不需要
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

# 把 server/ 加入 import 路径（使得 crawler 可以作为包被引用）
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from database import SessionLocal  # noqa: E402
from crawler import config as crawler_config  # noqa: E402
from crawler.lv_parser import (  # noqa: E402
    is_lv_response,
    is_target_url,
    looks_like_product_data,
    parse_response,
    extract_inventory_items,
)
from crawler.lv_writer import (  # noqa: E402
    persist_detail,
    persist_inventory,
)
from crawler.health import (  # noqa: E402
    CrawlHealthReport,
    validate_detail,
    validate_inventories,
    check_page_structure,
    send_alert,
    is_valid_detail_for_write,
)
from crawler.utils import retry_async  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("lv_crawler")


# ==================== 响应收集器 ====================

class ResponseCapture:
    """单次页面访问期间拦截所有 LV 响应（JSON + 图片）。

    每个 Page 在 navigate 前绑定一个 ResponseCapture，
    导航结束后从 capture 读取所有捕获的 JSON 数据和图片 URL 并清空。
    """

    IMAGE_EXTENSIONS = ('.jpg', '.jpeg', '.png', '.webp', '.gif')
    IMAGE_PATH_PATTERNS = ('/images/is/image/lv/', '/images/')

    def __init__(self, page: Page):
        self.page = page
        self.captured: List[Dict[str, Any]] = []
        self.image_urls: List[str] = []
        self._handler = None

    def attach(self) -> None:
        self._handler = lambda r: asyncio.create_task(self._on_response(r))
        self.page.on("response", self._handler)

    def detach(self) -> None:
        if self._handler:
            try:
                self.page.remove_listener("response", self._handler)
            except Exception:
                pass
            self._handler = None

    def reset(self) -> None:
        self.captured = []
        self.image_urls = []

    def get_product_images(self, article_no: str = "") -> List[str]:
        """返回捕获的产品图片 URL（去重、过滤）。"""
        seen = set()
        result = []
        for url in self.image_urls:
            if url in seen:
                continue
            seen.add(url)
            lower = url.lower()
            if any(p in lower for p in ('teads.tv', 'doubleclick', '/error/', '404', 'track', 'pixel', 'analytics')):
                continue
            if 'louisvuitton.com' not in lower:
                continue
            if any(ext in lower for ext in self.IMAGE_EXTENSIONS) or '/images/' in lower:
                if article_no and article_no.lower() in lower:
                    result.append(url)
                elif not article_no:
                    result.append(url)
                elif '/images/is/image/lv/' in lower:
                    result.append(url)
        return result

    async def _on_response(self, response: Response) -> None:
        url = response.url
        if not is_lv_response(url, crawler_config.RESPONSE_DOMAIN_ALLOWLIST):
            return
        # 只关心 200 OK
        try:
            if response.status != 200:
                return
        except Exception:
            return

        # 尝试读取 content-type
        try:
            content_type = (response.headers.get("content-type") or "").lower()
        except Exception:
            content_type = ""

        # 优先捕获图片 URL（基于 URL 模式和 content-type）
        url_lower = url.lower()
        is_image_content = content_type.startswith("image/")
        is_image_url = any(ext in url_lower for ext in self.IMAGE_EXTENSIONS) or '/images/' in url_lower
        if is_image_content or is_image_url:
            if 'louisvuitton.com' in url_lower:
                self.image_urls.append(url)
                return

        if "json" not in content_type and "javascript" not in content_type:
            return

        # 尝试读取 body
        body_text: Optional[str] = None
        try:
            body_text = await response.text()
        except Exception:
            return

        if not body_text:
            return

        # 尝试 JSON 解析
        payload: Any = None
        try:
            payload = json.loads(body_text)
        except Exception:
            return

        # URL 关键词 OR body 关键词命中才记录
        matched = (
            is_target_url(url, crawler_config.RESPONSE_URL_KEYWORDS)
            or looks_like_product_data(payload, url)
        )
        if matched or crawler_config.SAVE_ALL_LV_RESPONSES:
            entry = {"url": url, "status": response.status, "payload": payload}
            self.captured.append(entry)
            self._maybe_save_raw(url, body_text)

    def _maybe_save_raw(self, url: str, body_text: str) -> None:
        """把未识别的较大 JSON 落到本地，便于事后分析 LV 真实字段。"""
        if not crawler_config.RAW_CAPTURE_ENABLED:
            return
        if len(body_text) > crawler_config.RAW_CAPTURE_MAX_BYTES:
            return
        try:
            crawler_config.RAW_CAPTURE_DIR.mkdir(parents=True, exist_ok=True)
            ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            slug = url.replace("://", "_").replace("/", "_").replace("?", "_")[:120]
            file_path = crawler_config.RAW_CAPTURE_DIR / f"{ts}_{slug}.json"
            # 用格式化 JSON 写入（已是合法 JSON）
            try:
                formatted = json.dumps(json.loads(body_text), ensure_ascii=False, indent=2)
            except Exception:
                formatted = body_text
            file_path.write_text(formatted, encoding="utf-8")
        except Exception as e:
            logger.debug("save raw failed: %s", e)


# ==================== 用户行为模拟 ====================

async def simulate_user_scroll(page: Page) -> None:
    """滚动到页底，触发懒加载。"""
    if not crawler_config.SCROLL_TO_BOTTOM:
        return
    try:
        last_height = await page.evaluate("document.body.scrollHeight")
        scroll_y = 0
        while scroll_y < last_height:
            scroll_y += crawler_config.SCROLL_STEP_PX
            await page.evaluate(f"window.scrollTo(0, {scroll_y})")
            await page.wait_for_timeout(crawler_config.SCROLL_INTERVAL_MS)
            new_height = await page.evaluate("document.body.scrollHeight")
            if new_height == last_height:
                break
            last_height = new_height
        # 滚回顶部，便于后续元素可见
        await page.evaluate("window.scrollTo(0, 0)")
    except Exception as e:
        logger.debug("scroll failed: %s", e)


# ==================== 反爬检测 ====================

async def detect_block(page: Page, payloads: List[Dict[str, Any]]) -> Tuple[bool, str]:
    """检测是否被 Akamai WAF 拦截。

    返回 (is_blocked, reason)。
    检测策略：
    1. 页面内容含 Access Denied / Forbidden
    2. 页面 URL 被重定向到非商品页
    3. 所有 LV 响应均返回 403
    4. 页面内容为维护提示页
    """
    try:
        content = await page.content()
    except Exception:
        content = ""

    # 检查 1: Access Denied
    if "Access Denied" in content or "access denied" in content.lower():
        return True, "页面含 'Access Denied'，确认被 Akamai WAF 拦截"

    # 检查 2: 维护页
    if "maintenance" in content.lower() and len(content) < 5000:
        return True, "页面为维护提示页"

    # 检查 3: 所有 LV 响应都是 403
    lv_entries = [e for e in payloads if "louisvuitton" in e.get("url", "")]
    if lv_entries and all(e.get("status") == 403 for e in lv_entries):
        return True, "所有 LV 响应均为 403"

    # 检查 4: 页面被重定向到非商品页（URL 不含 /products/）
    current_url = page.url or ""
    if "/products/" not in current_url and "louisvuitton.com" in current_url:
        # 可能被重定向到首页或错误页
        if "error" in current_url.lower() or "dispatch" in current_url.lower():
            return True, f"被重定向到非商品页: {current_url}"

    # 检查 5: 页面内容过短（可能被替换为拦截页）
    if len(content) < 1000 and "louisvuitton" not in content.lower():
        return True, f"页面内容异常过短 ({len(content)} 字符)，可能被拦截"

    return False, ""


# ==================== 进度持久化 ====================

def save_progress(listings: List[Dict[str, Any]], completed_urls: set,
                  file_path: Path = None) -> None:
    """保存爬取进度到 JSON 文件，支持断点续爬。"""
    if file_path is None:
        file_path = crawler_config.PROGRESS_FILE
    data = {
        "saveTime": datetime.now().isoformat(),
        "total": len(listings),
        "completed": list(completed_urls),
        "completedCount": len(completed_urls),
        "pending": [
            {
                "url": it.get("url", ""),
                "name": it.get("name", ""),
                "article_no": it.get("article_no", ""),
                "price": it.get("price"),
                "currency": it.get("currency", ""),
            }
            for it in listings
            if it.get("url", "") not in completed_urls
        ],
    }
    try:
        file_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        logger.info("📁 进度已保存: %d/%d 完成", len(completed_urls), len(listings))
    except Exception as e:
        logger.warning("保存进度失败: %s", e)


def load_progress(file_path: Path = None) -> Optional[Dict[str, Any]]:
    """加载之前的爬取进度。"""
    if file_path is None:
        file_path = crawler_config.PROGRESS_FILE
    if not file_path.exists():
        return None
    try:
        data = json.loads(file_path.read_text(encoding="utf-8"))
        logger.info("📁 发现进度文件: %d/%d 已完成，%d 待爬取",
                    data.get("completedCount", 0),
                    data.get("total", 0),
                    len(data.get("pending", [])))
        return data
    except Exception as e:
        logger.warning("加载进度失败: %s", e)
        return None


# ==================== 随机化等待 ====================

async def random_sleep(min_sec: float, max_sec: float, label: str = "") -> None:
    """随机等待，模拟人类不规则操作节奏。"""
    wait = random.uniform(min_sec, max_sec)
    if label:
        logger.info("⏳ %s: 等待 %.1f 秒...", label, wait)
    await asyncio.sleep(wait)


async def random_mouse_move(page: Page) -> None:
    """随机移动鼠标，模拟真人浏览。"""
    try:
        x = random.randint(200, 1500)
        y = random.randint(200, 800)
        await page.mouse.move(x, y)
        await asyncio.sleep(random.uniform(0.3, 0.8))
        # 再移动一次
        x2 = random.randint(200, 1500)
        y2 = random.randint(200, 800)
        await page.mouse.move(x2, y2)
    except Exception:
        pass


async def smart_scroll(page: Page) -> None:
    """随机化的滚动行为，模拟真人浏览商品详情。"""
    try:
        scroll_steps = random.randint(2, 5)
        for i in range(scroll_steps):
            step = random.randint(300, 800)
            await page.evaluate(f"window.scrollBy(0, {step})")
            await asyncio.sleep(random.uniform(0.5, 1.5))
        # 偶尔滚回顶部
        if random.random() < 0.3:
            await page.evaluate("window.scrollTo(0, 0)")
            await asyncio.sleep(random.uniform(0.5, 1.0))
    except Exception:
        pass


async def refresh_session(context: BrowserContext, old_page: Page) -> Page:
    """关闭旧 tab 并新建 tab，清除 cookies，刷新会话。"""
    try:
        # 清除所有 cookies
        await context.clear_cookies()
        logger.info("🔄 已清除 cookies")
    except Exception as e:
        logger.debug("清除 cookies 失败: %s", e)

    # 新开一个 tab
    new_page = await context.new_page()
    try:
        await old_page.close()
        logger.info("🔄 旧 tab 已关闭，新 tab 已创建")
    except Exception:
        pass

    # 重新预设日本区
    await _ensure_country_selected(new_page)
    return new_page


# ==================== 单页处理流程 ====================

async def _ensure_country_selected(page: Page) -> None:
    """确保国家/区域已被选择（避免 dispatch.json 重定向）。

    LV 站点在首次访问时会根据 IP 弹出国/地区选择页（dispatch.json）。
    通过预先访问 dispatch 页面并模拟"点击"日本区，可让后续详情页直接加载。
    """
    try:
        # 先访问 dispatch 页面
        await page.goto(
            f"{crawler_config.LV_BASE_URL}/",
            wait_until="domcontentloaded",
            timeout=30000,
        )
        await page.wait_for_timeout(2000)
        # 通过设置 localStorage / cookie 让 LV 记住区域
        await page.evaluate("""
            () => {
                try {
                    localStorage.setItem('lv_country', 'jpn-jp');
                    localStorage.setItem('lv_lang', 'ja-jp');
                    localStorage.setItem('selectedCountry', 'jpn-jp');
                    localStorage.setItem('selectedLanguage', 'ja-jp');
                } catch (e) {}
                // 同时设置 cookie
                document.cookie = 'ak_cc=JP; path=/; domain=.louisvuitton.com';
                document.cookie = 'lv_country=jpn-jp; path=/; domain=.louisvuitton.com';
                document.cookie = 'lv_lang=ja-jp; path=/; domain=.louisvuitton.com';
            }
        """)
        logger.info("🌏 已预设日本区 cookie/localStorage")
    except Exception as e:
        logger.debug("ensure_country_selected: %s", e)


async def _extract_detail_from_dom(page: Page, url: str) -> Optional[Dict[str, Any]]:
    """从 LV 详情页 DOM 中提取商品信息。

    LV 是 Nuxt.js SPA，商品详情通过 SSR + 客户端 hydration 渲染。
    主要字段来源：
    - 商品名:  h1
    - 价格:    .lv-price (含 ￥xxx,xxx)
    - 货号:    URL 末尾的 /M2A099
    - 描述:    页面 .lv-product-description 区域
    - 图片:    <source srcset> / <img src> (含 /images/is/image/lv/)
    """
    try:
        info = await page.evaluate(r"""
            () => {
                const r = {};
                // 名称：h1
                const h1 = document.querySelector('h1');
                r.name = h1 ? h1.innerText.trim() : '';

                // 货号：从 URL 最后一段提取 (例如 /M2A099)
                const path = location.pathname;
                const m = path.match(/\/([A-Z0-9]{4,8})$/);
                r.article_no = m ? m[1] : '';
                r.slug = path.split('/').pop() || '';

                // 价格：.lv-price（textContent，因为 innerText 可能因 CSS 隐藏而返回空）
                const priceEl = document.querySelector('.lv-price');
                if (priceEl) {
                    const txt = priceEl.textContent || '';
                    const m2 = txt.match(/[¥￥]\s*([\d,]+)/);
                    r.price_text = m2 ? m2[1] : txt.trim();
                }

                // 货币：从价格字符推断
                r.currency = 'JPY';

                // 描述：找包含 "メゾン" 等关键词的段落
                const descs = Array.from(document.querySelectorAll('p, div, span'))
                    .filter(el => {
                        const t = el.innerText || '';
                        return t.length > 30 && t.length < 1500 &&
                            (t.includes('メゾン') || t.includes('アイコンバッグ') ||
                             t.includes('シグネチャー') || t.includes('エレガント'));
                    });
                if (descs.length > 0) {
                    r.description = descs[0].innerText.trim().substring(0, 800);
                }

                // 图片：多来源提取，优先取LV官方产品图
                const badPatterns = ['teads.tv', 'mpulse.net', 'linkedin.com', 'doubleclick.net',
                    'googletagservices', 'google-analytics', 'adservice', 'track', 'pixel', 'beacon',
                    '/error/', '404.jpg', 'maintenance_page'];
                const isBadUrl = (url) => {
                    if (!url) return true;
                    return badPatterns.some(p => url.toLowerCase().includes(p));
                };
                const isGoodImg = (url) => {
                    if (!url) return false;
                    if (isBadUrl(url)) return false;
                    const lower = url.toLowerCase();
                    if (lower.includes('louisvuitton.com') && lower.includes('/images/is/image/lv/')) return true;
                    if (lower.startsWith('/images/is/image/lv/')) return true;
                    const imgExts = ['.jpg', '.jpeg', '.png', '.webp'];
                    if (lower.includes('louisvuitton.com') && imgExts.some(ext => lower.endsWith(ext))) return true;
                    if (lower.includes('louisvuitton.com') && lower.includes('/images/') && imgExts.some(ext => lower.includes(ext + '?'))) return true;
                    return false;
                };
                const fixUrl = (u) => {
                    if (!u) return '';
                    if (u.startsWith('http')) return u;
                    if (u.startsWith('//')) return 'https:' + u;
                    if (u.startsWith('/')) return location.origin + u;
                    return u;
                };
                const imgSet = new Set();

                // 1. 从 <picture><source srcset> 提取（最可靠）
                document.querySelectorAll('picture source[srcset]').forEach(s => {
                    const urls = (s.srcset || '').split(',').map(x => x.trim().split(' ')[0]);
                    urls.forEach(u => {
                        const full = fixUrl(u);
                        if (full && isGoodImg(full)) imgSet.add(full);
                    });
                });

                // 2. 从 <img> 的 src 和 data-src 提取
                document.querySelectorAll('img[src], img[data-src]').forEach(i => {
                    [i.src, i.getAttribute('data-src')].forEach(u => {
                        const full = fixUrl(u);
                        if (full && isGoodImg(full)) imgSet.add(full);
                    });
                });

                // 3. 从所有 a[href] 中找图片链接（商品图点击放大的链接）
                document.querySelectorAll('a[href*="images/is/image/lv/"]').forEach(a => {
                    const full = fixUrl(a.href);
                    if (full && isGoodImg(full)) imgSet.add(full);
                });

                // 4. 从内联 style 的 background-image 提取
                document.querySelectorAll('[style*="url("]').forEach(el => {
                    const style = el.getAttribute('style') || '';
                    const m = style.match(/url\(["']?([^"')]+)["']?\)/);
                    if (m) {
                        const full = fixUrl(m[1]);
                        if (full && isGoodImg(full)) imgSet.add(full);
                    }
                });

                // 5. 从 JSON-LD / script 标签中的结构化数据提取
                document.querySelectorAll('script[type="application/ld+json"]').forEach(sc => {
                    try {
                        const data = JSON.parse(sc.textContent || '');
                        const extractImgs = (obj) => {
                            if (!obj) return;
                            if (typeof obj === 'string' && isGoodImg(obj)) imgSet.add(fixUrl(obj));
                            if (Array.isArray(obj)) obj.forEach(extractImgs);
                            if (typeof obj === 'object') Object.values(obj).forEach(extractImgs);
                        };
                        extractImgs(data);
                    } catch (e) {}
                });

                r.images = Array.from(imgSet).slice(0, 15);

                // 颜色
                const colorEls = Array.from(document.querySelectorAll('[class*="color" i], [class*="sku" i]'))
                    .filter(el => el.innerText && el.innerText.length < 50);
                if (colorEls.length > 0) {
                    r.color = colorEls[0].innerText.trim();
                }

                return r;
            }
        """)
        if not info.get("name") and not info.get("article_no"):
            return None

        # 价格转换为数字
        price_val: Optional[float] = None
        if info.get("price_text"):
            cleaned = info["price_text"].replace(",", "").replace(" ", "")
            try:
                price_val = float(cleaned)
            except ValueError:
                pass

        return {
            "name": info.get("name", ""),
            "article_no": info.get("article_no", ""),
            "sku": info.get("article_no", ""),
            "price": price_val,
            "currency": info.get("currency", "JPY"),
            "description": info.get("description", ""),
            "color": info.get("color", ""),
            "images": info.get("images", []),
            "url": url,
        }
    except Exception as e:
        logger.warning("DOM 提取失败: %s", e)
        return None


async def _extract_inventory_from_api(page: Page, sku_id: str) -> List[Dict[str, Any]]:
    """从 LV 库存 API 主动查询库存。

    调用 api.louisvuitton.com/eco-as/lvcom-prodct-dtl-eapi/v2/products/jpn-jp/availability
    通过 fetch 在浏览器上下文中发起请求（自动带上 cookie/auth）。
    """
    if not sku_id:
        return []
    api_url = (
        f"https://api.louisvuitton.com/eco-as/lvcom-prodct-dtl-eapi/"
        f"v2/products/jpn-jp/availability"
    )
    try:
        result = await page.evaluate(
            r"""
            async ([url, skuId]) => {
                try {
                    const r = await fetch(url, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ skuIds: [skuId] }),
                    });
                    if (!r.ok) return { error: 'status ' + r.status };
                    return await r.json();
                } catch (e) {
                    return { error: String(e) };
                }
            }
            """,
            [api_url, sku_id],
        )
        if result and isinstance(result, dict) and "error" in result:
            logger.debug("库存 API 返回错误: %s", result.get("error"))
            return []
        if result:
            return extract_inventory_items(result)
    except Exception as e:
        logger.debug("库存 API 调用失败: %s", e)
    return []


async def _extract_inventory_from_captures(captures: List[Dict[str, Any]],
                                              sku_id: str) -> List[Dict[str, Any]]:
    """从已捕获的 API 响应中提取库存信息。"""
    items: List[Dict[str, Any]] = []
    for entry in captures:
        url = entry.get("url", "")
        if "availability" not in url:
            continue
        payload = entry.get("payload")
        if not isinstance(payload, dict):
            continue
        # LV 实际格式: {"skuAvailability": [{...}], "availability": [...]}
        for sku_entry in payload.get("skuAvailability", []):
            if not isinstance(sku_entry, dict):
                continue
            if sku_entry.get("skuId") != sku_id:
                continue
            in_stock = bool(sku_entry.get("inStock", False))
            items.append({
                "sku": sku_id,
                "store_id": "jpn_online",
                "store_name": "LV オンラインストア (日本)",
                "store_address": "オンラインストア",
                "store_city": "Tokyo",
                "in_stock": in_stock,
                "stock_status": "in_stock" if in_stock else "out_of_stock",
            })
    return items


async def collect_store_inventories(page: Page, sku_id: str,
                                     cities: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    """抓取日本各门店的库存状态。

    流程：
    1. 滚动到「ストアの在庫状況を確認する」折叠面板并展开
    2. 点击「ストアの在庫状況」按钮打开库存搜索弹窗
    3. 在弹窗中输入城市名 → 点击「在庫状況を見る」
    4. 从第二步弹窗的 DOM 提取门店名称、地址、库存状态
    5. 过滤出日本门店（地址含 都道府県）

    采用 DOM 交互方案而非直接 API 调用，因为门店库存 API 需要特殊签名，
    通过浏览器正常交互最稳定。
    """
    if cities is None:
        cities = ["東京", "大阪", "名古屋", "福岡", "札幌"]

    all_stores: Dict[str, Dict[str, Any]] = {}

    async def _disable_backdrop() -> None:
        """禁用 backdrop 的点击拦截。"""
        await page.evaluate(r"""
            () => {
                const backdrops = document.querySelectorAll('.lv-modal__backdrop, .lv-backdrop');
                for (const b of backdrops) {
                    b.style.pointerEvents = 'none';
                    b.style.opacity = '0.3';
                }
            }
        """)

    def _is_japan_store(address: str) -> bool:
        """判断是否为日本门店（地址含都道府県标记）。"""
        return any(k in address for k in ['県', '都', '道', '府'])

    try:
        # 第一步：找到并展开「ストアの在庫状況を確認する」折叠面板
        expanded = await page.evaluate(r"""
            () => {
                // 找到包含库存文本的 lv-expandable-panel
                const panels = document.querySelectorAll('.lv-expandable-panel');
                let targetPanel = null;
                for (const panel of panels) {
                    if (panel.innerText.includes('ストアの在庫状況を確認する')) {
                        targetPanel = panel;
                        break;
                    }
                }
                if (!targetPanel) return { ok: false, reason: 'panel not found' };

                // 滚动到面板
                targetPanel.scrollIntoView({ behavior: 'smooth', block: 'center' });

                // 找到展开按钮并点击
                const btn = targetPanel.querySelector('button[aria-expanded]');
                if (!btn) return { ok: false, reason: 'button not found' };

                const isExpanded = btn.getAttribute('aria-expanded') === 'true';
                if (!isExpanded) {
                    btn.click();
                }
                return { ok: true, was_expanded: isExpanded };
            }
        """)
        if not expanded.get("ok"):
            logger.warning("未找到库存折叠面板: %s", expanded.get("reason"))
            return []
        await page.wait_for_timeout(1500)
        logger.info("库存折叠面板已展开")

        # 第二步：点击「ストアの在庫状況」按钮打开弹窗
        store_btn_visible = await page.evaluate(r"""
            () => {
                const btn = document.querySelector('.lv-product-locate-in-store__container');
                if (!btn) return false;
                btn.scrollIntoView({ behavior: 'smooth', block: 'center' });
                return true;
            }
        """)
        if not store_btn_visible:
            logger.warning("未找到库存按钮 .lv-product-locate-in-store__container")
            return []
        await page.wait_for_timeout(1500)
        # 用 JS 点击（避免 Playwright click 的视口检查）
        await page.evaluate(r"""
            () => {
                const btn = document.querySelector('.lv-product-locate-in-store__container');
                if (btn) btn.click();
            }
        """)
        await page.wait_for_timeout(3000)
        await _disable_backdrop()
        logger.info("门店库存弹窗已打开")

        # 逐个城市搜索
        for city in cities:
            try:
                # 确保回到第一步（搜索页）
                await page.evaluate(r"""
                    () => {
                        const first = document.querySelector('.lv-locate-in-store__first-step-modal');
                        const second = document.querySelector('.lv-locate-in-store__second-step-modal');
                        const container = document.querySelector('.lv-modal__container');
                        if (first && second) {
                            first.style.display = 'block';
                            second.style.display = 'none';
                        }
                    }
                """)
                await page.wait_for_timeout(500)
                await _disable_backdrop()

                # 清空并输入搜索词
                search_input = page.locator(
                    '.lv-locate-in-store__first-step-modal input[placeholder*="都道府県"]'
                )
                if await search_input.count() == 0:
                    # 更宽泛的选择器
                    search_input = page.locator(
                        '.lv-modal__content input[type="text"], .lv-modal__content input:not([type])'
                    )
                if await search_input.count() == 0:
                    logger.debug("未找到搜索输入框，跳过 %s", city)
                    continue

                try:
                    await search_input.first.click(timeout=3000)
                except Exception:
                    await search_input.first.click(force=True, timeout=3000)
                await search_input.first.fill('')
                await page.wait_for_timeout(200)
                await search_input.first.type(city, delay=100)
                await page.wait_for_timeout(2500)

                # 点击「在庫状況を見る」按钮
                see_btn = page.locator('.lv-modal__footer button')
                if await see_btn.count() == 0:
                    continue
                btn_disabled = await see_btn.first.get_attribute('disabled')
                if btn_disabled is not None:
                    logger.debug("「%s」搜索后按钮仍禁用，跳过", city)
                    continue

                try:
                    await see_btn.first.click(timeout=8000)
                except Exception as click_err:
                    logger.debug("正常点击失败，尝试 force click: %s", click_err)
                    await see_btn.first.click(force=True, timeout=5000)
                await page.wait_for_timeout(6000)

                # 从第二步弹窗的 DOM 提取门店列表
                stores = await page.evaluate(r"""
                    () => {
                        const second = document.querySelector('.lv-locate-in-store__second-step-modal');
                        if (!second) return [];
                        const cards = second.querySelectorAll('.lv-store-card-detailed');
                        const results = [];
                        for (const card of cards) {
                            const nameEl = card.querySelector('.lv-store-card-detailed__name');
                            const name = nameEl ? nameEl.innerText.trim() : '';
                            if (!name) continue;

                            const infoEl = card.querySelector('.lv-store-card-detailed__info');
                            let address = '';
                            if (infoEl) {
                                address = infoEl.innerText.trim().replace(/\n/g, ' ');
                            }
                            if (!address) {
                                const lines = card.innerText.trim().split('\n').map(s => s.trim()).filter(s => s);
                                for (const l of lines) {
                                    if ((l.includes('県') || l.includes('都') || l.includes('道') || l.includes('府')) && !name.includes(l)) {
                                        address = l;
                                        break;
                                    }
                                }
                            }

                            const stockEl = card.querySelector('.lv-store-card-detailed__stock');
                            let stock_status = '';
                            let in_stock = false;
                            if (stockEl) {
                                const raw = stockEl.innerText.trim();
                                if (raw.includes('在庫あり')) { in_stock = true; stock_status = 'in_stock'; }
                                else if (raw.includes('在庫なし')) { in_stock = false; stock_status = 'out_of_stock'; }
                                else if (raw.includes('在庫僅少')) { in_stock = true; stock_status = 'low_stock'; }
                                else { stock_status = raw; in_stock = false; }
                            }

                            let store_id = '';
                            const linkEl = card.querySelector('a[href*="point-of-sale"]');
                            if (linkEl) {
                                const href = linkEl.getAttribute('href') || '';
                                const m = href.match(/japan\/([^/?#]+)/);
                                if (m) store_id = m[1];
                            }
                            if (!store_id) {
                                store_id = name.substring(0, 64);
                            }

                            let store_city = '';
                            const cityMatch = address.match(/([\u4e00-\u9fa5]+[都道府県])/);
                            if (cityMatch) store_city = cityMatch[1];

                            results.push({
                                store_id: store_id,
                                store_name: name,
                                store_address: address.substring(0, 255),
                                store_city: store_city,
                                in_stock: in_stock,
                                stock_status: stock_status,
                            });
                        }
                        return results;
                    }
                """)

                # 只保留日本门店
                jp_stores = [s for s in stores if _is_japan_store(s.get('store_address', ''))]

                for s in jp_stores:
                    s["sku"] = sku_id
                    key = s.get("store_id", "") or s.get("store_name", "")
                    if key and key not in all_stores:
                        all_stores[key] = s

                logger.info("搜索「%s」: 找到 %d 家门店（日本 %d 家）", city, len(stores), len(jp_stores))

            except Exception as e:
                logger.debug("搜索 %s 失败: %s", city, e)
                continue

    except Exception as e:
        logger.warning("门店库存抓取异常: %s", e)

    result = list(all_stores.values())
    logger.info("门店库存抓取完成: %d 家日本门店", len(result))
    return result


async def fetch_page_payloads(
    page: Page,
    url: str,
    wait_ms: int,
    skip_country_setup: bool = False,
) -> Tuple[List[Dict[str, Any]], List[str]]:
    """访问单个 URL，等待 AJAX 完成，返回 (JSON响应列表, 图片URL列表)。"""
    if not skip_country_setup:
        await _ensure_country_selected(page)

    capture = ResponseCapture(page)
    capture.attach()
    try:
        logger.info("Navigating: %s", url)
        nav_ok = True
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=60000)
        except Exception as e:
            logger.warning("goto failed (%s): %s", url, e)
            nav_ok = False

        if nav_ok:
            # 使用随机化滚动替代固定滚动
            try:
                await smart_scroll(page)
            except Exception:
                pass
            try:
                await page.wait_for_timeout(wait_ms)
            except Exception as e:
                logger.debug("first wait interrupted: %s", e)
            # 随机鼠标移动
            try:
                await random_mouse_move(page)
            except Exception:
                pass
            try:
                await smart_scroll(page)
            except Exception:
                pass
            try:
                await page.wait_for_timeout(min(wait_ms, 2000))
            except Exception as e:
                logger.debug("second wait interrupted: %s", e)

        image_urls = capture.get_product_images()
        logger.debug("捕获 %d 条JSON, %d 张图片", len(capture.captured), len(image_urls))
        return list(capture.captured), image_urls
    finally:
        capture.detach()


# ==================== 抓取编排 ====================

async def _load_all_products(page: Page, max_clicks: int = 10) -> None:
    """点击"加载更多"按钮直到所有商品加载完成。"""
    for i in range(max_clicks):
        try:
            btn = page.locator(
                'button.lv-paginated-list__button, '
                'button:has-text("さらに表示する"), '
                'button:has-text("Show more")'
            )
            if not await btn.is_visible(timeout=2000):
                logger.info("没有更多商品可加载")
                break
            await btn.scroll_into_view_if_needed(timeout=3000)
            await btn.click(timeout=5000)
            logger.info("点击加载更多 [%d]", i + 1)
            await page.wait_for_timeout(3000)
        except Exception as e:
            logger.debug("加载更多结束: %s", e)
            break


async def collect_listing(page: Page, category_url: str = "") -> List[Dict[str, Any]]:
    """抓取分类页，从 DOM 提取商品列表（URL + 名称 + 价格）。

    LV 列表页是 Nuxt.js SSR，商品卡片直接在 DOM 中。
    策略：DOM 解析 + 点击加载更多 + 滚动懒加载。
    """
    url = category_url or crawler_config.CATEGORY_URL
    logger.info("访问分类页: %s", url)
    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=60000)
    except Exception as e:
        logger.warning("goto 失败: %s", e)
    await page.wait_for_timeout(5000)

    # 点击"加载更多"加载全部商品
    await _load_all_products(page, max_clicks=15)
    await simulate_user_scroll(page)
    await page.wait_for_timeout(2000)

    # 从 DOM 提取商品链接 + 名称 + 价格
    items = await page.evaluate(r"""
        () => {
            const results = [];
            const seen = new Set();
            // 所有含 /products/ 的链接
            const links = document.querySelectorAll('a[href*="/products/"]');
            for (const a of links) {
                const href = a.href || '';
                if (!href.includes('/jpn-jp/products/')) continue;
                if (seen.has(href)) continue;
                seen.add(href);

                // 从链接内提取名称和价格
                const nameEl = a.querySelector('h2, h3, [class*="name" i]');
                const priceEl = a.querySelector('[class*="price" i]');

                // 从 URL 提取货号（末尾 /M2A099）
                const m = href.match(/\/([A-Z0-9]{4,8})$/);

                results.push({
                    url: href,
                    name: nameEl ? nameEl.innerText.trim() : '',
                    price_text: priceEl ? priceEl.innerText.trim() : '',
                    article_no: m ? m[1] : '',
                });
            }
            return results;
        }
    """)

    # 解析价格
    import re as _re
    for item in items:
        pt = item.get("price_text", "")
        m = _re.search(r'[¥￥]\s*([\d,]+)', pt)
        if m:
            item["price"] = float(m.group(1).replace(",", ""))
        else:
            item["price"] = None
        item["currency"] = "JPY"
        item.pop("price_text", None)

    logger.info("分类页提取到 %d 个商品", len(items))
    return items


async def collect_detail(page: Page, listing: Dict[str, Any],
                         fetch_store_inventory: bool = False) -> Optional[Dict[str, Any]]:
    """抓取单个商品详情（DOM 解析 + API 库存 + 门店库存）。

    Args:
        fetch_store_inventory: 是否抓取门店库存（较慢，约 30-60 秒/商品）
    """
    url = listing.get("url", "")
    if not url:
        article = listing.get("article_no", "")
        if article:
            url = crawler_config.PRODUCT_DETAIL_URL_TEMPLATE.format(slug=article.lower())
        else:
            return None
    if url.startswith("/"):
        url = crawler_config.LV_BASE_URL + url

    # 访问详情页（捕获 JSON + 图片）
    payloads, captured_images = await fetch_page_payloads(
        page, url, crawler_config.DETAIL_PAGE_WAIT_MS, skip_country_setup=True,
    )

    # 策略 1: DOM 提取
    detail = await _extract_detail_from_dom(page, url)

    # 策略 2: 从列表页已有的信息补充
    if not detail:
        detail = {
            "name": listing.get("name", ""),
            "sku": listing.get("article_no", ""),
            "article_no": listing.get("article_no", ""),
            "price": listing.get("price"),
            "currency": listing.get("currency", "JPY"),
            "url": url,
        }
    else:
        if not detail.get("price") and listing.get("price"):
            detail["price"] = listing["price"]

    # 图片后备：如果 DOM 提取的图片不足，用网络拦截捕获的图片
    article_no = detail.get("article_no") or detail.get("sku") or ""
    dom_images = detail.get("images") or []
    if len(dom_images) < 2 and captured_images:
        net_imgs = [u for u in captured_images
                     if article_no and article_no.lower() in u.lower()]
        if not net_imgs:
            net_imgs = [u for u in captured_images if '/images/is/image/lv/' in u.lower()]
        if net_imgs:
            logger.info("  补充 %d 张网络拦截图片 (DOM仅 %d 张)", len(net_imgs), len(dom_images))
            existing = set(dom_images)
            merged = list(dom_images)
            for u in net_imgs:
                if u not in existing:
                    merged.append(u)
                    existing.add(u)
            detail["images"] = merged
            if not detail.get("image") and merged:
                detail["image"] = merged[0]

    # 库存：从 availability API 响应提取
    sku_id = detail.get("article_no") or detail.get("sku") or ""
    inventories: List[Dict[str, Any]] = []
    if sku_id:
        inventories = await _extract_inventory_from_captures(payloads, sku_id)

    # 门店库存（可选，较慢）
    if fetch_store_inventory and sku_id:
        store_inv = await collect_store_inventories(page, sku_id)
        inventories.extend(store_inv)

    for it in inventories:
        if not it.get("sku_id"):
            it["sku_id"] = sku_id

    return {"detail": detail, "inventories": inventories, "payloads": payloads}


def _detail_sku_id(detail: Dict[str, Any]) -> str:
    from crawler.lv_writer import _sku_id
    spu_id = f"spu-lv-{(detail.get('article_no') or '').strip().lower()}"
    return _sku_id(spu_id, detail.get("sku", ""),
                    detail.get("color", ""), detail.get("size", ""))


def _load_existing_article_nos() -> set:
    """从数据库加载已有的 LV 商品 article_no 集合，用于增量抓取。"""
    try:
        from models import SPU
        db = SessionLocal()
        try:
            existing = db.query(SPU.article_no).filter(
                SPU.brand_id == crawler_config.LV_BRAND_ID,
                SPU.article_no.isnot(None),
            ).all()
            article_nos = {row[0].strip().upper() for row in existing if row[0]}
            logger.info("📦 数据库中已有 %d 个 LV 商品", len(article_nos))
            return article_nos
        finally:
            db.close()
    except Exception as e:
        logger.warning("加载已有商品失败: %s", e)
        return set()


# ==================== 主流程 ====================

async def _create_browser_and_page(p, launch_mode: bool):
    """根据 launch_mode 选择连接方式（CDP 或独立启动）"""
    if launch_mode:
        logger.info("🚀 启动独立 Chrome 浏览器 (launch mode)...")
        browser: Browser = await p.chromium.launch(
            headless=False,
            executable_path=crawler_config.CHROME_EXECUTABLE,
            args=crawler_config.CHROME_STEALTH_ARGS,
        )
        context: BrowserContext = await browser.new_context(
            viewport=crawler_config.VIEWPORT,
            user_agent=crawler_config.USER_AGENT,
            locale=crawler_config.LOCALE,
            timezone_id=crawler_config.TIMEZONE_ID,
        )
        # 注入隐身脚本
        await context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            window.chrome = { runtime: {} };
            Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
            Object.defineProperty(navigator, 'languages', { get: () => ['ja-JP', 'ja'] });
        """)
        page: Page = await context.new_page()
        logger.info("✅ Chrome launch 模式已就绪")
        return browser, context, page
    else:
        logger.info("🔌 正在连接 CDP: %s", crawler_config.CDP_ENDPOINT)
        browser: Browser = await p.chromium.connect_over_cdp(crawler_config.CDP_ENDPOINT)
        if not browser.contexts:
            logger.error("❌ No browser context found. Please open Chrome and navigate to LV first.")
            return None, None, None
        context: BrowserContext = browser.contexts[0]
        # 始终新开一个 tab 抓取，避免干扰用户当前页面
        page: Page = await context.new_page()
        logger.info("✅ CDP 连接成功，已在新 tab 中工作")
        return browser, context, page


async def run(mode: str, dry_run: bool, single_url: str = "",
              launch_mode: bool = False,
              fetch_store_inventory: bool = False,
              resume: bool = False,
              incremental: bool = True) -> Dict[str, int]:
    summary = {"listings": 0, "details": 0, "inventories": 0, "errors": 0}

    async with async_playwright() as p:
        browser, context, page = await _create_browser_and_page(p, launch_mode)
        if page is None:
            return summary

        # ====== single 模式：直接抓取指定 URL ======
        if mode == "single" and single_url:
            logger.info("Single-mode crawl: %s", single_url)
            payloads, single_images = await fetch_page_payloads(page, single_url, crawler_config.DETAIL_PAGE_WAIT_MS)
            logger.info("Captured %d responses, %d images", len(payloads), len(single_images))

            # 策略 1: 从 DOM 提取（LV 是 SSR + 客户端 hydration）
            detail = await _extract_detail_from_dom(page, single_url)
            if detail:
                logger.info("=" * 60)
                logger.info("✅ 从 DOM 提取到商品数据:")
                for k, v in detail.items():
                    if k == "images":
                        logger.info("  %s: (%d 张图片)", k, len(v) if v else 0)
                    else:
                        logger.info("  %s: %s", k, v)
                logger.info("=" * 60)

            # 策略 2: 从捕获的 API 响应中补充信息
            for entry in payloads:
                result = parse_response(entry["url"], entry["payload"])
                for d in result.get("details", []):
                    for k, v in d.items():
                        if v and (not detail.get(k) or (k == "images" and not detail["images"])):
                            detail[k] = v
                if result.get("listings") and not detail.get("article_no"):
                    detail["article_no"] = result["listings"][0].get("article_no", "")

            # 图片后备：网络拦截捕获的图片
            if detail:
                art_no = detail.get("article_no") or ""
                dom_imgs = detail.get("images") or []
                if len(dom_imgs) < 2 and single_images:
                    net_imgs = [u for u in single_images
                                 if art_no and art_no.lower() in u.lower()]
                    if not net_imgs:
                        net_imgs = [u for u in single_images if '/images/is/image/lv/' in u.lower()]
                    if net_imgs:
                        logger.info("  补充 %d 张网络图片 (DOM仅 %d 张)", len(net_imgs), len(dom_imgs))
                        existing = set(dom_imgs)
                        merged = list(dom_imgs)
                        for u in net_imgs:
                            if u not in existing:
                                merged.append(u)
                                existing.add(u)
                        detail["images"] = merged
                        if not detail.get("image") and merged:
                            detail["image"] = merged[0]

            # 库存：从已捕获的 availability API 响应提取
            sku_id_for_inventory = detail.get("article_no") or detail.get("sku") if detail else ""
            inventories: List[Dict[str, Any]] = []
            if sku_id_for_inventory:
                inventories = await _extract_inventory_from_captures(payloads, sku_id_for_inventory)

            # 门店库存（可选）
            if fetch_store_inventory and sku_id_for_inventory:
                store_inv = await collect_store_inventories(page, sku_id_for_inventory)
                inventories.extend(store_inv)

            # 检查 Akamai 拦截迹象（使用统一检测函数）
            is_blocked, block_reason = await detect_block(page, payloads)
            if is_blocked:
                logger.error("❌ 检测到反爬拦截: %s", block_reason)
                if launch_mode:
                    logger.error(
                        "launch 模式会被 Akamai 识别为机器人。"
                        " 必须使用 CDP 接管模式，"
                        "在 Chrome 中手动访问 LV 并完成验证，"
                        "然后不带 --launch 参数重试。"
                    )
                else:
                    logger.error(
                        "CDP 模式也被拦截，可能原因："
                        "Chrome 使用的不是你日常的用户资料，"
                        "或者 Chrome 未带代理。"
                        "请仔细检查 README 中的启动步骤。"
                    )
                return summary

            # 打印抓取到的结果
            if detail:
                logger.info("=" * 60)
                logger.info("✅ 成功抓取到商品数据:")
                for k, v in detail.items():
                    if k == "images":
                        logger.info("  %s: (%d 张图片)", k, len(v) if v else 0)
                    else:
                        logger.info("  %s: %s", k, v)
                logger.info("=" * 60)
            else:
                logger.warning("❌ 未能解析到商品数据。检查 raw_captures/ 目录。")

            # 打印库存
            if inventories:
                logger.info("🏪 门店库存信息:")
                for inv in inventories:
                    logger.info("  - %s: %s", inv.get("store_name", ""),
                                inv.get("stock_status", ""))

            # 写入数据库
            if detail and not dry_run:
                db = SessionLocal()
                try:
                    result = persist_detail(db, detail, dry_run=dry_run)
                    db.commit()
                    if result["spu_id"]:
                        summary["details"] += 1
                    sku_id = result["sku_id"]
                    for inv in inventories:
                        inv["sku_id"] = sku_id
                        inv["spu_id"] = result["spu_id"]
                    inv_count = persist_inventory(db, inventories, dry_run=dry_run)
                    db.commit()
                    summary["inventories"] += inv_count
                    logger.info("💾 数据已写入数据库: spu=%s, sku=%s, inventories=%d",
                                result["spu_id"], result["sku_id"], inv_count)
                except Exception as e:
                    logger.exception("persist failed: %s", e)
                    summary["errors"] += 1
                finally:
                    db.close()

            # 健康检查
            report = CrawlHealthReport()
            if detail:
                for check in validate_detail(detail):
                    report.add(check)
            if inventories and fetch_store_inventory:
                for check in validate_inventories(inventories, min_expected=10):
                    report.add(check)
            # DOM 结构检查（仅在 fetch_store_inventory 时检查库存相关选择器）
            if fetch_store_inventory:
                try:
                    dom_checks = await check_page_structure(page)
                    for check in dom_checks:
                        report.add(check)
                except Exception as e:
                    logger.debug("DOM 结构检查异常: %s", e)

            if report.has_errors:
                send_alert(
                    f"商品 {detail.get('article_no', 'unknown')} 抓取发现健康问题: {report.summary()}",
                    level="error",
                )

            logger.info("📊 %s", report.summary())

            return summary

        # 1. 商品列表（list / all / detail 模式共用）
        category_url = single_url if (mode in ("list", "all", "detail") and single_url) else ""
        listings = await collect_listing(page, category_url=category_url)
        summary["listings"] = len(listings)
        if not listings:
            logger.warning("No listings captured. Check raw_captures/ for hints.")

        # 写入数据库
        db = SessionLocal()
        try:
            for it in listings:
                # 列表页通常没有完整价格，但有 name/article_no，先 upsert SPU
                detail_for_list = {
                    "name": it.get("name", ""),
                    "article_no": it.get("article_no") or it.get("sku", ""),
                    "sku": it.get("sku", ""),
                    "price": it.get("price"),
                    "currency": it.get("currency", ""),
                    "image": it.get("image", ""),
                    "images": [it["image"]] if it.get("image") else [],
                    "description": "",
                    "material": it.get("material", ""),
                }
                try:
                    persist_detail(db, detail_for_list, dry_run=dry_run)
                except Exception as e:
                    logger.warning("persist listing failed: %s | %s", e, it)
                    summary["errors"] += 1
            db.commit()
        finally:
            db.close()

        # 2. 商品详情 — 分批爬取 + 会话轮转 + 反爬检测
        if mode in ("all", "detail") and listings:
            # 增量抓取：加载数据库中已有的商品 article_no
            existing_article_nos = set()
            if incremental:
                existing_article_nos = _load_existing_article_nos()
            skipped_new = 0
            skipped_existing = 0
            crawl_listings = []

            for it in listings:
                article_no = (it.get("article_no") or "").strip().upper()
                url = it.get("url", "")
                # 检查数据库是否已有（且不是断点续爬中的未完成项）
                if incremental and article_no and article_no in existing_article_nos:
                    if not resume:  # resume 模式下不跳过，因为可能需要补充详情
                        skipped_existing += 1
                        continue
                crawl_listings.append(it)

            if incremental and skipped_existing > 0:
                logger.info("📋 增量模式：跳过 %d 个已有商品，待爬取 %d 个",
                            skipped_existing, len(crawl_listings))
            elif not incremental:
                logger.info("📋 全量模式：待爬取 %d 个商品", len(crawl_listings))

            # 断点续爬：加载已完成的 URL
            completed_urls: set = set()
            if resume:
                progress = load_progress()
                if progress:
                    completed_urls = set(progress.get("completed", []))
                    logger.info("🔄 断点续爬: 跳过已完成的 %d 个商品", len(completed_urls))

            consecutive_blocks = 0
            batch_count = 0  # 当前批次已爬数量
            total_to_crawl = len(crawl_listings)

            for idx, it in enumerate(crawl_listings):
                url = it.get("url", "")
                if not url:
                    continue

                # 跳过已完成的
                if url in completed_urls:
                    logger.info("⏭️  [%d/%d] 跳过已完成: %s",
                                idx + 1, total_to_crawl, it.get("article_no", ""))
                    continue

                logger.info("📦 [%d/%d] 开始爬取: %s (%s)",
                            idx + 1, total_to_crawl,
                            it.get("name", "")[:30],
                            it.get("article_no", ""))

                try:
                    # 随机等待（非固定间隔）
                    if idx > 0:
                        await random_sleep(
                            crawler_config.REQUEST_INTERVAL_MIN_SEC,
                            crawler_config.REQUEST_INTERVAL_MAX_SEC,
                            label="商品间隔"
                        )

                    # 每隔 N 个商品插入长暂停
                    if batch_count > 0 and batch_count % crawler_config.LONG_PAUSE_EVERY == 0:
                        await random_sleep(
                            crawler_config.LONG_PAUSE_MIN_SEC,
                            crawler_config.LONG_PAUSE_MAX_SEC,
                            label="长暂停（模拟思考）"
                        )

                    # 每隔 N 个商品回退列表页浏览
                    if batch_count > 0 and batch_count % crawler_config.BROWSE_BACK_EVERY == 0:
                        logger.info("🔄 回退列表页浏览（模拟真人路径）")
                        try:
                            await page.goto(crawler_config.CATEGORY_URL,
                                          wait_until="domcontentloaded", timeout=30000)
                            await asyncio.sleep(random.uniform(2, 4))
                            await smart_scroll(page)
                            await asyncio.sleep(random.uniform(1, 3))
                        except Exception:
                            pass

                    # 拟人化：随机鼠标移动
                    await random_mouse_move(page)

                    # 抓取商品详情（最多重试 2 次）
                    pack = None
                    payloads_for_detect = []
                    for attempt in range(3):
                        try:
                            pack = await collect_detail(page, it, fetch_store_inventory)
                            if pack:
                                payloads_for_detect = pack.get("payloads", [])
                                break
                            if attempt < 2:
                                logger.warning("⚠️  第 %d 次尝试未获取到数据，重试中...", attempt + 1)
                                await random_sleep(2, 5, label="重试等待")
                                await random_mouse_move(page)
                        except Exception as retry_err:
                            logger.warning("⚠️  第 %d 次尝试异常: %s", attempt + 1, retry_err)
                            if attempt < 2:
                                await random_sleep(3, 8, label="异常恢复等待")
                            else:
                                raise

                    if not pack:
                        logger.warning("⚠️  3次尝试均未获取到数据: %s", url)
                        continue

                    detail = pack["detail"]
                    inventories = pack["inventories"]

                    # 反爬检测：使用实际捕获的 payloads
                    is_blocked, block_reason = await detect_block(page, payloads_for_detect)
                    if is_blocked:
                        consecutive_blocks += 1
                        logger.error("🚫 检测到反爬拦截: %s", block_reason)
                        summary["errors"] += 1

                        if consecutive_blocks >= crawler_config.MAX_CONSECUTIVE_BLOCKS:
                            logger.error("🚫 连续 %d 次被拦截，停止爬取并保存进度",
                                         consecutive_blocks)
                            save_progress(crawl_listings, completed_urls)
                            break

                        # 等待冷却后刷新会话重试
                        logger.info("⏳ 反爬冷却: 等待 %d 秒后刷新会话重试...",
                                    crawler_config.BLOCK_COOLDOWN_SEC)
                        await asyncio.sleep(crawler_config.BLOCK_COOLDOWN_SEC)
                        page = await refresh_session(context, page)

                        # 再次尝试（使用新会话）
                        pack_retry = await collect_detail(page, it, fetch_store_inventory)
                        if pack_retry:
                            payloads_retry = pack_retry.get("payloads", [])
                            is_blocked2, _ = await detect_block(page, payloads_retry)
                            if not is_blocked2:
                                pack = pack_retry
                                detail = pack["detail"]
                                inventories = pack["inventories"]
                            else:
                                logger.error("🚫 刷新会话后仍被拦截，跳过此商品")
                                continue
                        else:
                            continue

                    consecutive_blocks = 0  # 成功则重置计数

                    # 写入前验证：跳过严重无效数据
                    if not dry_run and not is_valid_detail_for_write(detail):
                        logger.warning("⚠️  数据验证未通过，跳过写入: %s",
                                       detail.get("article_no", ""))
                        summary["errors"] += 1
                        completed_urls.add(url)  # 标记为已完成，避免反复尝试
                        batch_count += 1
                        if batch_count >= crawler_config.BATCH_SIZE:
                            logger.info("📋 达到批次上限（含跳过），刷新会话...")
                            save_progress(crawl_listings, completed_urls)
                            await random_sleep(
                                crawler_config.BATCH_COOLDOWN_MIN_SEC,
                                crawler_config.BATCH_COOLDOWN_MAX_SEC,
                                label="批次冷却"
                            )
                            page = await refresh_session(context, page)
                            batch_count = 0
                        continue

                    # 写入数据库
                    db = SessionLocal()
                    try:
                        result = persist_detail(db, detail, dry_run=dry_run)
                        db.commit()
                        if result["spu_id"]:
                            summary["details"] += 1
                        sku_id = result["sku_id"]
                        for inv in inventories:
                            inv["sku_id"] = sku_id
                            inv["spu_id"] = result["spu_id"]
                        inv_count = persist_inventory(db, inventories, dry_run=dry_run)
                        db.commit()
                        summary["inventories"] += inv_count
                        logger.info("✅ 已入库: %s (库存 %d)",
                                    detail.get("article_no", ""), inv_count)
                    finally:
                        db.close()

                    # 标记完成
                    completed_urls.add(url)
                    batch_count += 1

                    # 分批爬取：达到批次上限时刷新会话
                    if batch_count >= crawler_config.BATCH_SIZE:
                        logger.info("📋 已爬取 %d 个商品，达到批次上限，刷新会话...",
                                    batch_count)
                        save_progress(crawl_listings, completed_urls)

                        # 冷却等待
                        await random_sleep(
                            crawler_config.BATCH_COOLDOWN_MIN_SEC,
                            crawler_config.BATCH_COOLDOWN_MAX_SEC,
                            label="批次冷却"
                        )

                        # 刷新会话
                        page = await refresh_session(context, page)
                        batch_count = 0

                except Exception as e:
                    logger.exception("detail crawl failed: %s", e)
                    summary["errors"] += 1

            # 保存最终进度
            save_progress(crawl_listings, completed_urls)
            logger.info("📊 爬取完成: %d/%d 商品已入库",
                        len(completed_urls), len(crawl_listings))

    return summary


def _health_check() -> int:
    """运行健康检查，验证运行环境是否就绪。

    检查项：
    1. Python 依赖是否安装
    2. 数据库是否可连接
    3. CDP 端口是否可用（Chrome 是否启动）
    4. 数据库中已有数据统计
    """
    import platform
    print("=" * 60)
    print("LV 爬虫健康检查")
    print("=" * 60)

    all_ok = True

    # 1. Python 环境
    print(f"\n[1/4] Python 版本: {platform.python_version()}")
    try:
        import playwright
        print(f"  ✅ Playwright: 已安装")
    except ImportError:
        print("  ❌ Playwright: 未安装")
        all_ok = False

    try:
        import sqlalchemy
        print(f"  ✅ SQLAlchemy: 已安装")
    except ImportError:
        print("  ❌ SQLAlchemy: 未安装")
        all_ok = False

    # 2. 数据库
    print(f"\n[2/4] 数据库:")
    try:
        from database import engine
        from sqlalchemy import text
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
            print("  ✅ 连接: 正常")
            from models.sku import SPU
            from database import SessionLocal
            db = SessionLocal()
            total = db.query(SPU).filter(SPU.brand_id == "LV").count()
            print(f"  ✅ LV商品: {total} 个")
            db.close()
    except Exception as e:
        print(f"  ❌ 连接失败: {e}")
        all_ok = False

    # 3. CDP 连接
    print(f"\n[3/4] Chrome CDP ({crawler_config.CDP_ENDPOINT}):")
    try:
        import urllib.request
        resp = urllib.request.urlopen(crawler_config.CDP_ENDPOINT + "/json/version", timeout=5)
        import json
        data = json.loads(resp.read())
        print(f"  ✅ 连接: 正常")
        print(f"  ✅ 浏览器: {data.get('Browser', 'unknown')[:40]}")
    except Exception as e:
        print(f"  ❌ 连接失败: {e}")
        print("     请先启动 Chrome:")
        print('       open -n -a "Google Chrome" --args --remote-debugging-port=9333')
        print("     然后访问 https://jp.louisvuitton.com 完成验证")
        all_ok = False

    # 4. 配置检查
    print(f"\n[4/4] 配置:")
    print(f"  分类URL: {crawler_config.CATEGORY_URL[:60]}...")
    print(f"  请求间隔: {crawler_config.REQUEST_INTERVAL_MIN_SEC}-{crawler_config.REQUEST_INTERVAL_MAX_SEC}秒（随机）")
    print(f"  详情页等待: {crawler_config.DETAIL_PAGE_WAIT_MS}ms")
    print(f"  批次大小: {crawler_config.BATCH_SIZE} 个/批")
    print(f"  批次冷却: {crawler_config.BATCH_COOLDOWN_MIN_SEC}-{crawler_config.BATCH_COOLDOWN_MAX_SEC}秒")
    print(f"  反爬冷却: {crawler_config.BLOCK_COOLDOWN_SEC}秒")
    print(f"  干运行: {'是' if crawler_config.DRY_RUN else '否'}")

    print("\n" + "=" * 60)
    if all_ok:
        print("✅ 所有检查通过，可以开始抓取")
        print("   启动命令: venv/bin/python3.11 -m crawler.lv_crawler --mode all")
        return 0
    else:
        print("⚠️  存在问题，请检查后再运行")
        return 1


def main() -> int:
    parser = argparse.ArgumentParser(description="LV 日本官网数据采集")
    parser.add_argument(
        "--mode",
        choices=["list", "detail", "all", "single"],
        default="all",
        help="list=仅列表页；detail=列表+详情；all=详情+库存；single=单个URL（需配合 --url）",
    )
    parser.add_argument(
        "--url",
        type=str,
        default="",
        help="single 模式下的目标 URL",
    )
    parser.add_argument(
        "--launch",
        action="store_true",
        help="启动独立 Chrome 浏览器（而非 CDP 接管），适合首次测试",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="只解析与打印，不写库",
    )
    parser.add_argument(
        "--store-inventory",
        action="store_true",
        help="抓取门店库存（较慢，每个商品增加 30-60 秒）",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="断点续爬：从上次中断处继续（读取 crawl_progress.json）",
    )
    parser.add_argument(
        "--health-check",
        action="store_true",
        help="运行健康检查，验证环境是否就绪",
    )
    parser.add_argument(
        "--no-incremental",
        action="store_true",
        help="禁用增量模式：重新抓取所有商品（默认启用增量模式，跳过已有商品）",
    )
    args = parser.parse_args()

    if args.health_check:
        return _health_check()

    dry_run = args.dry_run or crawler_config.DRY_RUN
    start = time.time()
    summary = asyncio.run(run(args.mode, dry_run, args.url, args.launch,
                              args.store_inventory, args.resume,
                              not args.no_incremental))
    elapsed = time.time() - start
    logger.info(
        "Done in %.1fs | listings=%d details=%d inventories=%d errors=%d",
        elapsed,
        summary["listings"],
        summary["details"],
        summary["inventories"],
        summary["errors"],
    )
    return 0 if summary["errors"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
