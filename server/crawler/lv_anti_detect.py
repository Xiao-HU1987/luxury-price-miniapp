"""
LV 反检测爬虫 — 方案C: 命令行启动Chrome + Playwright connect_over_cdp

核心设计：
  - 用命令行直接启动 Chrome（非 Playwright 启动，避免自动化标记）
  - 暴露 --remote-debugging-port=9333 供 Playwright 连接
  - Playwright 通过 connect_over_cdp 连接到已运行的 Chrome
  - Chrome 使用真实 Profile 副本（含cookies/历史）
  - 模拟真人操作节奏（随机等待、滚动、停顿）

反检测策略：
  1. Chrome 由命令行启动（非Playwright），Akamai 无法识别自动化
  2. 使用真实 Chrome Profile（含cookies/浏览历史）
  3. 真人节奏操作（间隔 20-45s / SKU，批次冷却 10-18min）
"""

import argparse
import asyncio
import json
import logging
import os
import random
import re
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

# 清空代理环境变量
for _proxy_var in ("http_proxy", "https_proxy", "HTTP_PROXY", "HTTPS_PROXY",
                    "all_proxy", "ALL_PROXY"):
    os.environ.pop(_proxy_var, None)

from playwright.async_api import async_playwright, Page, BrowserContext

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("lv_anti_detect")

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_ROOT = BASE_DIR.parent / "data" / "lv"

# ==================================================================
# 反检测脚本（注入到每个页面）
# ==================================================================
STEALTH_SCRIPT = """
// 1. 隐藏 navigator.webdriver
Object.defineProperty(navigator, 'webdriver', { get: () => undefined });

// 2. 隐藏 chrome.runtime (Playwright/CDP 特有暴露)
try {
    if (!window.chrome) Object.defineProperty(window, 'chrome', { value: {} });
    if (!window.chrome.runtime) Object.defineProperty(window.chrome, 'runtime', { value: undefined });
} catch(e) {}

// 3. 修改 navigator.plugins
Object.defineProperty(navigator, 'plugins', {
    get: () => [{
        name: 'Chrome PDF Plugin',
        filename: 'internal-pdf-viewer',
        description: 'Portable Document Format'
    }]
});

// 4. 修改 navigator.languages
Object.defineProperty(navigator, 'languages', {
    get: () => ['ja-JP', 'ja', 'en-US', 'en']
});

// 5. 移除 CDP DOM 标记 ($cdc_*)
const removeCDP = () => {
    for (const key in document) {
        if (key.startsWith('$') && key.includes('cdc')) {
            try { delete document[key]; } catch(e) {}
        }
    }
    if (window.$chrome_cdc) {
        for (const key in window.$chrome_cdc) {
            try { delete window.$chrome_cdc[key]; } catch(e) {}
        }
    }
};
// 定期清理，防止 Playwright 重新注入
setInterval(removeCDP, 500);
removeCDP();

// 6. 覆盖 Object.defineProperty 防止 Akamai 重新设置 webdriver
try {
    const origDefineProperty = Object.defineProperty;
    Object.defineProperty = function(obj, prop, descriptor) {
        if (obj === navigator && prop === 'webdriver') {
            return obj;
        }
        return origDefineProperty.call(this, obj, prop, descriptor);
    };
} catch(e) {}
"""

# ==================================================================
# 门店库存采集配置（JP）
# ==================================================================
STORE_CONFIG = {
    "JP": {
        "panel_text": "ストアの在庫状況を確認する",
        "stock_in_keywords": ["在庫あり"],
        "stock_out_keywords": ["在庫なし"],
        "stock_low_keywords": ["在庫僅少"],
        "address_keywords": ["日本"],
        "cities": ["東京", "大阪", "京都", "横浜", "名古屋", "神戸", "福岡",
                    "札幌", "仙台", "埼玉", "千葉", "広島", "沖縄"],
        "city_coords": {
            "東京": (35.6762, 139.6503),
            "大阪": (34.6937, 135.5023),
            "京都": (35.0116, 135.7681),
            "横浜": (35.4437, 139.6380),
            "名古屋": (35.1815, 136.9066),
            "神戸": (34.6901, 135.1955),
            "福岡": (33.5904, 130.4017),
            "札幌": (43.0618, 141.3545),
            "仙台": (38.2682, 140.8694),
            "埼玉": (35.8617, 139.6455),
            "千葉": (35.6074, 140.1065),
            "広島": (34.3853, 132.4553),
            "沖縄": (26.2125, 127.6811),
        },
        "store_id_regex": r"japan/([^/?#]+)",
        "city_regex": r"([\u4e00-\u9fa5]+[都道府県])\s*\d{3}",
    }
}

# ==================================================================
# 反爬策略参数（真人节奏）
# ==================================================================
BATCH_SIZE = 4
REQUEST_INTERVAL = (20.0, 45.0)
BATCH_COOLDOWN = (600.0, 1080.0)
DETAIL_PAGE_WAIT = 15


# ==================================================================
# 数据存储
# ==================================================================
def _append_jsonl(path: Path, obj: Any):
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=False) + "\n")


def _load_existing_skus(path: Path) -> set:
    if not path.exists():
        return set()
    ids = set()
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            try:
                obj = json.loads(line.strip())
                ids.add(obj.get("sku_id", ""))
            except Exception:
                pass
    return ids


# ==================================================================
# 禁用 backdrop 遮罩（防止拦截点击事件）
# ==================================================================
async def _disable_backdrop(page: Page) -> None:
    """禁用 modal backdrop 的点击拦截。"""
    try:
        await page.evaluate(r"""
            () => {
                const backdrops = document.querySelectorAll('.lv-modal__backdrop, .lv-backdrop');
                for (const b of backdrops) {
                    b.style.pointerEvents = 'none';
                    b.style.opacity = '0.3';
                }
            }
        """)
    except Exception:
        pass


# ==================================================================
# DOM 提取
# ==================================================================
async def _extract_stores_from_dom(page: Page, cfg: Dict) -> List[Dict]:
    return await page.evaluate(r"""
        (cfg) => {
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
                        if (!name.includes(l)) { address = l; break; }
                    }
                }

                const stockEl = card.querySelector('.lv-store-card-detailed__stock');
                let stock_status = '';
                let in_stock = false;
                if (stockEl) {
                    const raw = stockEl.innerText.trim();
                    if (cfg.stock_in_keywords.some(k => raw.includes(k))) {
                        in_stock = true; stock_status = 'in_stock';
                    } else if (cfg.stock_out_keywords.some(k => raw.includes(k))) {
                        in_stock = false; stock_status = 'out_of_stock';
                    } else if (cfg.stock_low_keywords.some(k => raw.includes(k))) {
                        in_stock = true; stock_status = 'low_stock';
                    } else { stock_status = raw; in_stock = false; }
                }

                let store_id = '';
                const linkEl = card.querySelector('a[href*="point-of-sale"]');
                if (linkEl) {
                    const href = linkEl.getAttribute('href') || '';
                    const m = href.match(new RegExp(cfg.store_id_regex));
                    if (m) store_id = m[1] || m[2] || '';
                }
                if (!store_id) store_id = name.substring(0, 64);

                let store_city = '';
                const cityMatch = address.match(new RegExp(cfg.city_regex));
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
    """, {
        "stock_in_keywords": cfg["stock_in_keywords"],
        "stock_out_keywords": cfg["stock_out_keywords"],
        "stock_low_keywords": cfg["stock_low_keywords"],
        "store_id_regex": cfg["store_id_regex"],
        "city_regex": cfg["city_regex"],
    })


def _is_target_store(address: str, cfg: Dict) -> bool:
    return any(k in address for k in cfg["address_keywords"])


# ==================================================================
# 真人模拟滚动
# ==================================================================
async def _scroll_page(page: Page, scroll_style: str = "browse"):
    try:
        max_y = await page.evaluate("document.body.scrollHeight - window.innerHeight")
        if not max_y or max_y < 100:
            return

        if scroll_style == "search":
            await page.evaluate(f"window.scrollTo(0, {max(500, max_y // 3)})")
            await asyncio.sleep(random.uniform(0.6, 1.5))
            await page.evaluate(f"window.scrollTo(0, {max(1000, max_y * 2 // 3)})")
            await asyncio.sleep(random.uniform(0.5, 1.2))
            return

        current = 0
        while current < max_y:
            step = random.randint(180, 420)
            current = min(current + step, max_y)
            await page.evaluate(f"window.scrollTo(0, {current})")
            pause = random.uniform(0.8, 2.0)
            if random.random() < 0.15:
                pause *= random.uniform(2.0, 3.5)
            await asyncio.sleep(pause)
            if random.random() < 0.2 and current > 800:
                back = random.randint(200, 500)
                await page.evaluate(f"window.scrollTo(0, {max(0, current - back)})")
                await asyncio.sleep(random.uniform(0.5, 1.5))
                current = max(0, current - back)

        await page.evaluate(f"window.scrollTo(0, {random.randint(0, 300)})")
        await asyncio.sleep(random.uniform(0.5, 1.2))
    except Exception:
        pass


# ==================================================================
# LV 登录状态检测
# ==================================================================
async def _check_lv_login_status(page: Page) -> bool:
    """检查是否已登录 LV JP 官网。

    检测方法（按优先级）：
    1. CDP Cookie 检测（可访问 HttpOnly cookie）
    2. JS Cookie 检测（document.cookie）
    3. 页面元素检测 - 查找已登录特征
    """
    try:
        # 方法0：通过 Playwright CDP 获取所有 cookie（包括 HttpOnly）
        try:
            all_cookies = await page.context.cookies()
            lv_cookies = [c for c in all_cookies if 'louisvuitton' in (c.get('domain', '') or '').lower()]
            if lv_cookies:
                # 检查是否有认证相关的 cookie
                auth_cookie_names = ['access_token', 'sso', 'auth', 'token', 'AMCV_', 's_ecid', 'akaas_']
                has_auth = any(
                    any(pattern in (c.get('name', '') or '').lower() for pattern in auth_cookie_names)
                    for c in lv_cookies
                )
                if has_auth:
                    logger.info("CDP Cookie检测: 找到 %d 个 LV cookies，含认证cookie", len(lv_cookies))
                    return True
                # 即使没有明确认证cookie，只要有足够多的LV cookie也认为已登录
                if len(lv_cookies) >= 5:
                    logger.info("CDP Cookie检测: 找到 %d 个 LV cookies，认为已登录", len(lv_cookies))
                    return True
        except Exception as e:
            logger.debug("CDP Cookie检测失败: %s", e)

        # JS 端检测
        is_logged_in = await page.evaluate("""
            () => {
                // 方法1：检查 cookie（降低阈值，HttpOnly cookie 不可见）
                try {
                    const cookies = document.cookie;
                    const loginCookiePatterns = [
                        'access_token', 'sso', 'auth', 'token',
                        'lv_', 'LV_', 'AMCV_', 's_ecid',
                        'akaas_', 'ak_bmsc',
                    ];
                    let lvCookieCount = 0;
                    for (const pattern of loginCookiePatterns) {
                        if (cookies.includes(pattern)) lvCookieCount++;
                    }
                    if (lvCookieCount >= 1) return true;
                } catch(e) {}

                // 方法2：查找"ログアウト"(登出)按钮 - 最可靠的已登录标志
                const allElements = document.querySelectorAll('*');
                for (const el of allElements) {
                    const text = (el.innerText || '').trim();
                    if (text === 'ログアウト' || text === 'Logout' || text === 'Sign out') {
                        return true;
                    }
                    if (text.length > 50) continue;
                }

                // 方法3：查找 header 中的账户图标
                const headerIcons = document.querySelectorAll(
                    'header [class*="icon"], header [class*="Icon"], ' +
                    'header [data-testid], [class*="header"] [class*="icon"]'
                );
                for (const el of headerIcons) {
                    const ariaLabel = (el.getAttribute('aria-label') || '').trim();
                    const title = (el.getAttribute('title') || '').trim();
                    if (ariaLabel.includes('マイ') || ariaLabel.includes('アカウント') ||
                        title.includes('マイ') || title.includes('アカウント')) {
                        return true;
                    }
                }

                // 方法4：查找"My LV"或"マイLV"链接
                const allLinks = document.querySelectorAll('a');
                for (const link of allLinks) {
                    const text = (link.innerText || '').trim();
                    const href = (link.getAttribute('href') || '');
                    if ((text.includes('マイLV') || text.includes('My LV')) &&
                        href.includes('/mylv')) {
                        return true;
                    }
                }

                return false;
            }
        """)
        return is_logged_in
    except Exception as e:
        logger.warning("登录状态检查异常: %s", e)
        return False


async def _ensure_logged_in(page: Page, ctx: BrowserContext) -> bool:
    """确保已登录 LV JP 官网，未登录则提示用户手动登录。

    返回 True 表示已登录，False 表示登录失败或超时。
    """
    # 先访问 LV JP 首页
    try:
        await page.goto("https://jp.louisvuitton.com/jpn-jp/homepage",
                        wait_until="domcontentloaded", timeout=30000)
        await page.wait_for_timeout(3000)
    except Exception as e:
        logger.warning("访问 LV JP 首页失败: %s", e)

    # 检查登录状态
    logged_in = await _check_lv_login_status(page)
    if logged_in:
        logger.info("✅ LV JP 已登录")
        return True

    # 未登录，提示用户
    logger.warning("=" * 60)
    logger.warning("⚠️  LV JP 官网未登录！")
    logger.warning("门店库存查询需要登录账号，请在 Chrome 浏览器中手动登录：")
    logger.warning("1. 浏览器窗口已打开 LV JP 首页")
    logger.warning("2. 点击右上角「ログイン」按钮")
    logger.warning("3. 输入您的 LV 账号和密码完成登录")
    logger.warning("4. 登录成功后，爬虫将自动继续")
    logger.warning("=" * 60)

    # 等待用户登录（最多等 5 分钟）
    for attempt in range(60):
        await asyncio.sleep(5)
        try:
            logged_in = await _check_lv_login_status(page)
            if logged_in:
                logger.info("✅ 检测到登录成功！继续执行...")
                await page.wait_for_timeout(2000)
                return True
        except Exception:
            pass
        if attempt % 12 == 11:  # 每 60 秒提示一次
            logger.info("等待登录中... (%d/60)", attempt + 1)

    logger.error("登录超时（5分钟），跳过库存采集")
    return False


# ==================================================================
# 门店库存采集（单个SKU）
# ==================================================================
async def collect_store_inventories(
    page: Page,
    ctx: BrowserContext,
    country: str,
    sku_id: str,
) -> List[Dict]:
    cfg = STORE_CONFIG.get(country)
    if not cfg:
        return []

    cities = cfg["cities"]
    city_coords = cfg.get("city_coords", {})
    panel_text = cfg["panel_text"]
    all_stores: Dict[str, Dict] = {}

    try:
        # === 第零步：检查登录状态 ===
        logged_in = await _check_lv_login_status(page)
        if not logged_in:
            logger.warning("[%s] 未登录 LV，跳过库存采集", country)
            return []

        # === 第一步：找到并展开库存面板 ===
        panel_info = await page.evaluate(r"""
            (panelText) => {
                const panels = document.querySelectorAll('.lv-expandable-panel');
                for (const panel of panels) {
                    if ((panel.innerText||'').includes(panelText)) {
                        const btn = panel.querySelector('button[aria-expanded]');
                        return {
                            found: true,
                            isExpanded: btn ? btn.getAttribute('aria-expanded') === 'true' : false,
                        };
                    }
                }
                return { found: false };
            }
        """, panel_text)

        if not panel_info or not panel_info.get("found"):
            logger.warning("[%s] 未找到库存面板", country)
            return []

        await asyncio.sleep(random.uniform(1.5, 4.0))

        if not panel_info.get("isExpanded"):
            panel_btn = page.locator(f'.lv-expandable-panel button[aria-expanded]:has-text("{panel_text}")')
            btn_count = await panel_btn.count()
            if btn_count == 0:
                panel_btn = page.locator(f'button[aria-expanded]:has-text("{panel_text}")')
                btn_count = await panel_btn.count()

            if btn_count > 0:
                try:
                    await panel_btn.first.scroll_into_view_if_needed(timeout=5000)
                    await page.wait_for_timeout(random.randint(800, 2500))
                    await panel_btn.first.click(timeout=5000)
                except Exception:
                    await page.evaluate(r"""
                        (panelText) => {
                            const panels = document.querySelectorAll('.lv-expandable-panel');
                            for (const panel of panels) {
                                if ((panel.innerText||'').includes(panelText)) {
                                    const btn = panel.querySelector('button[aria-expanded]');
                                    if (btn) btn.click();
                                    return;
                                }
                            }
                        }
                    """, panel_text)
            else:
                logger.warning("[%s] 未找到面板展开按钮", country)
                return []

        # 等待面板展开
        await page.wait_for_function(
            """(panelText) => {
                const panels = document.querySelectorAll('.lv-expandable-panel');
                for (const panel of panels) {
                    if ((panel.innerText||'').includes(panelText)) {
                        const content = panel.querySelector('.lv-expandable-panel__content');
                        if (!content) return false;
                        if (content.getAttribute('aria-hidden') === 'true' || content.style.display === 'none') return false;
                        const btn = content.querySelector('.lv-product-locate-in-store__container');
                        if (!btn) return false;
                        const rect = btn.getBoundingClientRect();
                        return rect.width > 0 && rect.height > 0;
                    }
                }
                return false;
            }""",
            arg=panel_text,
            timeout=15000,
        )

        await asyncio.sleep(random.uniform(1.0, 2.5))

        # === 第二步：点击库存按钮打开弹窗 ===
        locate_btn = page.locator('.lv-product-locate-in-store__container')
        if await locate_btn.count() > 0:
            try:
                await locate_btn.first.scroll_into_view_if_needed(timeout=5000)
                await page.wait_for_timeout(random.randint(500, 1500))
                await locate_btn.first.click(timeout=5000)
            except Exception:
                await page.evaluate("""
                    () => {
                        const btn = document.querySelector('.lv-product-locate-in-store__container');
                        if (btn) btn.click();
                    }
                """)
        else:
            logger.warning("[%s] 未找到门店库存按钮", country)
            return []

        # 等待弹窗
        modal_ready = False
        for wait_s in [4, 6, 8]:
            await asyncio.sleep(wait_s)
            has_modal = await page.evaluate("""
                () => {
                    return !!document.querySelector(
                        '.lv-locate-in-store__first-step-modal, .lv-modal__container, #address-search-input, .lv-address-search-form__input'
                    );
                }
            """)
            if has_modal:
                modal_ready = True
                break

        if not modal_ready:
            logger.warning("[%s] 弹窗未加载", country)
            return []

        await asyncio.sleep(random.uniform(2.0, 4.5))

        # === 禁用 backdrop（防止拦截点击事件） ===
        await _disable_backdrop(page)

        # === 第三步：授权地理位置 ===
        try:
            await ctx.grant_permissions(['geolocation'])
        except Exception:
            pass

        # === 第四步：逐个城市搜索 ===
        total_cities = len(cities)
        for city_idx, city in enumerate(cities, 1):
            try:
                if city_idx > 1 and random.random() < 0.35:
                    long_pause = random.uniform(4.0, 10.0)
                    logger.info("[%s] %d/%d城市, 停顿%.1fs", country, city_idx, total_cities, long_pause)
                    await asyncio.sleep(long_pause)
                else:
                    await asyncio.sleep(random.uniform(1.0, 3.5))

                # 回到搜索页
                await page.evaluate("""
                    () => {
                        const first = document.querySelector('.lv-locate-in-store__first-step-modal');
                        const second = document.querySelector('.lv-locate-in-store__second-step-modal');
                        if (first && second) {
                            first.style.display = 'block';
                            second.style.display = 'none';
                        }
                    }
                """)
                await page.wait_for_timeout(random.randint(700, 1600))

                stores: List[Dict] = []

                # 方法1：地理位置搜索
                coords = city_coords.get(city)
                if coords:
                    try:
                        await ctx.set_geolocation({"latitude": coords[0], "longitude": coords[1]})
                        await page.wait_for_timeout(random.randint(500, 1800))

                        geo_btn = page.locator('.lv-store-geolocation__get-button')
                        if await geo_btn.count() > 0:
                            try:
                                await geo_btn.first.scroll_into_view_if_needed(timeout=4000)
                                await page.wait_for_timeout(random.randint(400, 1400))
                            except Exception:
                                pass
                            await geo_btn.first.click(force=True, timeout=5000)

                            # 等待结果
                            for attempt in range(3):
                                try:
                                    timeout_s = 10 + attempt * 7
                                    await page.wait_for_function(
                                        """() => {
                                            const second = document.querySelector('.lv-locate-in-store__second-step-modal');
                                            if (!second) return false;
                                            const cards = second.querySelectorAll('.lv-store-card-detailed');
                                            if (cards.length > 0) return true;
                                            if (second.querySelector('[class*="no-result"], [class*="empty"]')) return true;
                                            return false;
                                        }""",
                                        timeout=timeout_s * 1000,
                                    )
                                    break
                                except Exception:
                                    if attempt < 2:
                                        await page.wait_for_timeout(random.randint(1500, 3500))

                            await asyncio.sleep(random.uniform(1.5, 4.0))
                            stores = await _extract_stores_from_dom(page, cfg)
                    except Exception as geo_e:
                        logger.debug("[%s] 「%s」地理位置搜索异常: %s", country, city, geo_e)

                # 方法2：文本搜索（备选）
                if not stores:
                    try:
                        search_input = page.locator('#address-search-input, .lv-address-search-form__input, input[type="search"]')
                        if await search_input.count() > 0:
                            await search_input.first.click(force=True, timeout=3000)
                            await page.wait_for_timeout(random.randint(400, 1000))

                            # 彻底清空搜索栏（先选中全部再删除，确保清除干净）
                            await search_input.first.click(force=True, timeout=3000)
                            await page.wait_for_timeout(200)
                            # 方式1: fill('') 清空
                            await search_input.first.fill('')
                            await page.wait_for_timeout(300)
                            # 方式2: 再次确认清空（防止Vue组件未同步）
                            await search_input.first.evaluate("el => { el.value = ''; el.dispatchEvent(new Event('input', {bubbles: true})); }")
                            await page.wait_for_timeout(random.randint(300, 800))

                            # 输入城市名（使用 type 模拟真人逐字输入）
                            await search_input.first.type(city, delay=random.randint(80, 180))
                            await page.wait_for_timeout(random.randint(2.5, 5.5))

                            # 选择第一个补全项
                            await page.evaluate("""
                                () => {
                                    const modal = document.querySelector('.lv-modal__content') || document.querySelector('.lv-modal__container');
                                    if (!modal) return;
                                    const sels = modal.querySelectorAll('[class*="suggestion"] li, [role="option"]');
                                    if (sels.length > 0 && sels[0].getBoundingClientRect().width > 0) sels[0].click();
                                }
                            """)
                            await page.wait_for_timeout(random.randint(1.5, 3.0))

                            search_btn = page.locator('.lv-address-search-form__button')
                            if await search_btn.count() > 0:
                                await search_btn.first.click(force=True, timeout=3000)

                            # 等待结果
                            for attempt in range(2):
                                try:
                                    timeout_s = 10 + attempt * 8
                                    await page.wait_for_function(
                                        """() => {
                                            const second = document.querySelector('.lv-locate-in-store__second-step-modal');
                                            if (!second) return false;
                                            if (second.querySelectorAll('.lv-store-card-detailed').length > 0) return true;
                                            if (second.querySelector('[class*="no-result"], [class*="empty"]')) return true;
                                            return false;
                                        }""",
                                        timeout=timeout_s * 1000,
                                    )
                                    break
                                except Exception:
                                    await page.wait_for_timeout(random.randint(2.0, 4.0))

                            await asyncio.sleep(random.uniform(1.5, 3.5))
                            stores = await _extract_stores_from_dom(page, cfg)

                            # 如果当前城市名搜不到结果，尝试去掉「府」「都」后缀重试
                            if len(stores) == 0 and (city.endswith('府') or city.endswith('都')):
                                fallback_city = city.rstrip('府').rstrip('都')
                                logger.info("[%s] 「%s」无结果，尝试用「%s」重试", country, city, fallback_city)
                                # 回到搜索页
                                await page.evaluate("""
                                    () => {
                                        const first = document.querySelector('.lv-locate-in-store__first-step-modal');
                                        const second = document.querySelector('.lv-locate-in-store__second-step-modal');
                                        if (first && second) {
                                            first.style.display = 'block';
                                            second.style.display = 'none';
                                        }
                                    }
                                """)
                                await page.wait_for_timeout(random.randint(700, 1600))

                                # 重新搜索
                                search_input2 = page.locator('.lv-address-search-form__input, input[type="text"]')
                                if await search_input2.count() > 0:
                                    await search_input2.first.click(timeout=3000)
                                    await page.wait_for_timeout(200)
                                    await search_input2.first.fill('')
                                    await page.wait_for_timeout(300)
                                    await search_input2.first.evaluate("el => { el.value = ''; el.dispatchEvent(new Event('input', {bubbles: true})); }")
                                    await page.wait_for_timeout(random.randint(300, 800))
                                    await search_input2.first.type(fallback_city, delay=random.randint(80, 180))
                                    await page.wait_for_timeout(random.randint(2.5, 5.5))

                                    await page.evaluate("""
                                        () => {
                                            const modal = document.querySelector('.lv-modal__content') || document.querySelector('.lv-modal__container');
                                            if (!modal) return;
                                            const sels = modal.querySelectorAll('[class*="suggestion"] li, [role="option"]');
                                            if (sels.length > 0 && sels[0].getBoundingClientRect().width > 0) sels[0].click();
                                        }
                                    """)
                                    await page.wait_for_timeout(random.randint(1.5, 3.0))

                                    search_btn2 = page.locator('.lv-address-search-form__button')
                                    if await search_btn2.count() > 0:
                                        await search_btn2.first.click(timeout=3000)

                                    for attempt in range(2):
                                        try:
                                            timeout_s = 10 + attempt * 8
                                            await page.wait_for_function(
                                                """() => {
                                                    const second = document.querySelector('.lv-locate-in-store__second-step-modal');
                                                    if (!second) return false;
                                                    if (second.querySelectorAll('.lv-store-card-detailed').length > 0) return true;
                                                    if (second.querySelector('[class*="no-result"], [class*="empty"]')) return true;
                                                    return false;
                                                }""",
                                                timeout=timeout_s * 1000,
                                            )
                                            break
                                        except Exception:
                                            await page.wait_for_timeout(random.randint(2.0, 4.0))

                                    await asyncio.sleep(random.uniform(1.5, 3.5))
                                    stores = await _extract_stores_from_dom(page, cfg)
                    except Exception as text_e:
                        logger.debug("[%s] 「%s」文本搜索异常: %s", country, city, text_e)

                # 过滤目标国家门店
                target_stores = [s for s in stores if _is_target_store(s.get('store_address', ''), cfg)]

                # 空结果重试
                if len(stores) == 0 and len(cities) > 1:
                    await asyncio.sleep(random.uniform(3.5, 7.0))
                    stores_retry = await _extract_stores_from_dom(page, cfg)
                    if stores_retry:
                        stores = stores_retry
                        target_stores = [s for s in stores if _is_target_store(s.get('store_address', ''), cfg)]

                for s in target_stores:
                    s["sku"] = sku_id
                    key = s.get("store_id", "") or s.get("store_name", "")
                    if key and key not in all_stores:
                        all_stores[key] = s

                logger.info("[%s] 「%s」[%d/%d]: %d家(目标%d家)",
                            country, city, city_idx, total_cities, len(stores), len(target_stores))

            except Exception as e:
                logger.info("[%s] 搜索 %s 失败: %s", country, city, e)
                await asyncio.sleep(random.uniform(2.0, 5.0))
                continue

    except Exception as e:
        logger.warning("[%s] 门店库存采集异常: %s", country, e)

    result = list(all_stores.values())
    logger.info("[%s] 门店库存采集完成: %d 家门店", country, len(result))
    return result


# ==================================================================
# 主采集流程
# ==================================================================
# CDP 端点
CDP_ENDPOINT = "http://127.0.0.1:9333"
CHROME_EXECUTABLE = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

# 专用 Profile 目录（独立于用户日常 Chrome，避免冲突）
# 与 start_lv_chrome.sh 保持一致
CRAWLER_PROFILE = "/tmp/lv-crawler-profile"


def _launch_chrome_command_line() -> subprocess.Popen:
    """命令行启动 Chrome（带 CDP 端口），不经过 Playwright。

    关键：Chrome 由系统命令启动，不会带 --enable-automation 标记，
    Akamai 无法通过自动化指纹检测。
    """
    import shutil
    REAL_CHROME_PROFILE = os.path.expanduser(
        "~/Library/Application Support/Google/Chrome/Default"
    )

    # 准备专用 Profile（如果不存在则从真实 Profile 复制 cookies）
    cookies_ready = os.path.exists(CRAWLER_PROFILE) and os.path.isfile(
        os.path.join(CRAWLER_PROFILE, "Cookies")
    )
    if not cookies_ready and os.path.isdir(REAL_CHROME_PROFILE):
        logger.info("准备 Chrome Profile（从真实 Profile 复制 cookies）...")
        if os.path.exists(CRAWLER_PROFILE):
            shutil.rmtree(CRAWLER_PROFILE, ignore_errors=True)
        os.makedirs(CRAWLER_PROFILE, exist_ok=True)
        for fname in [
            "Cookies", "Local State", "Preferences",
            "Network", "Local Storage", "Session Storage",
        ]:
            src = os.path.join(REAL_CHROME_PROFILE, fname)
            dst = os.path.join(CRAWLER_PROFILE, fname)
            if os.path.exists(src):
                if os.path.isdir(src):
                    if os.path.exists(dst):
                        shutil.rmtree(dst, ignore_errors=True)
                    shutil.copytree(src, dst, symlinks=True)
                else:
                    shutil.copy2(src, dst)
        logger.info("Chrome Profile 准备完成")

    # 先杀掉占用 9333 端口的旧 Chrome 进程
    os.system("lsof -ti:9333 | xargs kill -9 2>/dev/null")

    # 启动 Chrome（注意：不加 --enable-automation）
    chrome_cmd = [
        CHROME_EXECUTABLE,
        f"--user-data-dir={CRAWLER_PROFILE}",
        "--remote-debugging-port=9333",
        "--no-first-run",
        "--no-default-browser-check",
        "--disable-blink-features=AutomationControlled",
        "--disable-background-networking",
        "--disable-sync",
        "--disable-extensions",
        "--disable-component-update",
        "--disable-default-apps",
        "--disable-breakpad",
        "--disable-crashpad-for-testing",
        "--no-sandbox",
        "--enable-logging=stderr",
        "--v=1",
        "--lang=ja-JP",
        "--no-popup-blocking",
        "about:blank",
    ]

    logger.info("正在启动 Chrome（命令行模式，无 Playwright 启动）...")
    proc = subprocess.Popen(chrome_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    logger.info("Chrome PID=%d，等待 CDP 就绪...", proc.pid)

    # 等待 CDP 端口就绪
    import urllib.request
    for attempt in range(30):
        try:
            with urllib.request.urlopen(CDP_ENDPOINT + "/json/version", timeout=2) as resp:
                if resp.status == 200:
                    logger.info("CDP 端口已就绪")
                    return proc
        except Exception:
            pass
        time.sleep(1)
        if attempt % 5 == 4:
            logger.info("等待 Chrome CDP 就绪... (%d/30)", attempt + 1)

    raise RuntimeError("Chrome CDP 端口未就绪，启动失败")


async def _connect_chrome_via_cdp(pw) -> tuple:
    """通过 connect_over_cdp 连接到已运行的 Chrome。

    返回 (browser, context, page)。
    """
    logger.info("通过 CDP 连接 Chrome: %s", CDP_ENDPOINT)
    browser = await pw.chromium.connect_over_cdp(CDP_ENDPOINT)

    # 获取或创建上下文
    if browser.contexts:
        ctx = browser.contexts[0]
    else:
        ctx = await browser.new_context(locale="ja-JP", timezone_id="Asia/Tokyo")

    # 强制设置语言和时区（通过 CDP target 配置）
    try:
        await browser.new_context(locale="ja-JP", timezone_id="Asia/Tokyo")
        # 注意：如果已有 context，不能修改 timezone，需要新建
    except Exception:
        pass

    # 创建新页面（避免复用已有页面带来的污染）
    page = await ctx.new_page()
    await page.set_viewport_size({"width": 1440, "height": 900})

    # 注入反检测脚本
    try:
        await ctx.add_init_script(STEALTH_SCRIPT)
        logger.info("反检测脚本已注入")
    except Exception:
        pass

    # 验证反检测效果
    webdriver_val = await page.evaluate("navigator.webdriver")
    chrome_runtime = await page.evaluate("typeof window.chrome !== 'undefined'")
    logger.info(
        "反检测验证: navigator.webdriver=%s, chrome.runtime=%s",
        webdriver_val, chrome_runtime,
    )

    return browser, ctx, page


# ==================================================================
# 慢速真人模拟参数（方案1）
# ==================================================================
TRUST_BUILD_TIME = 180  # 信任建立阶段：至少3分钟
SKU_NAV_WAIT = (20.0, 35.0)  # 每个SKU页面加载等待
SKU_INTERVAL = (40.0, 70.0)  # SKU之间间隔（模拟真人阅读时间）
MICRO_BREAK_EVERY = 3  # 每3个SKU一次微休息
MICRO_BREAK = (180.0, 300.0)  # 微休息时长（3-5分钟）
RESET_EVERY = 8  # 每8个SKU重置会话
RESET_BREAK = (300.0, 480.0)  # 重置休息时长（5-8分钟）
BLOCK_RECOVERY = (600.0, 900.0)  # 被拦截后恢复时间（10-15分钟）
MAX_CONSECUTIVE_BLOCKS = 2  # 连续被拦截次数上限

# Chrome Profile 路径
REAL_CHROME_PROFILE = os.path.expanduser(
    "~/Library/Application Support/Google/Chrome/Default"
)


def _prepare_chrome_profile() -> str:
    """准备 Chrome Profile（从真实 Profile 复制关键数据）"""
    import shutil
    cookies_ready = os.path.exists(CRAWLER_PROFILE) and os.path.isfile(
        os.path.join(CRAWLER_PROFILE, "Cookies")
    )
    if not cookies_ready and os.path.isdir(REAL_CHROME_PROFILE):
        logger.info("准备 Chrome Profile（从真实 Profile 复制数据）...")
        if os.path.exists(CRAWLER_PROFILE):
            shutil.rmtree(CRAWLER_PROFILE, ignore_errors=True)
        os.makedirs(CRAWLER_PROFILE, exist_ok=True)
        for fname in [
            "Cookies", "Local State", "Preferences",
            "Network", "Local Storage", "Session Storage",
        ]:
            src = os.path.join(REAL_CHROME_PROFILE, fname)
            dst = os.path.join(CRAWLER_PROFILE, fname)
            if os.path.exists(src):
                if os.path.isdir(src):
                    if os.path.exists(dst):
                        shutil.rmtree(dst, ignore_errors=True)
                    shutil.copytree(src, dst, symlinks=True)
                else:
                    shutil.copy2(src, dst)
        logger.info("Chrome Profile 准备完成")
    return CRAWLER_PROFILE


async def _trust_building_phase(page: Page, ctx: BrowserContext):
    """信任建立阶段：模拟真人首次访问 LV 官网的行为
    
    在开始任何爬虫操作前，先用 3-5 分钟模拟真实用户浏览：
    1. 访问首页，等待加载
    2. 慢速滚动（模拟看内容）
    3. 随机点击一些导航链接
    4. 返回首页
    """
    logger.info("=" * 60)
    logger.info("【信任建立阶段】模拟真人访问 LV 官网...")
    logger.info("=" * 60)

    # 1. 访问首页
    logger.info("访问 LV JP 首页...")
    await page.goto("https://jp.louisvuitton.com/jpn-jp/homepage",
                    wait_until="domcontentloaded", timeout=45000)
    await page.wait_for_timeout(5000)

    # 2. 慢速滚动 3 轮
    for round_num in range(3):
        logger.info("首页滚动第 %d 轮...", round_num + 1)
        max_y = await page.evaluate("document.body.scrollHeight - window.innerHeight")
        if max_y and max_y > 200:
            # 慢速分段滚动
            steps = random.randint(4, 7)
            for step in range(steps):
                target_y = int(max_y * (step + 1) / steps)
                await page.evaluate(f"window.scrollTo(0, {target_y})")
                await asyncio.sleep(random.uniform(1.0, 2.5))
            
            # 回到顶部
            await page.evaluate("window.scrollTo(0, 0)")
            await asyncio.sleep(random.uniform(0.5, 1.0))
        
        await asyncio.sleep(random.uniform(1.5, 3.0))

    # 3. 随机点击一个分类链接（模拟真人浏览）
    try:
        nav_links = await page.evaluate("""
            () => {
                const links = document.querySelectorAll('a[href*="/jpn-jp/"]');
                const results = [];
                for (const l of links) {
                    const href = l.getAttribute('href') || '';
                    const text = (l.innerText || '').trim();
                    if (href && text && href !== '/jpn-jp/homepage' && 
                        !href.includes('/products/') && results.length < 5) {
                        results.push({href, text});
                    }
                }
                return results;
            }
        """)
        if nav_links:
            chosen = random.choice(nav_links[:3])
            logger.info("点击导航: %s -> %s", chosen['text'], chosen['href'])
            await page.goto(f"https://jp.louisvuitton.com{chosen['href']}",
                            wait_until="domcontentloaded", timeout=30000)
            await page.wait_for_timeout(3000)
            await _scroll_page(page, "browse")
    except Exception as e:
        logger.debug("导航点击异常: %s", e)

    # 4. 返回首页
    await page.goto("https://jp.louisvuitton.com/jpn-jp/homepage",
                    wait_until="domcontentloaded", timeout=30000)
    await page.wait_for_timeout(3000)

    # 5. 最终等待
    remaining = TRUST_BUILD_TIME - 30  # 已用约30秒
    if remaining > 0:
        logger.info("信任建立：再等待 %.0f 秒...", remaining)
        await asyncio.sleep(remaining)

    logger.info("✅ 信任建立完成")


async def _human_like_navigate(page: Page, url: str) -> bool:
    """真人风格的页面导航
    
    返回：是否成功加载
    """
    try:
        # 导航到目标页面
        resp = await page.goto(url, wait_until="domcontentloaded", timeout=45000)
        if resp:
            logger.info("HTTP状态: %d", resp.status)
        
        # 模拟真人阅读时间：20-35秒
        nav_wait = random.uniform(*SKU_NAV_WAIT)
        logger.info("模拟阅读等待 %.1f 秒...", nav_wait)
        await asyncio.sleep(nav_wait)
        
        # 检查是否被拦截
        body_text = await page.evaluate(
            "document.body ? document.body.innerText.substring(0, 300) : ''"
        )
        if "Access denied" in (body_text or ""):
            return False
        
        # 检查是否有价格元素
        try:
            has_price = await page.wait_for_function(
                r"""() => {
                    const prices = document.querySelectorAll('.lv-price');
                    if (prices.length > 0) return /\d/.test(prices[0].innerText || '');
                    return false;
                }""",
                timeout=15000,
            )
            if not has_price:
                logger.warning("价格元素未找到")
                return False
        except Exception:
            logger.warning("等待价格元素超时")
            return False
        
        logger.info("✅ 页面加载成功")
        return True
        
    except Exception as e:
        logger.error("导航异常: %s", e)
        return False


async def _check_page_accessible(page: Page) -> bool:
    """检查当前页面是否可访问（无 Akamai 拦截）"""
    try:
        body_text = await page.evaluate(
            "document.body ? document.body.innerText.substring(0, 300) : ''"
        )
        return "Access denied" not in (body_text or "")
    except Exception:
        return False


async def _go_home_and_browse(page: Page, ctx: BrowserContext):
    """回到首页浏览（微休息时的行为）"""
    try:
        await page.goto("https://jp.louisvuitton.com/jpn-jp/homepage",
                        wait_until="domcontentloaded", timeout=30000)
        await page.wait_for_timeout(3000)
        await _scroll_page(page, "browse")
        
        # 随机点击一个链接
        try:
            links = await page.evaluate("""
                () => {
                    const links = document.querySelectorAll('a[href*="/jpn-jp/"]');
                    const results = [];
                    for (const l of links) {
                        const href = l.getAttribute('href') || '';
                        const text = (l.innerText || '').trim();
                        if (href && text && !href.includes('/products/') && results.length < 5) {
                            results.push({href, text});
                        }
                    }
                    return results;
                }
            """)
            if links:
                chosen = random.choice(links[:3])
                await page.goto(f"https://jp.louisvuitton.com{chosen['href']}",
                                wait_until="domcontentloaded", timeout=30000)
                await page.wait_for_timeout(2000)
                await _scroll_page(page, "browse")
        except Exception:
            pass
            
        # 回到首页
        await page.goto("https://jp.louisvuitton.com/jpn-jp/homepage",
                        wait_until="domcontentloaded", timeout=30000)
    except Exception as e:
        logger.debug("首页浏览异常: %s", e)


async def crawl_jp_men_skus(sku_file: str, limit: int = 0, reuse_chrome: bool = False):
    """CDP 连接方式采集 JP 男士 SKU 门店库存

    核心策略：
    1. 连接已由命令行启动的 Chrome（connect_over_cdp，无自动化标记）
    2. 每个 SKU 间隔 40-70 秒（真人阅读节奏）
    3. 每 3 个 SKU 微休息 3-5 分钟
    4. 被拦截后冷却 10-15 分钟
    5. 跳过重定向循环/404/410 的异常 SKU
    """
    country = "JP"
    base_dir = DATA_ROOT / country
    base_dir.mkdir(parents=True, exist_ok=True)

    with open(sku_file, "r", encoding="utf-8") as f:
        sku_list = json.load(f)
    logger.info("SKU白名单: %d 个", len(sku_list))

    inv_path = base_dir / f"inventories_{country}.jsonl"
    existing = _load_existing_skus(inv_path)
    logger.info("已有库存SKU: %d 个, 将跳过", len(existing))

    to_process = [s for s in sku_list if s["sku"] not in existing]
    if limit > 0:
        to_process = to_process[:limit]
    logger.info("实际需处理: %d 个 SKU", len(to_process))

    if not to_process:
        logger.info("无待处理SKU")
        return

    consecutive_blocks = 0
    processed = 0
    success = 0
    no_panel_skus = []
    bad_skus = []

    async with async_playwright() as pw:
        # 检查 CDP 是否已就绪，未就绪则启动 Chrome
        import urllib.request
        cdp_ready = False
        try:
            with urllib.request.urlopen(CDP_ENDPOINT + "/json/version", timeout=3) as resp:
                if resp.status == 200:
                    cdp_ready = True
                    logger.info("CDP 已就绪，复用已有 Chrome")
        except Exception:
            pass

        if not cdp_ready:
            if reuse_chrome:
                logger.error("CDP 未就绪！请先启动 Chrome（bash start_lv_chrome.sh）")
                return
            logger.info("CDP 未就绪，启动 Chrome...")
            _launch_chrome_command_line()
        else:
            logger.info("连接 Chrome CDP: %s", CDP_ENDPOINT)

        browser = await pw.chromium.connect_over_cdp(CDP_ENDPOINT)

        if browser.contexts:
            ctx = browser.contexts[0]
        else:
            ctx = await browser.new_context(
                locale="ja-JP", timezone_id="Asia/Tokyo",
                viewport={"width": 1440, "height": 900},
            )

        if ctx.pages:
            page = ctx.pages[0]
        else:
            page = await ctx.new_page()

        # === 登录检查 ===
        login_ok = await _ensure_logged_in(page, ctx)
        if not login_ok:
            logger.warning("未登录 LV JP，库存采集将跳过（但会继续采集商品信息）")

        # === 信任建立阶段 ===
        await _trust_building_phase(page, ctx)

        # === 主采集循环 ===
        for i, item in enumerate(to_process, 1):
            sku_id = item["sku"]
            product_url = item.get(
                "url", f"https://jp.louisvuitton.com/jpn-jp/products/-/{sku_id}"
            )

            # 微休息（每3个SKU）
            if processed > 0 and processed % MICRO_BREAK_EVERY == 0:
                mb = random.uniform(*MICRO_BREAK)
                logger.info("=== 微休息 %.0f 秒 (已处理 %d) ===", mb, processed)
                await _go_home_and_browse(page, ctx)
                await asyncio.sleep(mb)
                logger.info("微休息结束")

            # SKU 间隔
            if processed > 0:
                interval = random.uniform(*SKU_INTERVAL)
                logger.info("SKU间隔 %.1f 秒", interval)
                await asyncio.sleep(interval)

            logger.info("=" * 60)
            logger.info("=== %d/%d %s ===", i, len(to_process), sku_id)
            logger.info("=" * 60)

            try:
                # CDP 方式导航（无自动化标记，商品页可正常访问）
                try:
                    resp = await page.goto(product_url, wait_until="domcontentloaded", timeout=45000)
                except Exception as nav_e:
                    err = str(nav_e)
                    if "TOO_MANY_REDIRECTS" in err:
                        logger.warning("[%s] 重定向循环，跳过", sku_id)
                        bad_skus.append({"sku_id": sku_id, "reason": "redirect_loop"})
                        processed += 1
                        await page.goto("https://jp.louisvuitton.com/jpn-jp/homepage",
                                        wait_until="domcontentloaded", timeout=30000)
                        await asyncio.sleep(2)
                        continue
                    logger.error("[%s] 导航异常: %s", sku_id, err)
                    consecutive_blocks += 1
                    if consecutive_blocks >= MAX_CONSECUTIVE_BLOCKS:
                        recovery = random.uniform(*BLOCK_RECOVERY)
                        logger.info("连续拦截，恢复等待 %.0f 秒...", recovery)
                        await asyncio.sleep(recovery)
                        consecutive_blocks = 0
                    processed += 1
                    continue

                status = resp.status if resp else None
                if status == 404:
                    logger.warning("[%s] 404 页面，跳过", sku_id)
                    bad_skus.append({"sku_id": sku_id, "reason": "404"})
                    processed += 1
                    continue
                if status == 410:
                    logger.warning("[%s] 410 Gone，商品已下架，跳过", sku_id)
                    bad_skus.append({"sku_id": sku_id, "reason": "410_gone"})
                    processed += 1
                    continue
                if status and status >= 400:
                    logger.warning("[%s] HTTP %s，可能被拦截", sku_id, status)
                    consecutive_blocks += 1
                    if consecutive_blocks >= MAX_CONSECUTIVE_BLOCKS:
                        recovery = random.uniform(*BLOCK_RECOVERY)
                        logger.info("连续拦截，恢复等待 %.0f 秒...", recovery)
                        await asyncio.sleep(recovery)
                        consecutive_blocks = 0
                    processed += 1
                    continue

                consecutive_blocks = 0
                logger.info("[%s] 页面加载成功 (HTTP %s)", sku_id, status)

                # 模拟真人浏览（慢速滚动）
                await _scroll_page(page, "browse")
                await asyncio.sleep(random.uniform(3.0, 6.0))

                # 采集库存
                stores = await collect_store_inventories(page, ctx, country, sku_id)

                if stores:
                    for store in stores:
                        record = {
                            "sku_id": sku_id,
                            "country": country,
                            "source_url": page.url,
                            **store,
                            "crawled_at": datetime.now().isoformat(),
                        }
                        _append_jsonl(inv_path, record)
                    logger.info("[%s] 保存 %d 家门店库存", sku_id, len(stores))
                    success += 1
                else:
                    no_panel_path = base_dir / f"no_panel_skus_{country}.jsonl"
                    _append_jsonl(no_panel_path, {"sku_id": sku_id, "country": country})
                    no_panel_skus.append(sku_id)
                    logger.info("[%s] 无面板或零库存", sku_id)

                processed += 1

            except Exception as e:
                logger.error("[%s] 采集异常: %s", sku_id, e)
                processed += 1
                await asyncio.sleep(random.uniform(10, 30))

        # 保存无面板SKU
        if no_panel_skus:
            no_panel_path = base_dir / f"no_panel_skus_{country}.jsonl"
            with open(no_panel_path, "a", encoding="utf-8") as f:
                for sku_id in no_panel_skus:
                    f.write(
                        json.dumps(
                            {
                                "sku_id": sku_id,
                                "country": country,
                                "crawled_at": datetime.now().isoformat(),
                            },
                            ensure_ascii=False,
                        )
                        + "\n"
                    )

        # 保存异常SKU
        if bad_skus:
            bad_path = base_dir / f"bad_skus_{country}.jsonl"
            with open(bad_path, "a", encoding="utf-8") as f:
                for item in bad_skus:
                    item["country"] = country
                    item["crawled_at"] = datetime.now().isoformat()
                    f.write(json.dumps(item, ensure_ascii=False) + "\n")

        logger.info("=" * 60)
        logger.info("=== 采集完成 ===")
        logger.info(
            "总处理: %d, 成功: %d, 无面板: %d, 异常: %d",
            processed, success, len(no_panel_skus), len(bad_skus),
        )
        logger.info("=" * 60)

        await browser.close()


# ==================================================================
# 入口
# ==================================================================
def main():
    parser = argparse.ArgumentParser(
        description="LV CDP 连接方式采集 — 命令行启动Chrome + connect_over_cdp"
    )
    parser.add_argument("--sku-file", required=True, help="SKU白名单JSON文件")
    parser.add_argument("--limit", type=int, default=0, help="处理数量限制")
    parser.add_argument(
        "--trust-only",
        action="store_true",
        help="仅运行信任建立阶段（测试用，不采集数据）",
    )
    parser.add_argument(
        "--reuse-chrome",
        action="store_true",
        help="复用已有 Chrome 实例（不重启，保留登录状态）",
    )
    args = parser.parse_args()

    sku_file = args.sku_file
    if not os.path.isabs(sku_file):
        sku_file = str(BASE_DIR.parent / sku_file)

    if args.trust_only:
        # 仅测试信任建立（CDP 连接方式）
        async def test_trust():
            from playwright.async_api import async_playwright
            async with async_playwright() as pw:
                browser = await pw.chromium.connect_over_cdp(CDP_ENDPOINT)
                ctx = browser.contexts[0] if browser.contexts else await browser.new_context(
                    locale="ja-JP", timezone_id="Asia/Tokyo")
                page = await ctx.new_page()
                await _trust_building_phase(page, ctx)

                # 测试访问第一个 SKU
                if os.path.exists(sku_file):
                    with open(sku_file, "r") as f:
                        sku_list = json.load(f)
                    if sku_list:
                        test_sku = sku_list[0]["sku"]
                        test_url = sku_list[0].get("url", f"https://jp.louisvuitton.com/jpn-jp/products/-/{test_sku}")
                        logger.info("测试访问 SKU: %s", test_sku)
                        try:
                            resp = await page.goto(test_url, wait_until="domcontentloaded", timeout=45000)
                            logger.info("访问结果: HTTP %s -> %s", resp.status if resp else "None", page.url)
                        except Exception as e:
                            logger.info("访问异常: %s", str(e).split("\n")[0])
                await browser.close()

        asyncio.run(test_trust())
    else:
        asyncio.run(crawl_jp_men_skus(sku_file, args.limit, args.reuse_chrome))


if __name__ == "__main__":
    main()
