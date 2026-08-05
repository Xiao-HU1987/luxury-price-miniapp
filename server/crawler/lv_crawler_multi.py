"""LV 多国家官网爬虫统一入口（日本 JP / 韩国 KR / 中国大陆 CN）

支持抓取：
  * 商品列表（分类页）
  * 商品详情（含名称、货号、图片）
  * 官网价格
  * 门店库存（仅 KR / JP，中国大陆通常不公开门店库存接口）

与 lv_crawler.py 相同的工作方式：
  * 必须通过 CDP 接管日常使用的 Chrome，绕过 Akamai WAF
  * 拦截浏览器发出的所有 louisvuitton.com 响应 → 直接从 JSON 提取

标准启动流程（每次 Chrome 重启后都要执行 1-3）：
  1. 关闭所有 Chrome（Cmd+Q）
  2. 执行：
       open -n -a "Google Chrome" --args --remote-debugging-port=9333 \\
           --proxy-server="http://127.0.0.1:7890"
  3. 打开 https://kr.louisvuitton.com 或 https://cn.louisvuitton.com ，
     手动通过验证码/人机验证（如有），保留 Chrome 不要关。
  4. 跑爬虫（先单测一个详情页确认解析正常）：
       cd server/
       # 韩国 单商品详情测试
       venv/bin/python -m crawler.lv_crawler_multi --country KR \\
           --mode single --url "https://kr.louisvuitton.com/kor-kr/products/..."
       # 韩国 列表抓取
       venv/bin/python -m crawler.lv_crawler_multi --country KR --mode list
       # 韩国 全量（列表 + 所有详情 + 库存）
       venv/bin/python -m crawler.lv_crawler_multi --country KR --mode all
       # 中国大陆 列表抓取
       venv/bin/python -m crawler.lv_crawler_multi --country CN --mode list

产物：
  data/lv/{country}/products_{country}.jsonl      # 解析后的商品数据（每行一个 JSON）
  data/lv/{country}/inventories_{country}.jsonl   # 门店库存数据（KR/JP 才有）
  data/lv/{country}/raw_captures/                 # 所有匹配关键词的原始响应（便于调试解析器）
"""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import random
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

# 关键：清空代理环境变量，避免 CDP 连接（127.0.0.1:9333）被系统代理拦截
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

from crawler import config as crawler_config  # noqa: E402
from crawler.brands import get_brand  # noqa: E402
from crawler.lv_parser import (  # noqa: E402
    is_lv_response,
    looks_like_product_data,
    parse_response,
    extract_inventory_items,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("lv_crawler_multi")

# ==================================================================
# 目录初始化
# ==================================================================
DATA_ROOT = BASE_DIR.parent / "data" / "lv"


def _ensure_dirs(country: str) -> Dict[str, Path]:
    root = DATA_ROOT / country
    raw_dir = root / "raw_captures"
    raw_dir.mkdir(parents=True, exist_ok=True)
    return {
        "root": root,
        "raw": raw_dir,
        "products": root / f"products_{country}.jsonl",
        "inventories": root / f"inventories_{country}.jsonl",
        "slugs": root / f"slugs_{country}.json",
        "progress": root / f"progress_{country}.json",
    }


# ==================================================================
# 响应拦截器
# ==================================================================
class ResponseCapture:
    """单次页面访问期间拦截所有 LV JSON / 图片响应。"""

    IMAGE_EXTENSIONS = ('.jpg', '.jpeg', '.png', '.webp', '.gif')
    IMAGE_PATH_PATTERNS = ('/images/is/image/lv/', '/images/')

    def __init__(self, page: Page, country: str, raw_dir: Path):
        self.page = page
        self.country = country
        self.raw_dir = raw_dir
        self.json_responses: List[Dict[str, Any]] = []
        self.image_urls: List[str] = []
        self.dom_snapshot: Dict[str, Any] = {}  # 新增：DOM兜底数据快照
        self._handler = None

    async def __aenter__(self):
        async def _on_response(resp: Response):
            try:
                await self._process_response(resp)
            except Exception as e:  # pragma: no cover - 防御性
                logger.debug("响应处理异常 %s: %s", resp.url, e)

        self._handler = _on_response
        self.page.on("response", _on_response)
        return self

    async def __aexit__(self, exc_type, exc, tb):
        if self._handler is not None:
            self.page.remove_listener("response", self._handler)
        # === 退出时收集一次 DOM 兜底快照（防 API 被拦截）===
        try:
            # 采集前调试：记录页面 URL 和 .lv-price 数量
            try:
                _dbg = await self.page.evaluate("""() => {
                    return {
                        url: location.href,
                        title: document.title,
                        lvPriceCount: document.querySelectorAll('.lv-price').length,
                        bodyLen: document.body ? document.body.innerText.length : 0,
                        readyState: document.readyState,
                    };
                }""")
                logger.info("[DOM快照采集前] url=%s title=%s lvPrice=%d bodyLen=%d readyState=%s",
                            str(_dbg.get("url",""))[:80], str(_dbg.get("title",""))[:30],
                            int(_dbg.get("lvPriceCount",0)), int(_dbg.get("bodyLen",0)), str(_dbg.get("readyState","")))
            except Exception as _dbg_e:
                logger.warning("[DOM快照采集前] 调试查询失败: %s", _dbg_e)
            self.dom_snapshot = await self._collect_dom_snapshot(self.page)
        except Exception as e:
            logger.debug("DOM 快照采集失败: %s", e)

    @staticmethod
    async def _collect_dom_snapshot(page: Page) -> Dict[str, Any]:
        """从 DOM 中提取商品数据，作为 AKAMAI 拦截导致 API 响应为空时的 100% 兜底。

        采集内容：
        1. window 全局对象上常见的数据挂载点（__NEXT_DATA__、__INITIAL_STATE__、__APP_DATA__、
           window.lvProduct、window.productData 等）
        2. <script type="application/ld+json"> 结构化数据
        3. <meta property="product:* / og:* / twitter:*"> Open Graph / product meta
        4. <script id="__NEXT_DATA__">（Next.js 站点）
        5. 文本价格 + 标题（DOM innerText 的 h1 / .price 节点）
        """
        try:
            data = await page.evaluate('''() => {
                const out = {next_data: null, initial_state: null, app_data: null,
                             ld_json: [], meta: {}, window_keys: [],
                             product_scripts: [], price_text: null, title_text: null, sku_text: null,
                             body_text: null};

                // 1) window 数据挂载点
                for (const k of ['__NEXT_DATA__','__INITIAL_STATE__','__APP_DATA__',
                                 '__PRELOADED_STATE__','__REDUX_STATE__','__DATA__',
                                 'lvProduct','lvproduct','productData','productInfo',
                                 'product_detail','productDetail','pdpData','skuData']) {
                    try {
                        const val = window[k];
                        if (val !== null && val !== undefined) {
                            if (typeof val === 'object') {
                                const s = JSON.stringify(val);
                                if (s.length < 2_000_000) {
                                    out[k.startsWith('__') ? k.replace(/^__|__$/g,'').toLowerCase() : 'window_' + k.toLowerCase()] =
                                        JSON.parse(s);
                                    out.window_keys.push(k);
                                }
                            } else if (typeof val === 'string' && val.length < 2000) {
                                out['window_' + k.toLowerCase()] = val;
                                out.window_keys.push(k);
                            }
                        }
                    } catch(e){}
                }

                // 2) 脚本标签（Next.js + 任意内联 JSON）
                document.querySelectorAll('script').forEach(scr => {
                    try {
                        const type = (scr.getAttribute('type') || '').toLowerCase();
                        const id = (scr.id || '').toLowerCase();
                        const txt = scr.textContent || '';
                        if (!txt || txt.length > 5_000_000) return;
                        if (type === 'application/ld+json') {
                            try { out.ld_json.push(JSON.parse(txt)); }
                            catch(e){ try { out.ld_json.push(txt.substring(0,2000)); } catch(e){} }
                            return;
                        }
                        if (id === '__next_data__' || id.includes('next_data')) {
                            try { out.next_data = JSON.parse(txt); }
                            catch(e){ try { out.next_data_raw = txt.substring(0,10000); } catch(e){} }
                            return;
                        }
                        if (type === 'application/json' || txt.trim().startsWith('{') && txt.length < 500000) {
                            // 可能是商品数据的内联 JSON
                            try {
                                const parsed = JSON.parse(txt);
                                if (parsed && typeof parsed === 'object' &&
                                    (JSON.stringify(parsed).includes('sku') ||
                                     JSON.stringify(parsed).includes('price'))) {
                                    out.product_scripts.push(parsed);
                                }
                            } catch(e){}
                        }
                    } catch(e){}
                });

                // 3) meta tags
                document.querySelectorAll('meta[property], meta[name]').forEach(m => {
                    const k = m.getAttribute('property') || m.getAttribute('name');
                    const v = m.getAttribute('content');
                    if (k && v) {
                        const lk = k.toLowerCase();
                        if (lk.startsWith('product:') || lk.startsWith('og:') || lk.startsWith('twitter:')
                            || lk === 'sku' || lk.includes('sku') || lk.includes('price')
                            || lk.includes('currency') || lk.includes('description') || lk.includes('brand')) {
                            out.meta[k] = v;
                        }
                    }
                });

                // 4) h1 / price / sku 文本
                try {
                    const h1s = document.querySelectorAll('h1');
                    for (const h of h1s) {
                        const t = (h.innerText||'').trim();
                        if (t && t.length >= 2) { out.title_text = t.substring(0,300); break; }
                    }
                    const priceSel = '[class*="price" i], [data-testid*="price" i], [itemprop="price"], .lv-price';
                    const _priceEls = document.querySelectorAll(priceSel);
                    out._debug_priceElCount = _priceEls.length;
                    out._debug_priceTexts = [];
                    _priceEls.forEach(p => {
                        const t = (p.innerText||'').trim();
                        out._debug_priceTexts.push(t);
                        if (t && t.length <= 40 && (t.match(/[0-9]/g)||[]).length >= 3) {
                            if (!out.price_text) out.price_text = t;
                        }
                    });
                    const skuSel = '[class*="sku" i], [data-testid*="sku" i], [itemprop="sku"], .lv-sku, .sku, [class*="reference" i]';
                    document.querySelectorAll(skuSel).forEach(el => {
                        const t = (el.innerText||'').trim();
                        if (t && t.length <= 30 && /^[A-Z][A-Z0-9]{4,}$/.test(t.trim().replace(/\s+/g,''))) {
                            if (!out.sku_text) out.sku_text = t.trim().replace(/\s+/g,'');
                        }
                    });
                    const body = (document.body && document.body.innerText) ? document.body.innerText : '';
                    out.body_text = body.substring(0, 3000);
                } catch(e){}
                return out;
            }''')  # 注意：此 playwright 版本不支持 evaluate(timeout=...) 参数
            return data or {}
        except Exception as _e:
            logger.warning("DOM 快照采集异常: %s", _e)
            return {}

    async def _process_response(self, resp: Response):
        url = resp.url
        lower = url.lower()

        # === 1. 图片 URL 收集（纯内存） ===
        if any(p in lower for p in self.IMAGE_PATH_PATTERNS) and \
           any(lower.endswith(ext) or (ext + '?') in lower or (ext + '&') in lower
               for ext in self.IMAGE_EXTENSIONS):
            if url not in self.image_urls:
                self.image_urls.append(url)
            return

        # === 2. JSON / 文本响应（louisvuitton.com 域名） ===
        if not is_lv_response(url):
            return

        # 跳过明显的静态资源
        if any(lower.endswith(ext) for ext in ('.css', '.js', '.woff', '.woff2',
                                               '.ttf', '.svg', '.ico', '.map')):
            return

        status = resp.status
        ct = (resp.headers.get("content-type") or "").lower()
        is_json = "json" in ct

        # 尝试读取响应体（无论状态码，因为Akamai拦截会返回403/302+HTML）
        try:
            text = await resp.text()
        except Exception:
            return
        if not text:
            # 空响应也保存诊断（针对SKU API级别的请求）
            looks_important_api = any(k in lower for k in ('/skus/', '/sku/', '/availability', '/products/', '/catalog/'))
            if looks_important_api and (status < 200 or status >= 400):
                self._save_raw(url, ct, f"[EMPTY_BODY] status={status}")
                logger.warning("[RESP] 重要API空响应 status=%s url=%s", status, url[:100])
            return

        data: Any = None
        if is_json or text.lstrip().startswith(('{', '[')):
            try:
                data = json.loads(text)
            except Exception:
                data = None

        # ===== 反爬拦截检测（非200状态）=====
        blocked = False
        if status < 200 or status >= 400:
            blocked = True
            lower_text = text.lower()
            akamai_hits = [k for k in ('akamai','bot defender','challenge','verif','captcha','blocked',
                                       'access denied','forbidden','403','too many request','rate limit')
                           if k in lower_text]
            # 保存所有非200响应（用于离线诊断），关键API不管有没有命中关键词都保存
            looks_important_api = any(k in lower for k in ('/skus/', '/sku/', '/availability', '/products/', '/catalog/', '/api/'))
            if looks_important_api or akamai_hits:
                self._save_raw(url, ct, text[:crawler_config.RAW_CAPTURE_MAX_BYTES])
                if akamai_hits:
                    logger.warning("[ANTI-BOT] ⚠️  疑似Akamai拦截 status=%s hits=%s url=%s",
                                   status, akamai_hits, url[:120])
                else:
                    logger.info("[RESP] 非200 API响应 status=%s len=%d url=%s", status, len(text), url[:100])
            # 若内容其实是JSON（例如错误响应 {"error":"rate limited"}），也塞到json_responses里打标记
            if data is not None:
                wrapped = {"url": url, "status": status, "data": data, "_blocked": True, "_akamai": bool(akamai_hits)}
                self.json_responses.append(wrapped)
                return

            # 非JSON且非200 → 直接跳过解析
            return

        # 正常 2xx JSON
        if data is None:
            # 非 JSON（如 text/html 200 商品页本身），仅在 SAVE_ALL 时保存
            if crawler_config.SAVE_ALL_LV_RESPONSES and len(text) < 500_000:
                self._save_raw(url, ct, text[:crawler_config.RAW_CAPTURE_MAX_BYTES])
            return

        self.json_responses.append({"url": url, "status": status, "data": data})
        if crawler_config.SAVE_ALL_LV_RESPONSES or looks_like_product_data(data):
            self._save_raw(url, "application/json", json.dumps(data, ensure_ascii=False))

    def _save_raw(self, url: str, content_type: str, payload: str):
        """保存一条原始响应（用于后续离线调整解析器）。"""
        try:
            safe = "".join(c if c.isalnum() else "_" for c in url.split("?")[0])[-80:]
            ts = int(time.time() * 1000)
            name = f"{self.country}_{ts}_{safe}.json" if "json" in content_type.lower() or payload.lstrip().startswith(('{', '[')) else f"{self.country}_{ts}_{safe}.txt"
            out = self.raw_dir / name
            # 文件体积限制
            if len(payload) > crawler_config.RAW_CAPTURE_MAX_BYTES:
                payload = payload[:crawler_config.RAW_CAPTURE_MAX_BYTES] + "\n...TRUNCATED"
            with open(out, "w", encoding="utf-8") as f:
                json.dump({"url": url, "content_type": content_type,
                           "saved_at": datetime.now().isoformat(timespec="seconds"),
                           "body": payload}, f, ensure_ascii=False)
        except Exception:
            pass


# ==================================================================
# 浏览器 / Page 辅助
# ==================================================================
_STEALTH_JS = """
() => {
    Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
    Object.defineProperty(navigator, 'languages', {get: () => ['ja', 'en', 'fr']});
    Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
    window.chrome = {runtime: {}, loadTimes: function(){}, csi: function(){}};
    Object.defineProperty(navigator, 'plugins', {get: () => [1,2,3,4,5]});
    const origQuery = window.navigator.permissions.query;
    window.navigator.permissions.query = (parameters) => (
        parameters.name === 'notifications' ?
            Promise.resolve({ state: Notification.permission }) :
            origQuery(parameters)
    );
}
"""

async def _stealth_page(page: Page):
    """注入反检测脚本到页面，降低被Akamai识别为自动化浏览器的概率。"""
    try:
        await page.add_init_script(_STEALTH_JS)
    except Exception:
        pass

async def _safe_navigate(page: Page, url: str, wait_ms: int = 6000) -> bool:
    try:
        await page.goto(url, timeout=60_000, wait_until="domcontentloaded")
        # ===== 显式等待价格文本出现（最长 15 秒）=====
        # CN 站 Vue 渲染慢，需要约 12 秒才出现 .lv-price 文本；JP/KR 站 6-8 秒即可
        # 用 wait_for_function 等到 .lv-price 元素存在且 innerText 含数字（避免匹配到空占位符）
        # 等到就立即继续（节省时间），超时也继续（不阻塞流程）
        try:
            await page.wait_for_function(
                """() => {
                    const els = document.querySelectorAll('.lv-price .notranslate, .lv-price, [itemprop="price"]');
                    for (const el of els) {
                        const t = (el.innerText || el.textContent || '').trim();
                        if (t && /[0-9]/.test(t)) return true;
                    }
                    return false;
                }""",
                timeout=15_000,
            )
            logger.debug("价格元素文本已出现，继续后续流程")
        except Exception as e:
            logger.warning("价格元素等待超时(15s)，回退到固定等待 %dms: %s", wait_ms, e)
            await asyncio.sleep(wait_ms / 1000.0)
        # ===== 关闭营销弹窗 / 订阅弹窗（防爬攻防：韩国LV大量弹窗会破坏页面）=====
        try:
            await page.evaluate('''() => {
                const sels = [
                    // 韩文
                    'button[aria-label*="닫기"]','button[aria-label="취소"]',
                    // 英文
                    'button[aria-label*="close" i]','button[aria-label*="dismiss" i]',
                    // 通用 class 名
                    '.lv-popup-close','.lv-modal-close','.lv-dialog__close',
                    '.popup-close','.modal-close','.close-popup',
                    '[class*="popup"] button','[class*="modal"] button',
                    '[class*="newsletter"] button','[class*="subscription"] button',
                    '[class*="marketing"] button','[class*="promotion"] button',
                    '[id*="popup"] button','[id*="modal"] button',
                    // 显式可见关闭按钮（文案）
                    'button:has-text("닫기")','button:has-text("Close")',
                    'a:has-text("닫기")','a:has-text("Close")',
                ];
                let n = 0;
                for (const s of sels) {
                    try {
                        document.querySelectorAll(s).forEach(b => {
                            const r = b.getBoundingClientRect();
                            if (r.width > 0 && r.height > 0) {
                                try { b.click(); n++; } catch(e){}
                            }
                        });
                    } catch(e){}
                }
                // 清除遮罩层（常见：position fixed + z-index 9999）
                try {
                    document.querySelectorAll('[class*="overlay"],[class*="backdrop"],[class*="mask"],[id*="overlay"],[id*="backdrop"]').forEach(el => {
                        const r = el.getBoundingClientRect();
                        if (r.width > 0 && r.height > 0) el.remove();
                    });
                } catch(e){}
                return n;
            }''')
        except Exception:
            pass
        await _scroll_page(page)
        await asyncio.sleep(1.5)
        # 二次关闭弹窗（有些弹窗懒加载）
        try:
            await page.evaluate('''() => {
                const sels = [
                    'button[aria-label*="닫기"]','button[aria-label*="close" i]',
                    '.lv-popup-close','.lv-modal-close',
                    '[class*="popup"] button','[class*="newsletter"] button',
                    'button:has-text("닫기")','button:has-text("Close")',
                ];
                let n = 0;
                for (const s of sels) {
                    try {
                        document.querySelectorAll(s).forEach(b => {
                            const r = b.getBoundingClientRect();
                            if (r.width>0 && r.height>0) { try{b.click();n++}catch(e){} }
                        });
                    } catch(e){}
                }
                return n;
            }''')
        except Exception:
            pass
        return True
    except Exception as e:
        logger.warning("页面加载失败 %s: %s", url, e)
        return False


async def _scroll_page(page: Page):
    """模拟用户滚动，触发懒加载。"""
    try:
        viewport = page.viewport_size or {"height": 1000}
        height = viewport["height"]
        current = 0
        while True:
            current += height // 2
            await page.evaluate(f"window.scrollTo(0, {current})")
            await asyncio.sleep(0.4)
            scrolled = await page.evaluate("window.scrollY")
            max_y = await page.evaluate("document.body.scrollHeight - window.innerHeight")
            if scrolled + 50 >= max_y:
                break
    except Exception:
        pass


# ==================================================================
# 统一浏览器管理器（单例）
# ==================================================================
# 设计原则（解决历史Chrome调用问题的根因）：
#   1. 单一 CDP 连接：整个进程只调用一次 connect_over_cdp，复用同一 browser 实例
#   2. 统一 profile 目录：仅使用 /tmp/chrome-cdp-profile（与 chrome_manager.sh 一致）
#   3. 页面池上限：MAX_PAGES=2，新建前自动关闭多余页面，杜绝标签页累积
#   4. 统一 stealth 注入：所有新建 page 自动注入反检测脚本
#   5. 强制重建协议：recreate_page() 保证"先关闭旧page → 验证 → 创建新page"
#   6. 不再在业务函数内自行 connect_over_cdp / launch_persistent_context


class BrowserManager:
    """全局浏览器单例管理器。

    使用方式：
        bm = await BrowserManager.get_instance(pw)
        page = await bm.new_scoped_page()      # 申请一个新 page（自动注入 stealth）
        # ... 使用 page ...
        await bm.release_page(page)            # 释放（关闭）

        # 或重建 page（先关旧再开新）：
        page = await bm.recreate_page(page)
    """
    _instance: "BrowserManager" = None
    _pw_ref = None  # 持有 playwright 实例引用防止 GC

    MAX_PAGES = 2  # 标签页硬上限：1 主用 + 1 备用

    def __init__(self, browser: Browser, ctx: BrowserContext, owned_persistent_ctx: bool = False):
        self.browser = browser
        self.ctx = ctx
        # owned_persistent_ctx=True 表示 ctx 是 launch_persistent_context 创建的，
        # 需要在 cleanup 时关闭；CDP 模式下 False（不能关闭用户的 Chrome）
        self._owned_persistent_ctx = owned_persistent_ctx
        self._active_pages: List[Page] = []

    @classmethod
    async def get_instance(cls, pw) -> "BrowserManager":
        """获取/创建全局 BrowserManager 单例。"""
        if cls._instance is not None and cls._instance.browser is not None:
            # 健康检查：确认 browser 仍然可用
            try:
                _ = cls._instance.browser.contexts
                return cls._instance
            except Exception:
                logger.warning("[BM] 旧实例已失效，重新创建")
                cls._instance = None
                cls._pw_ref = None

        cls._pw_ref = pw  # 防止 pw 被 GC 回收
        try:
            browser = await pw.chromium.connect_over_cdp(crawler_config.CDP_ENDPOINT)
            if not browser.contexts:
                ctx = await browser.new_context()
            else:
                ctx = browser.contexts[0]
            logger.info("[BM] CDP 连接成功 (endpoint=%s)", crawler_config.CDP_ENDPOINT)
            cls._instance = cls(browser, ctx, owned_persistent_ctx=False)
        except Exception as e:
            logger.warning("[BM] CDP 连接失败: %s，回退到 launch_persistent_context", e)
            ctx = await pw.chromium.launch_persistent_context(
                user_data_dir='/tmp/chrome-cdp-profile',
                executable_path='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
                args=['--no-first-run', '--no-default-browser-check',
                      '--disable-blink-features=AutomationControlled',
                      '--disable-features=AutomationControlled'],
                ignore_default_args=['--enable-automation',
                                     '--disable-background-networking',
                                     '--disable-component-update',
                                     '--disable-client-side-phishing-detection'],
                headless=False,
                viewport={'width': 1920, 'height': 1080},
            )
            browser = ctx.browser if hasattr(ctx, 'browser') else None
            logger.info("[BM] persistent context 启动成功 (profile=/tmp/chrome-cdp-profile)")
            cls._instance = cls(browser, ctx, owned_persistent_ctx=True)

        # 启动时清理历史残留标签页（最多保留 1 个，避免与用户手动打开的页面冲突）
        await cls._instance._cleanup_extra_tabs(keep=1)
        return cls._instance

    @classmethod
    def reset(cls):
        """重置单例（仅用于测试或进程结束）。"""
        cls._instance = None
        cls._pw_ref = None

    async def _cleanup_extra_tabs(self, keep: int = 1) -> int:
        """关闭多余标签页，仅保留最近 keep 个。"""
        closed = 0
        try:
            pages = list(self.ctx.pages)
            if len(pages) <= keep:
                return 0
            # 关闭最旧的页面，保留最后 keep 个
            for p in pages[:-keep]:
                try:
                    await p.close()
                    closed += 1
                except Exception:
                    pass
            if closed > 0:
                logger.info("[BM] 清理 %d 个多余标签页（保留 %d）", closed, keep)
        except Exception as e:
            logger.debug("[BM] 清理标签页异常: %s", e)
        # 同步 _active_pages 列表
        self._active_pages = [p for p in self._active_pages if p in self.ctx.pages]
        return closed

    async def new_scoped_page(self) -> Page:
        """申请一个新 page，自动注入 stealth，并强制清理超出上限的标签页。"""
        # 先清理，确保不超过 MAX_PAGES
        await self._cleanup_extra_tabs(keep=self.MAX_PAGES - 1)
        page = await self.ctx.new_page()
        await _stealth_page(page)
        self._active_pages.append(page)
        logger.debug("[BM] 新建 page，当前活跃: %d", len(self._active_pages))
        return page

    async def release_page(self, page: Page):
        """释放（关闭）一个 page。"""
        try:
            if page in self._active_pages:
                self._active_pages.remove(page)
            await page.close()
        except Exception:
            pass

    async def recreate_page(self, old_page: Optional[Page]) -> Page:
        """重建 page：先关闭旧的，验证关闭成功，再创建新的。"""
        if old_page is not None:
            await self.release_page(old_page)
            # 等待关闭生效
            await asyncio.sleep(0.5)
        return await self.new_scoped_page()

    async def health_check(self) -> bool:
        """检查 browser 是否仍然可用。"""
        try:
            _ = self.ctx.pages
            return True
        except Exception:
            return False

    async def cleanup(self):
        """清理资源（CDP 模式不关闭 browser，仅清理 page；persistent 模式关闭 ctx）。"""
        for p in list(self._active_pages):
            try:
                await p.close()
            except Exception:
                pass
        self._active_pages.clear()
        if self._owned_persistent_ctx:
            try:
                await self.ctx.close()
            except Exception:
                pass
        BrowserManager.reset()


# ==================================================================
# 兼容旧接口：保留 _connect_browser / _get_page_via_cdp / _close_extra_tabs
# 但内部统一走 BrowserManager，杜绝重复连接
# ==================================================================
async def _connect_browser(pw) -> Browser:
    """[兼容接口] 通过 BrowserManager 获取 browser。"""
    bm = await BrowserManager.get_instance(pw)
    return bm.browser


async def _get_page_via_cdp(pw) -> Page:
    """[兼容接口] 通过 BrowserManager 申请新 page。"""
    bm = await BrowserManager.get_instance(pw)
    return await bm.new_scoped_page()


async def _close_extra_tabs(browser: Browser = None) -> int:
    """[兼容接口] 通过 BrowserManager 清理多余标签页。"""
    if BrowserManager._instance is None:
        return 0
    return await BrowserManager._instance._cleanup_extra_tabs(keep=1)


# ==================================================================
# 保存 JSONL 行
# ==================================================================
def _append_jsonl(path: Path, obj: Any):
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=False) + "\n")


def _load_existing_ids(path: Path, key: str) -> set:
    if not path.exists():
        return set()
    ids = set()
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
                k = obj.get(key)
                if k:
                    ids.add(k)
            except Exception:
                pass
    return ids


# ==================================================================
# 列表模式：抓取所有包包分类页 → 提取 slug 列表
# ==================================================================
async def crawl_list(country: str, adapter):
    dirs = _ensure_dirs(country)
    # slugs 去重
    seen_slugs: set = set()
    if dirs["slugs"].exists():
        with open(dirs["slugs"], "r", encoding="utf-8") as f:
            try:
                seen_slugs = set(json.load(f))
            except Exception:
                seen_slugs = set()

    category_urls = getattr(adapter, "category_urls", None) or [adapter.get_category_url()]

    async with async_playwright() as pw:
        page = await _get_page_via_cdp(pw)
        try:
            for cat_url in category_urls:
                logger.info("[LIST] 访问分类页: %s", cat_url)
                async with ResponseCapture(page, country, dirs["raw"]) as cap:
                    ok = await _safe_navigate(page, cat_url, wait_ms=crawler_config.LIST_PAGE_WAIT_MS)
                    if not ok:
                        continue
                    # 尝试点击加载更多（按分类页 3 次）
                    for _ in range(5):
                        try:
                            # 通过适配器提供的选择器（或兜底通用关键词）
                            load_more_sel = adapter.selectors.get("load_more_button")
                            if load_more_sel:
                                btn = await page.query_selector(load_more_sel)
                                if not btn:
                                    break
                                await btn.click(timeout=5000)
                                await asyncio.sleep(2.5)
                                await _scroll_page(page)
                                await asyncio.sleep(1.5)
                            else:
                                break
                        except Exception:
                            break
                # 从 JSON 响应中抽取 slug
                new_slugs = _extract_slugs_from_responses(cap.json_responses, adapter)
                logger.info("[LIST] 捕获到 %d 条 JSON 响应，提取 %d 个新 slug",
                            len(cap.json_responses), len(new_slugs) - len(seen_slugs))
                seen_slugs.update(new_slugs)
                # 每抓完一个分类立即落盘
                with open(dirs["slugs"], "w", encoding="utf-8") as f:
                    json.dump(sorted(seen_slugs), f, ensure_ascii=False, indent=2)
                # 随机冷却
                await asyncio.sleep(random.uniform(*adapter.request_interval_range))
        finally:
            try:
                await page.close()
            except Exception:
                pass
    logger.info("[LIST] %s 完成，共 %d 个商品 slug，已保存到 %s",
                country, len(seen_slugs), dirs["slugs"])
    return sorted(seen_slugs)


def _extract_slugs_from_responses(json_responses: List[Dict], adapter) -> List[str]:
    """从列表页 JSON 响应中抽取所有商品 slug / articleNo。"""
    slugs: List[str] = []

    def _walk(node):
        if isinstance(node, dict):
            for k, v in node.items():
                # 关键词：slug, identifier, id, articleNumber, productId
                if isinstance(k, str) and k.lower() in ("slug", "identifier", "id") and isinstance(v, str):
                    if v and (v.startswith(('M', 'N', 'S', 'G')) or '-' in v or len(v) in (6, 7, 8)):
                        slugs.append(v)
                if k == "articleNumber" and isinstance(v, str):
                    slugs.append(v)
                # 产品对象数组
                if k == "products" and isinstance(v, list):
                    for p in v:
                        if isinstance(p, dict):
                            if "identifier" in p and isinstance(p["identifier"], str):
                                slugs.append(p["identifier"])
                            if "slug" in p and isinstance(p["slug"], str):
                                slugs.append(p["slug"])
                            if "articleNumber" in p and isinstance(p["articleNumber"], str):
                                slugs.append(p["articleNumber"])
                # LV 列表页可能是 hits
                if k == "hits" and isinstance(v, list):
                    for h in v:
                        if isinstance(h, dict):
                            # algolia / commerce cloud 常见字段
                            for f2 in ("slug", "identifier", "id", "sku", "skuId",
                                       "articleNumber", "productId"):
                                if f2 in h and isinstance(h[f2], str):
                                    slugs.append(h[f2])
                _walk(v)
        elif isinstance(node, list):
            for item in node:
                _walk(item)

    for jr in json_responses:
        _walk(jr.get("data") or jr)

    # 清理：过滤非包包、去重
    country_path_token = {
        "JP": "/jpn-jp/products/",
        "KR": "/kor-kr/products/",
        "CN": "/chn-cn/products/",
    }.get(adapter.country, "/products/")

    cleaned: List[str] = []
    seen = set()
    for s in slugs:
        if not s:
            continue
        s = s.strip()
        # 从 URL 中抽 slug
        if "/products/" in s:
            s = s.split("/products/", 1)[1].split("?")[0].split("/")[0]
        if not s or len(s) < 4:
            continue
        lower = s.lower()
        # 过滤明显非包包的关键词
        if any(kw in lower for kw in adapter.non_product_keywords):
            continue
        if s in seen:
            continue
        seen.add(s)
        cleaned.append(s)
    return cleaned


# ==================================================================
# 门店库存采集（DOM 交互式，支持 JP / KR 多语言）
# ==================================================================

# 各国门店库存采集配置（UI 文案、城市、行政区划关键词等）
_STORE_INVENTORY_CONFIG: Dict[str, Dict[str, Any]] = {
    "JP": {
        "panel_text": "ストアの在庫状況を確認する",
        "input_placeholder_keywords": ["都道府県"],
        "stock_in_keywords": ["在庫あり"],
        "stock_out_keywords": ["在庫なし"],
        "stock_low_keywords": ["在庫僅少"],
        # 用「日本」作为国家标识，避免「道」误匹配中国街道名（如"世纪大道"）
        "address_keywords": ['日本'],
        "cities": ["東京", "大阪", "京都", "横浜", "名古屋", "神戸", "福岡"],
        "store_id_regex": r"japan/([^/?#]+)",
        # prefecture 后紧跟邮编（如"東京都 150-0001"），避免"表参道"等街道名误匹配
        "city_regex": r"([\u4e00-\u9fa5]+[都道府県])\s*\d{3}",
    },
    "KR": {
        # KR 实际面板文案（2026-08-04 通过浏览器实际确认）
        "panel_text": "매장에서 찾기",
        "input_placeholder_keywords": ["시/도", "시도", "주소"],
        "stock_in_keywords": ["재고 있음", "구매 가능", "available", "in stock"],
        "stock_out_keywords": ["재고 없음", "품절", "sold out", "unavailable"],
        "stock_low_keywords": ["재고 적음", "한정", "少量", "low stock"],
        # 用「대한민국」作为国家标识，避免误匹配日本/中国门店
        "address_keywords": ['대한민국'],
        "cities": ["서울", "부산", "대구", "인천", "광주"],
        "store_id_regex": r"korea/([^/?#]+)|south-korea/([^/?#]+)",
        "city_regex": r"([\uac00-\ud7a3]+[시도])",
    },
}


async def collect_store_inventories_multi(
    page: Page,
    country: str,
    sku_id: str,
    cities: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    """通过 DOM 交互采集门店库存（支持 JP / KR 多语言）。

    流程：
    1. 滚动到「门店库存确认」折叠面板并展开
    2. 点击「门店库存」按钮打开搜索弹窗
    3. 逐个城市输入搜索 → 从 DOM 提取门店名称、地址、库存状态
    4. 过滤出目标国家门店（地址含行政区划关键词）

    采用 DOM 交互而非直接 API，因为库存 API 需特殊签名，浏览器交互最稳定。
    """
    cfg = _STORE_INVENTORY_CONFIG.get(country)
    if not cfg:
        logger.warning("国家 %s 未配置门店库存采集参数", country)
        return []

    if cities is None:
        cities = cfg["cities"]

    all_stores: Dict[str, Dict[str, Any]] = {}

    async def _disable_backdrop() -> None:
        await page.evaluate(r"""
            () => {
                const backdrops = document.querySelectorAll('.lv-modal__backdrop, .lv-backdrop');
                for (const b of backdrops) {
                    b.style.pointerEvents = 'none';
                    b.style.opacity = '0.3';
                }
            }
        """)

    def _is_target_store(address: str) -> bool:
        return any(k in address for k in cfg["address_keywords"])

    try:
        # 第零步：关闭可能残留的弹窗（批量采集时上一个SKU的弹窗可能未关闭）
        try:
            await page.evaluate(r"""
                () => {
                    // 点击关闭按钮
                    const closeBtns = document.querySelectorAll(
                        '.lv-modal__close, .lv-close, button[aria-label*="close" i], '
                        'button[aria-label*="閉じる"], button[aria-label*="닫기"]'
                    );
                    for (const btn of closeBtns) {
                        try { btn.click(); } catch(e) {}
                    }
                    // 隐藏所有弹窗
                    const modals = document.querySelectorAll(
                        '.lv-modal__container, .lv-locate-in-store__first-step-modal, '
                        '.lv-locate-in-store__second-step-modal'
                    );
                    for (const m of modals) {
                        m.style.display = 'none';
                    }
                    // 移除body滚动锁定
                    if (document.body.style.overflow === 'hidden') {
                        document.body.style.overflow = '';
                    }
                }
            """)
            await page.wait_for_timeout(800)
        except Exception as _e:
            logger.debug("[%s] 关闭残留弹窗异常: %s", country, _e)

        # 第一步：找到并展开库存折叠面板
        panel_text = cfg["panel_text"]
        expanded = await page.evaluate(r"""
            (panelText) => {
                const panels = document.querySelectorAll('.lv-expandable-panel');
                let targetPanel = null;
                for (const panel of panels) {
                    if (panel.innerText.includes(panelText)) {
                        targetPanel = panel;
                        break;
                    }
                }
                if (!targetPanel) return { ok: false, reason: 'panel not found' };
                targetPanel.scrollIntoView({ behavior: 'smooth', block: 'center' });
                const btn = targetPanel.querySelector('button[aria-expanded]');
                if (!btn) return { ok: false, reason: 'button not found' };
                const isExpanded = btn.getAttribute('aria-expanded') === 'true';
                if (!isExpanded) btn.click();
                return { ok: true, was_expanded: isExpanded };
            }
        """, panel_text)
        if not expanded.get("ok"):
            logger.warning("[%s] 未找到库存折叠面板: %s", country, expanded.get("reason"))
            return []
        await page.wait_for_timeout(1500)
        logger.info("[%s] 库存折叠面板已展开", country)

        # 第二步：点击库存按钮打开弹窗
        store_btn_visible = await page.evaluate(r"""
            () => {
                const btn = document.querySelector('.lv-product-locate-in-store__container');
                if (!btn) return false;
                btn.scrollIntoView({ behavior: 'smooth', block: 'center' });
                return true;
            }
        """)
        if not store_btn_visible:
            logger.warning("[%s] 未找到库存按钮 .lv-product-locate-in-store__container", country)
            return []
        await page.wait_for_timeout(1500)
        await page.evaluate(r"""
            () => {
                const btn = document.querySelector('.lv-product-locate-in-store__container');
                if (btn) btn.click();
            }
        """)
        await page.wait_for_timeout(3000)
        await _disable_backdrop()
        logger.info("[%s] 门店库存弹窗已打开", country)

        # 调试：输出弹窗DOM结构（确认选择器是否匹配）
        modal_debug = await page.evaluate(r"""
            () => {
                const first = document.querySelector('.lv-locate-in-store__first-step-modal');
                const second = document.querySelector('.lv-locate-in-store__second-step-modal');
                const modal = document.querySelector('.lv-modal__container, .lv-modal__content');
                const inputs = document.querySelectorAll('.lv-modal__content input, .lv-locate-in-store input, input[type="text"]');
                const inputInfo = [];
                for (const inp of inputs) {
                    inputInfo.push({
                        placeholder: inp.getAttribute('placeholder') || '',
                        type: inp.getAttribute('type') || 'text',
                        className: inp.className || '',
                        id: inp.id || '',
                        visible: inp.offsetParent !== null,
                    });
                }
                return {
                    hasFirstStep: !!first,
                    hasSecondStep: !!second,
                    hasModal: !!modal,
                    modalClass: modal ? modal.className : '',
                    inputCount: inputs.length,
                    inputs: inputInfo,
                    modalHTML: modal ? modal.innerHTML.substring(0, 500) : '',
                };
            }
        """)
        logger.info("[%s] 弹窗DOM调试: firstStep=%s secondStep=%s modal=%s inputs=%d",
                    country, modal_debug.get("hasFirstStep"), modal_debug.get("hasSecondStep"),
                    modal_debug.get("hasModal"), modal_debug.get("inputCount"))
        if modal_debug.get("inputs"):
            for i, inp in enumerate(modal_debug["inputs"][:3]):
                logger.info("[%s]   input[%d]: placeholder=%s class=%s visible=%s",
                            country, i, inp.get("placeholder"), inp.get("className"), inp.get("visible"))

        # 逐个城市搜索
        for city in cities:
            try:
                # 回到第一步（搜索页）
                await page.evaluate(r"""
                    () => {
                        const first = document.querySelector('.lv-locate-in-store__first-step-modal');
                        const second = document.querySelector('.lv-locate-in-store__second-step-modal');
                        if (first && second) {
                            first.style.display = 'block';
                            second.style.display = 'none';
                        }
                    }
                """)
                await page.wait_for_timeout(500)
                await _disable_backdrop()

                # 清空并输入搜索词（使用实际class名）
                search_input = page.locator(
                    '.lv-address-search-form__input, '
                    '.lv-locate-in-store__first-step-modal input[type="text"], '
                    '.lv-locate-in-store__first-step-modal input:not([type]), '
                    '.lv-modal__content input[type="text"], '
                    '.lv-modal__content input:not([type])'
                )
                if await search_input.count() == 0:
                    logger.info("[%s] 「%s」未找到搜索输入框，跳过", country, city)
                    continue

                try:
                    await search_input.first.click(timeout=3000)
                except Exception:
                    await search_input.first.click(force=True, timeout=3000)
                await search_input.first.fill('')
                await page.wait_for_timeout(200)
                await search_input.first.type(city, delay=100)
                await page.wait_for_timeout(2500)

                # 从补全下拉列表中选择第一个匹配项（LV官网需要选择具体地址）
                suggestion_selected = await page.evaluate(r"""
                    () => {
                        // 查找补全列表项（多种可能的选择器）
                        const suggestions = document.querySelectorAll(
                            '.lv-address-search-form__suggestions li, .lv-address-search-form__suggestion-item, .lv-suggestions li, [class*="suggestion"] li, [class*="autocomplete"] li, .lv-list-item'
                        );
                        // 同时检查所有可见的列表项
                        const allListItems = document.querySelectorAll('li[role="option"], [role="listbox"] li, ul[class*="list"] li');
                        const combined = suggestions.length > 0 ? suggestions : allListItems;
                        if (combined.length > 0) {
                            combined[0].click();
                            return { ok: true, count: combined.length, text: combined[0].innerText.substring(0, 80) };
                        }
                        return { ok: false, count: 0, suggestionSelectors: suggestions.length, listItemSelectors: allListItems.length };
                    }
                """)
                if suggestion_selected.get("ok"):
                    logger.info("[%s] 「%s」选中补全项: %s",
                                country, city, suggestion_selected.get("text", ""))
                    await page.wait_for_timeout(1500)
                else:
                    logger.info("[%s] 「%s」无补全列表(suggestion=%s listItem=%s)，输出弹窗HTML前800字符:",
                                country, city,
                                suggestion_selected.get("suggestionSelectors"),
                                suggestion_selected.get("listItemSelectors"))
                    # 输出弹窗HTML用于调试
                    modal_html = await page.evaluate(r"""
                        () => {
                            const modal = document.querySelector('.lv-modal__container, .lv-modal__content, .lv-locate-in-store__first-step-modal');
                            return modal ? modal.innerHTML.substring(0, 800) : 'MODAL NOT FOUND';
                        }
                    """)
                    logger.info("[%s] 弹窗HTML: %s", country, modal_html[:800])

                # 点击搜索按钮
                see_btn = page.locator('.lv-modal__footer button')
                if await see_btn.count() == 0:
                    # 尝试更宽泛的按钮选择器
                    see_btn = page.locator('.lv-locate-in-store__first-step-modal button[type="submit"], '
                                           'button:has-text("在庫"), button:has-text("確認"), '
                                           'button:has-text("확인"), button:has-text("재고")')
                if await see_btn.count() == 0:
                    logger.info("[%s] 「%s」未找到搜索按钮", country, city)
                    continue
                btn_disabled = await see_btn.first.get_attribute('disabled')
                if btn_disabled is not None:
                    logger.info("[%s] 「%s」搜索后按钮仍禁用，跳过", country, city)
                    continue

                try:
                    await see_btn.first.click(timeout=8000)
                except Exception as click_err:
                    logger.debug("[%s] 正常点击失败，force click: %s", country, click_err)
                    await see_btn.first.click(force=True, timeout=5000)

                # 自适应等待：等待门店卡片出现（最长15秒，渐进式）
                stores = []
                for attempt in range(3):
                    try:
                        timeout_s = 5 + attempt * 5
                        await page.wait_for_function(
                            f"""() => {{
                                const second = document.querySelector('.lv-locate-in-store__second-step-modal');
                                if (!second) return false;
                                const cards = second.querySelectorAll('.lv-store-card-detailed');
                                if (cards.length > 0) return true;
                                const noResult = second.querySelector('[class*="no-result"], [class*="empty"], [class*="not-found"]');
                                if (noResult) return true;
                                return false;
                            }}""",
                            timeout=timeout_s * 1000,
                        )
                        break
                    except Exception:
                        if attempt < 2:
                            logger.debug("[%s] 「%s」搜索结果等待超时(第%d次, %ds)，重试...",
                                        country, city, attempt + 1, timeout_s)
                            await page.wait_for_timeout(2000)
                        else:
                            logger.info("[%s] 「%s」搜索结果等待超时(%ds)，继续尝试", country, city, timeout_s)

                # 从 DOM 提取门店列表
                stores = await page.evaluate(r"""
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

                # 只保留目标国家门店
                target_stores = [s for s in stores if _is_target_store(s.get('store_address', ''))]

                # 空结果重试：如果找到0家或门店异常少，等待后重试一次
                if len(stores) == 0 and len(cities) > 1:
                    logger.info("[%s] 「%s」首次搜索0家，等待3秒后重试...", country, city)
                    await page.wait_for_timeout(3000)
                    stores_retry = await page.evaluate(r"""
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
                    if len(stores_retry) > 0:
                        stores = stores_retry
                        target_stores = [s for s in stores if _is_target_store(s.get('store_address', ''))]
                        logger.info("[%s] 「%s」重试成功: %d 家门店", country, city, len(stores))

                for s in target_stores:
                    s["sku"] = sku_id
                    key = s.get("store_id", "") or s.get("store_name", "")
                    if key and key not in all_stores:
                        all_stores[key] = s

                logger.info("[%s] 搜索「%s」: 找到 %d 家门店（目标 %d 家）",
                            country, city, len(stores), len(target_stores))

            except Exception as e:
                logger.info("[%s] 搜索 %s 失败: %s", country, city, e)
                continue

    except Exception as e:
        logger.warning("[%s] 门店库存抓取异常: %s", country, e)

    result = list(all_stores.values())
    logger.info("[%s] 门店库存抓取完成: %d 家门店", country, len(result))
    return result


# ==================================================================
# 单商品详情
# ==================================================================
async def crawl_single(country: str, adapter, url_or_slug: str, dirs=None,
                        fetch_store_inventory: bool = False) -> Optional[Dict]:
    if dirs is None:
        dirs = _ensure_dirs(country)

    if country == "JP":
        product_url = url_or_slug if url_or_slug.startswith("http") else adapter.get_product_url(url_or_slug)
    elif country == "KR":
        product_url = url_or_slug if url_or_slug.startswith("http") else f"https://kr.louisvuitton.com/kor-kr/products/{url_or_slug}"
    elif country == "CN":
        product_url = url_or_slug if url_or_slug.startswith("http") else f"https://cn.louisvuitton.com/chn-cn/products/{url_or_slug}"
    else:
        product_url = url_or_slug if url_or_slug.startswith("http") else adapter.get_product_url(url_or_slug)

    logger.info("[SINGLE] %s", product_url)
    async with async_playwright() as pw:
        page = await _get_page_via_cdp(pw)
        try:
            async with ResponseCapture(page, country, dirs["raw"]) as cap:
                ok = await _safe_navigate(page, product_url, wait_ms=crawler_config.DETAIL_PAGE_WAIT_MS)
                if not ok:
                    return None
            result = _extract_product(country, adapter, cap, product_url)
            if result:
                # 避免重复写
                existing = _load_existing_ids(dirs["products"], "sku_id")
                if result.get("sku_id") and result["sku_id"] not in existing:
                    _append_jsonl(dirs["products"], result)
            # 库存（被动拦截）
            inventories = _extract_inventories(country, adapter, cap, product_url, result)
            if inventories:
                for inv in inventories:
                    _append_jsonl(dirs["inventories"], inv)
            # 门店库存（主动 DOM 交互，较慢）
            if fetch_store_inventory and result and result.get("sku_id"):
                sku_id = result["sku_id"]
                store_invs = await collect_store_inventories_multi(page, country, sku_id)
                if store_invs:
                    logger.info("[SINGLE] %s 门店库存: %d 家", country, len(store_invs))
                    for inv in store_invs:
                        inv["sku_id"] = sku_id
                        inv["country"] = country
                        inv["currency"] = adapter.currency
                        inv["source_url"] = product_url
                        inv["crawled_at"] = datetime.now().isoformat(timespec="seconds")
                        _append_jsonl(dirs["inventories"], inv)
                else:
                    logger.info("[SINGLE] %s 门店库存: 0 家", country)
            return result
        finally:
            try:
                await page.close()
            except Exception:
                pass


def _extract_product(country: str, adapter, cap: ResponseCapture, product_url: str) -> Optional[Dict]:
    """聚合所有详情页 JSON 响应 → 产出一个商品对象。

    优先级：
    1. skus API 响应（最可靠，含 skuId/name/priceRaw/medias）
    2. 其他 API 响应（兜底）
    """
    merged: Dict[str, Any] = {
        "source_url": product_url,
        "country": country,
        "currency": adapter.currency,
        "crawled_at": datetime.now().isoformat(timespec="seconds"),
    }

    # 优先级 1：先找 skus API 响应
    sku_responses = []
    other_responses = []
    for jr in cap.json_responses:
        url_lower = jr.get("url", "").lower()
        if "skus" in url_lower and ("price" in url_lower or "product" in url_lower):
            sku_responses.append(jr)
        else:
            other_responses.append(jr)

    if sku_responses:
        # 从 skus API 响应提取
        primary_sku = None
        all_skus = []
        for sr in sku_responses:
            data = sr.get("data") or sr
            if isinstance(data, list):
                for item in data:
                    if isinstance(item, dict):
                        all_skus.append(item)
            elif isinstance(data, dict):
                all_skus.append(data)

        if all_skus:
            # 优先找 sellable 的 SKU，或者选 URL 中提到的 SKU
            url_sku = ""
            if "/products/" in product_url:
                url_sku = product_url.rstrip("/").split("/")[-1]

            # 匹配 URL 中的 SKU
            for s in all_skus:
                if s.get("skuId") == url_sku:
                    primary_sku = s
                    break
            # 如果没匹配到，选第一个 sellable 的
            if not primary_sku:
                for s in all_skus:
                    if s.get("sellable"):
                        primary_sku = s
                        break
            # 兜底
            if not primary_sku:
                primary_sku = all_skus[0]

            if primary_sku:
                sku_id = primary_sku.get("skuId", "")
                name = primary_sku.get("name", "")
                price_raw = primary_sku.get("priceRaw", 0)
                sellable = primary_sku.get("sellable", False)

                # 提取图片
                images = []
                medias = primary_sku.get("medias", [])
                if isinstance(medias, list):
                    for m in medias:
                        if isinstance(m, dict):
                            url = m.get("url") or m.get("imageUrl") or m.get("src", "")
                            if url and url.startswith("http"):
                                images.append(url)
                        elif isinstance(m, str) and m.startswith("http"):
                            images.append(m)

                # 多 SKU 信息
                sku_details = []
                for s in all_skus:
                    sid = s.get("skuId", "")
                    sn = s.get("name", "")
                    sp = s.get("priceRaw", 0)
                    ss = s.get("sellable", False)
                    if sid:
                        sku_details.append({
                            "sku_id": sid,
                            "name": sn,
                            "price": sp,
                            "sellable": ss,
                        })

                merged.update({
                    "sku_id": sku_id,
                    "name_local": name,
                    "price": price_raw if price_raw else 0,
                    "price_values": [s["price"] for s in sku_details if s["price"] > 0],
                    "images": images[:30],
                    "sku_ids": [s["sku_id"] for s in sku_details],
                    "skus": sku_details,
                    "sellable": sellable,
                })
                logger.info("从 SKU API 提取: sku=%s name=%s price=%s 多SKU数=%d",
                            sku_id, name, price_raw, len(sku_details))
                return merged

    # DOM 快照数据提前暂存，等 names_found 初始化后再合并
    dom = getattr(cap, 'dom_snapshot', None) or {}
    dom_extracted = False
    _dom_cache_names: Dict[str, str] = {}
    _dom_cache_prices: List[float] = []
    _dom_cache_images: List[str] = []
    _dom_cache_sku_ids: List[str] = []
    _dom_cache_article_nos: List[str] = []

    # 从 dom_snapshot 里的"商品脚本/ld_json/next_data"里找商品级 dict 列表做 walk
    dom_dicts_to_walk: List[Any] = []
    if isinstance(dom.get('ld_json'), list):
        for lj in dom['ld_json']:
            if isinstance(lj, (dict, list)):
                dom_dicts_to_walk.append(lj)
    nd = dom.get('next_data')
    if isinstance(nd, dict):
        dom_dicts_to_walk.append(nd)
    for k in ('initial_state','app_data','preloaded_state','redux_state','data',
              'window_lvproduct','window_productdata','window_productinfo',
              'window_product_detail','window_productdetail','window_pdpdata','window_skudata'):
        v = dom.get(k)
        if isinstance(v, (dict, list)):
            dom_dicts_to_walk.append(v)
    if isinstance(dom.get('product_scripts'), list):
        dom_dicts_to_walk.extend(dom['product_scripts'])

    if dom_dicts_to_walk:
        def _walk_dom(node):
            if isinstance(node, dict):
                if any(kw in str(node.get("name", "")).lower() for kw in ("conversion", "click", "view", "track", "pixel", "beacon")):
                    return
                for name_field in ("name", "title", "displayName", "label"):
                    if isinstance(node.get(name_field), str):
                        val = node[name_field].strip()
                        if 2 <= len(val) <= 200 and not any(kw in val.lower() for kw in ("conversion", "click", "track", "pixel", "beacon", "dcl", "cdim")):
                            lang = node.get("locale") or node.get("lang") or \
                                   ("local" if name_field == "displayName" else f"dom_{name_field}_{len(_dom_cache_names)}")
                            _dom_cache_names[lang] = val
                for pf in ("priceRaw", "price", "priceAmount", "amount", "listPrice", "salePrice"):
                    pv = node.get(pf)
                    if isinstance(pv, (int, float)) and pv > 1000:
                        _dom_cache_prices.append(float(pv))
                    elif isinstance(pv, dict):
                        for sub in ("value", "amount", "centAmount"):
                            if isinstance(pv.get(sub), (int, float)) and pv[sub] > 0:
                                val = float(pv[sub])
                                if sub == "centAmount":
                                    val /= 100.0
                                _dom_cache_prices.append(val)
                for sf in ("skuId", "sku", "id", "identifier", "articleNumber", "reference"):
                    sv = node.get(sf)
                    if isinstance(sv, str) and 4 <= len(sv) <= 20:
                        if sv.startswith(("M", "N", "S", "G", "P")):
                            if sf in ("articleNumber", "reference"):
                                if sv not in _dom_cache_article_nos:
                                    _dom_cache_article_nos.append(sv)
                            else:
                                if sv not in _dom_cache_sku_ids:
                                    _dom_cache_sku_ids.append(sv)
                for imf in ("image", "mainImage", "thumbnail", "picture"):
                    im = node.get(imf)
                    if isinstance(im, str) and im.startswith("http"):
                        _dom_cache_images.append(im)
                    elif isinstance(im, dict):
                        for k2 in ("url", "src", "href"):
                            if isinstance(im.get(k2), str) and im[k2].startswith("http"):
                                _dom_cache_images.append(im[k2])
                if isinstance(node.get("images"), list):
                    for im in node["images"]:
                        if isinstance(im, str) and im.startswith("http"):
                            _dom_cache_images.append(im)
                        elif isinstance(im, dict):
                            for k2 in ("url", "src", "href"):
                                if isinstance(im.get(k2), str) and im[k2].startswith("http"):
                                    _dom_cache_images.append(im[k2])
                if isinstance(node.get("medias"), list):
                    for m in node["medias"]:
                        if isinstance(m, dict):
                            for k2 in ("url", "src", "imageUrl"):
                                if isinstance(m.get(k2), str) and m[k2].startswith("http"):
                                    _dom_cache_images.append(m[k2])
                        elif isinstance(m, str) and m.startswith("http"):
                            _dom_cache_images.append(m)
                for v in node.values():
                    _walk_dom(v)
            elif isinstance(node, list):
                for item in node:
                    _walk_dom(item)
        for dw in dom_dicts_to_walk:
            _walk_dom(dw)

    # meta 标签兜底（sku/price/title）
    meta = dom.get('meta') or {}
    if not _dom_cache_prices:
        for mk, mv in meta.items():
            lk = mk.lower()
            if ('price' in lk and 'amount' in lk) or lk == 'product:price:amount' or lk == 'product:price':
                try:
                    pv = float(str(mv).replace(',','').replace('¥','').replace('₩','').strip())
                    if pv > 1000:
                        _dom_cache_prices.append(pv)
                except:
                    pass
            if (lk.endswith(':sku') or 'sku' in lk) and isinstance(mv, str):
                sv = mv.strip().replace(' ','')
                if 4 <= len(sv) <= 20 and sv[0] in 'MNGSP' and sv.isalnum():
                    if sv not in _dom_cache_sku_ids:
                        _dom_cache_sku_ids.append(sv)
    if not _dom_cache_sku_ids:
        st = dom.get('sku_text')
        if st and st[0] in 'MNGSP' and st.isalnum() and 5 <= len(st) <= 20:
            _dom_cache_sku_ids.append(st)
    if not _dom_cache_names:
        tt = dom.get('title_text')
        if tt:
            _dom_cache_names['dom_title'] = tt
    if not _dom_cache_prices:
        pt = dom.get('price_text') or ''
        digits = re.sub(r'[^0-9]', '', pt)
        if digits:
            try:
                pv = float(digits)
                if pv > 1000:
                    _dom_cache_prices.append(pv)
            except: pass
        if not _dom_cache_prices and dom.get('body_text'):
            body = dom['body_text']
            for m in re.findall(r'[₩$¥]\s*([0-9][0-9,\.]{3,20})', body):
                try:
                    pv = float(m.replace(',','').replace('.',''))
                    if pv > 10000:
                        _dom_cache_prices.append(pv)
                except: pass
            if not _dom_cache_prices:
                for m in re.findall(r'([0-9]{2,3}(?:,[0-9]{3})+)\s*(?:원|KRW|₩)', body):
                    try:
                        pv = float(m.replace(',',''))
                        if pv > 10000:
                            _dom_cache_prices.append(pv)
                    except: pass
    # 额外：从 URL 提取 SKU 作为最后兜底
    url_sku = ""
    if "/products/" in product_url:
        url_sku = product_url.rstrip("/").split("/")[-1]
        if url_sku and url_sku[0] in 'MNGSPR' and url_sku.isalnum() and 5 <= len(url_sku) <= 20:
            if url_sku not in _dom_cache_sku_ids:
                _dom_cache_sku_ids.append(url_sku)

    dom_has_data_before_init = bool(_dom_cache_names or _dom_cache_prices or _dom_cache_sku_ids or _dom_cache_article_nos)

    # 优先级 2：从其他响应兜底提取
    names_found: Dict[str, str] = {}
    prices: List[float] = []
    images: List[str] = []
    sku_ids: List[str] = []
    article_nos: List[str] = []

    # === 注入 DOM 兜底数据（先过滤 Akamai 错误页）===
    _dom_is_akamai_error = False
    _akamai_error_markers = ('access denied', 'forbidden', 'bot defender',
                             '403', 'too many request', 'rate limit',
                             '验证您的身份', '请完成验证', '访问过于频繁', '人机验证',
                             'ロボット', '本人確認', '인증', '차단')
    if _dom_cache_names:
        _first_dom_name = next(iter(_dom_cache_names.values()), '').lower()
        if any(m in _first_dom_name for m in _akamai_error_markers):
            _dom_is_akamai_error = True
            logger.warning("DOM 兜底检测到 Akamai 错误页特征，DOM 数据全部丢弃：name=%s",
                           _first_dom_name[:80])
    if _dom_is_akamai_error:
        # 清空DOM兜底数据，避免错误页数据落盘
        _dom_cache_names.clear()
        _dom_cache_prices.clear()
        _dom_cache_sku_ids.clear()
        _dom_cache_article_nos.clear()
        _dom_cache_images.clear()

    names_found.update(_dom_cache_names)
    prices.extend(_dom_cache_prices)
    images.extend(_dom_cache_images)
    sku_ids.extend(_dom_cache_sku_ids)
    article_nos.extend(_dom_cache_article_nos)
    if dom_has_data_before_init and not _dom_is_akamai_error:
        dom_extracted = True
        logger.info("DOM 兜底预载入: names=%d prices=%s skus=%s articleNos=%s",
                    len(_dom_cache_names), sorted(set(_dom_cache_prices))[:5],
                    _dom_cache_sku_ids[:5], _dom_cache_article_nos[:5])
        # 调试：DOM快照中的价格元素信息
        _debug_price_count = dom.get('_debug_priceElCount', 0)
        _debug_price_texts = dom.get('_debug_priceTexts', [])
        _debug_price_text = dom.get('price_text', '')
        logger.info("DOM 快照调试: priceElCount=%d priceTexts=%s price_text=%s",
                    _debug_price_count, _debug_price_texts[:5], _debug_price_text)

    def _walk(node, path=""):
        if isinstance(node, dict):
            # 过滤 tracking/analytics 数据
            if any(kw in str(node.get("name", "")).lower() for kw in ("conversion", "click", "view", "track", "pixel", "beacon")):
                return
            # 商品名
            for name_field in ("name", "title", "displayName", "label"):
                if isinstance(node.get(name_field), str):
                    val = node[name_field].strip()
                    if 2 <= len(val) <= 200 and not any(kw in val.lower() for kw in ("conversion", "click", "track", "pixel", "beacon", "dcl", "cdim")):
                        lang = node.get("locale") or node.get("lang") or \
                               ("local" if name_field == "displayName" else f"{name_field}_{len(names_found)}")
                        names_found[lang] = val
            # 价格（新增 priceRaw 支持）
            for pf in ("priceRaw", "price", "priceAmount", "amount", "listPrice", "salePrice"):
                pv = node.get(pf)
                if isinstance(pv, (int, float)) and pv > 1000:  # LV 价格至少 1000 日元
                    prices.append(float(pv))
                elif isinstance(pv, dict):
                    for sub in ("value", "amount", "centAmount"):
                        if isinstance(pv.get(sub), (int, float)) and pv[sub] > 0:
                            val = float(pv[sub])
                            if sub == "centAmount":
                                val /= 100.0
                            prices.append(val)
            # SKU / 货号
            for sf in ("skuId", "sku", "id", "identifier", "articleNumber", "reference"):
                sv = node.get(sf)
                if isinstance(sv, str) and 4 <= len(sv) <= 20:
                    if sv.startswith(("M", "N", "S", "G")):
                        if sf in ("articleNumber", "reference"):
                            if sv not in article_nos:
                                article_nos.append(sv)
                        else:
                            if sv not in sku_ids:
                                sku_ids.append(sv)
            # 图片
            for imf in ("image", "mainImage", "thumbnail", "picture"):
                im = node.get(imf)
                if isinstance(im, str) and im.startswith("http"):
                    images.append(im)
                elif isinstance(im, dict):
                    for k2 in ("url", "src", "href"):
                        if isinstance(im.get(k2), str) and im[k2].startswith("http"):
                            images.append(im[k2])
            if isinstance(node.get("images"), list):
                for im in node["images"]:
                    if isinstance(im, str) and im.startswith("http"):
                        images.append(im)
                    elif isinstance(im, dict):
                        for k2 in ("url", "src", "href"):
                            if isinstance(im.get(k2), str) and im[k2].startswith("http"):
                                images.append(im[k2])
            # medias 列表
            if isinstance(node.get("medias"), list):
                for m in node["medias"]:
                    if isinstance(m, dict):
                        for k2 in ("url", "src", "imageUrl"):
                            if isinstance(m.get(k2), str) and m[k2].startswith("http"):
                                images.append(m[k2])
                    elif isinstance(m, str) and m.startswith("http"):
                        images.append(m)
            # 递归
            for v in node.values():
                _walk(v)
        elif isinstance(node, list):
            for item in node:
                _walk(item)

    for jr in other_responses:
        _walk(jr.get("data") or jr)

    # 加入从 HTML/HEAD 中抓取的图片 URL
    images.extend([u for u in cap.image_urls if "louisvuitton.com" in u.lower()])

    # 去重
    def _unique(seq):
        seen = set()
        out = []
        for x in seq:
            if x in seen:
                continue
            seen.add(x)
            out.append(x)
        return out

    images = _unique(images)[:30]
    sku_ids = _unique(sku_ids)
    article_nos = _unique(article_nos)
    prices = sorted(set(prices))

    # 语言 → 字段映射
    name_local = ""
    for k, v in names_found.items():
        if any(mark in k.lower() for mark in ("local", "displayname", "name_0")):
            name_local = v
            break
    if not name_local and names_found:
        # 找第一个不是 tracking 的名字
        for v in names_found.values():
            if not any(kw in v.lower() for kw in ("conversion", "click", "track", "pixel")):
                name_local = v
                break
        if not name_local:
            name_local = next(iter(names_found.values()))

    # 过滤非包包（边界词匹配，避免 pet→petit 误匹配）
    if name_local:
        check_text = f"{name_local} {' '.join(sku_ids)} {' '.join(article_nos)}"
        hit_kw = adapter.contains_non_product_keyword(check_text)
        if hit_kw:
            logger.info("SKIP（非包包类 关键词=%s）: %s", hit_kw, name_local)
            # 返回带标记的 dict，让调用方不触发 BLOCKED 冷却
            return {
                "_skip_filter": True,
                "_skip_keyword": hit_kw,
                "sku_id": article_nos[0] if article_nos else (sku_ids[0] if sku_ids else ""),
                "name_local": name_local,
                "price": prices[-1] if prices else 0,
                "source_url": product_url,
                "crawled_at": datetime.utcnow().isoformat() + "Z",
            }

    merged.update({
        "name_local": name_local,
        "names": names_found,
        "sku_ids": sku_ids,
        "article_nos": article_nos,
        "price": prices[-1] if prices else 0,
        "price_values": prices,
        "images": images,
    })

    sku_id = (article_nos[0] if article_nos else (sku_ids[0] if sku_ids else ""))
    merged["sku_id"] = sku_id
    if not sku_id:
        logger.warning("无法提取 sku_id，丢弃: %s", product_url)
        return None
    return merged


def _extract_inventories(country: str, adapter, cap: ResponseCapture,
                         product_url: str, product: Optional[Dict]) -> List[Dict]:
    """从响应中提取门店库存。"""
    items = []
    for jr in cap.json_responses:
        try:
            parsed = extract_inventory_items(jr.get("data") or jr)
            for inv in parsed:
                inv.setdefault("country", country)
                inv.setdefault("currency", adapter.currency)
                inv.setdefault("source_url", product_url)
                inv["crawled_at"] = datetime.now().isoformat(timespec="seconds")
                if product:
                    inv.setdefault("sku_id", product.get("sku_id") or "")
                    inv.setdefault("article_no", (product.get("article_nos") or [""])[0])
                items.append(inv)
        except Exception as e:
            logger.debug("库存解析失败 %s", e)
    return items


# ==================================================================
# 批量补采门店库存（从已采集的商品列表读取 SKU，只采库存）
# ==================================================================
async def crawl_store_inventories_batch(
    country: str,
    adapter,
    limit: int = 0,
    skip_existing: bool = True,
) -> int:
    """批量补采门店库存（优化版）。

    优化点：
    1. 启动前清理多余标签页
    2. 每处理10个SKU重建page（避免DOM状态累积）
    3. 面板等待渐进式重试（最多3次，超时递增）
    4. 连续失败追踪 + 自适应冷却
    5. 错误后强制重建page

    Returns:
        成功采集的 SKU 数
    """
    dirs = _ensure_dirs(country)
    dedup_file = dirs["root"] / f"products_{country}_dedup.jsonl"
    if not dedup_file.exists():
        logger.error("[STORE-INV] %s 不存在，无法补采", dedup_file)
        return 0

    # 读取所有 SKU
    sku_list: List[Dict[str, str]] = []
    with open(dedup_file, "r", encoding="utf-8") as f:
        for line in f:
            try:
                obj = json.loads(line)
                sku_id = obj.get("sku_id", "")
                source_url = obj.get("source_url", "")
                if sku_id and source_url:
                    if country == "JP":
                        source_url = f"https://jp.louisvuitton.com/jpn-jp/products/-/{sku_id}"
                    elif country == "KR":
                        source_url = f"https://kr.louisvuitton.com/kor-kr/products/-/{sku_id}"
                    elif country == "CN":
                        source_url = f"https://cn.louisvuitton.com/chn-cn/products/-/{sku_id}"
                    sku_list.append({"sku_id": sku_id, "source_url": source_url})
            except Exception:
                pass
    logger.info("[STORE-INV] %s 共 %d 个 SKU 待处理", country, len(sku_list))
    logger.info("[STORE-INV] URL已修正为 /-/ 格式")

    # 跳过已有门店库存的 SKU
    inv_file = dirs["root"] / f"inventories_{country}_stores.jsonl"
    existing_inv_skus: set[str] = set()
    if skip_existing and inv_file.exists():
        with open(inv_file, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    obj = json.loads(line)
                    sid = obj.get("sku_id", "")
                    if sid:
                        existing_inv_skus.add(sid.lower())
                except Exception:
                    pass
        logger.info("[STORE-INV] 已有门店库存的 SKU: %d 个，将跳过",
                    len(existing_inv_skus))

    to_process = [s for s in sku_list if s["sku_id"].lower() not in existing_inv_skus]
    if limit:
        to_process = to_process[:limit]
    logger.info("[STORE-INV] 实际需处理: %d 个 SKU", len(to_process))
    if not to_process:
        return 0

    processed = 0
    success = 0
    consecutive_failures = 0
    no_panel_count = 0
    PAGE_LIFESPAN = 10
    failed_skus: list = []  # 反爬失败SKU列表（用于后续重试）

    # 无库存面板 SKU 记录文件（用于后续手动验证）
    no_panel_file = dirs["root"] / f"no_panel_skus_{country}.jsonl"
    # 读取已记录的无面板 SKU，避免重复记录
    no_panel_skus_existing: set = set()
    if no_panel_file.exists():
        with open(no_panel_file, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    obj = json.loads(line)
                    sid = obj.get("sku_id", "")
                    if sid:
                        no_panel_skus_existing.add(sid.lower())
                except Exception:
                    pass

    # 已跳过的无面板 SKU 也从 to_process 中排除（避免重复扫描）
    to_process = [s for s in to_process
                  if s["sku_id"].lower() not in no_panel_skus_existing]
    logger.info("[STORE-INV] 排除已记录无面板SKU后，实际需处理: %d 个 SKU", len(to_process))
    if not to_process:
        return 0

    async with async_playwright() as pw:
        # === 统一通过 BrowserManager 获取浏览器单例（不再自行 connect_over_cdp）===
        bm = await BrowserManager.get_instance(pw)
        page = await bm.new_scoped_page()
        logger.info("[STORE-INV] 浏览器管理器就绪，开始采集")

        try:
            for i, item in enumerate(to_process, 1):
                sku_id = item["sku_id"]
                product_url = item["source_url"]

                # 每 PAGE_LIFESPAN 个 SKU 重建 page（通过 BrowserManager 统一管理）
                if processed > 0 and processed % PAGE_LIFESPAN == 0:
                    logger.info("[STORE-INV] 重建page（已处理%d个SKU）", processed)
                    page = await bm.recreate_page(page)
                    await asyncio.sleep(2)

                # 批次间冷却
                if processed > 0 and processed % adapter.batch_size == 0:
                    cd = random.uniform(*adapter.batch_cooldown_range)
                    logger.info("[STORE-INV] 批次冷却 %.1f 秒（%d/%d）",
                                cd, i, len(to_process))
                    await asyncio.sleep(cd)

                # 连续失败自适应冷却
                if consecutive_failures >= 3:
                    cooldown = min(60 * consecutive_failures, 300)
                    logger.info("[STORE-INV] 连续失败%d次，冷却%d秒",
                                consecutive_failures, cooldown)
                    await asyncio.sleep(cooldown)
                    consecutive_failures = 0
                    page = await bm.recreate_page(page)

                try:
                    ok = await _safe_navigate(page, product_url,
                                              wait_ms=crawler_config.DETAIL_PAGE_WAIT_MS)
                    if not ok:
                        logger.warning("[STORE-INV] 导航失败 %s", product_url)
                        consecutive_failures += 1
                        processed += 1
                        await asyncio.sleep(random.uniform(*adapter.request_interval_range))
                        continue

                    # === 反爬软封禁检测：检查价格元素是否加载成功 ===
                    # Akamai 软封禁时页面能加载但商品内容缺失（价格元素不存在）
                    # 这种情况下"无面板"是假象，应判为反爬失败
                    price_loaded = False
                    try:
                        await page.wait_for_function(
                            "() => {"
                            "  const els = document.querySelectorAll('.lv-price .notranslate, .lv-price, [itemprop=\"price\"]');"
                            "  for (const el of els) {"
                            "    const t = (el.innerText||'').trim();"
                            "    if (t && (t.match(/[0-9]/g)||[]).length >= 3) return true;"
                            "  }"
                            "  return false;"
                            "}",
                            timeout=15000
                        )
                        price_loaded = True
                    except Exception as e:
                        logger.warning("[STORE-INV] %d/%d %s 价格元素超时(15s)=反爬软封禁",
                                       i, len(to_process), sku_id)
                        price_loaded = False

                    if not price_loaded:
                        # 价格元素未加载 = 反爬软封禁，不计为无面板
                        consecutive_failures += 1
                        failed_skus.append({"sku_id": sku_id, "url": product_url,
                                            "reason": "price_timeout_anti_crawler"})
                        processed += 1
                        await asyncio.sleep(random.uniform(*adapter.request_interval_range))
                        continue

                    # 渐进式面板等待（用sleep+evaluate替代wait_for_function，更可靠）
                    panel_text = _STORE_INVENTORY_CONFIG[country]["panel_text"]
                    panel_found = False
                    for attempt, timeout_s in enumerate([15, 25, 35]):
                        # 分段等待：每3秒检查一次面板是否存在
                        elapsed = 0
                        while elapsed < timeout_s:
                            try:
                                found = await page.evaluate(
                                    "() => {"
                                    "  const panels = document.querySelectorAll('.lv-expandable-panel');"
                                    "  for (const p of panels) {"
                                    f"    if ((p.innerText||'').includes('{panel_text}')) return true;"
                                    "  }"
                                    "  return false;"
                                    "}"
                                )
                            except Exception as e:
                                if elapsed == 0:
                                    logger.debug("[STORE-INV] %s evaluate异常: %s", sku_id, str(e)[:80])
                                found = False
                            if found:
                                panel_found = True
                                break
                            await asyncio.sleep(3)
                            elapsed += 3
                        if panel_found:
                            if attempt > 0:
                                logger.info("[STORE-INV] %s 面板等待成功(第%d次, %ds)",
                                            sku_id, attempt + 1, timeout_s)
                            break
                        if attempt < 2:
                            logger.debug("[STORE-INV] %s 面板等待超时(%ds)，重试...",
                                        sku_id, timeout_s)
                            await asyncio.sleep(2)
                        else:
                            logger.warning("[STORE-INV] %d/%d %s 面板等待超时(%ds)",
                                          i, len(to_process), sku_id, timeout_s)

                    if not panel_found:
                        # 无库存面板：记录到独立文件，供后续手动验证
                        # 说明：可能是新上市产品暂未铺设门店库存，或线上专属商品
                        no_panel_count += 1
                        no_panel_record = {
                            "sku_id": sku_id,
                            "country": country,
                            "source_url": product_url,
                            "reason": "no_inventory_panel",
                            "note": "新上市产品或线上专属，需人工验证",
                            "detected_at": datetime.now().isoformat(timespec="seconds"),
                        }
                        _append_jsonl(no_panel_file, no_panel_record)
                        logger.info("[STORE-INV] %d/%d %s: 无库存面板(已记录,待人工验证) #%d",
                                    i, len(to_process), sku_id, no_panel_count)
                        processed += 1
                        await asyncio.sleep(random.uniform(*adapter.request_interval_range))
                        continue

                    # 采集门店库存
                    store_invs = await collect_store_inventories_multi(page, country, sku_id)
                    if store_invs:
                        for inv in store_invs:
                            inv["sku_id"] = sku_id
                            inv["country"] = country
                            inv["currency"] = adapter.currency
                            inv["source_url"] = product_url
                            inv["crawled_at"] = datetime.now().isoformat(timespec="seconds")
                            _append_jsonl(inv_file, inv)
                        success += 1
                        consecutive_failures = 0  # 成功重置连续失败计数
                        logger.info("[STORE-INV] %d/%d %s: %d 家门店",
                                    i, len(to_process), sku_id, len(store_invs))
                    else:
                        consecutive_failures += 1
                        logger.info("[STORE-INV] %d/%d %s: 0 家门店",
                                    i, len(to_process), sku_id)

                except Exception as e:
                    logger.warning("[STORE-INV] 抓取失败 %s: %s", sku_id, e)
                    consecutive_failures += 1
                    page = await bm.recreate_page(page)

                processed += 1
                # 请求间隔
                await asyncio.sleep(random.uniform(*adapter.request_interval_range))

        finally:
            await bm.release_page(page)
            # 注意：不调用 bm.cleanup()，因为 CDP 模式下不关闭用户的 Chrome
            # 标签页清理已由 BrowserManager 内部管理

    logger.info("[STORE-INV] %s 完成: 处理 %d 个，成功 %d 个，无面板(待验证) %d 个",
                country, processed, success, no_panel_count)
    # 将无面板计数暴露给调用方（通过模块级变量，便于 main 函数读取通知）
    globals()['_LAST_NO_PANEL_COUNT'] = no_panel_count
    globals()['_LAST_NO_PANEL_FILE'] = str(no_panel_file)
    return success


# ==================================================================
# 全量：列表 + 所有详情
# ==================================================================
async def crawl_all(country: str, adapter, limit: int = 0,
                     fetch_store_inventory: bool = False):
    dirs = _ensure_dirs(country)
    # 1. 列表
    slugs = await crawl_list(country, adapter)
    logger.info("[ALL] %s 总商品数: %d", country, len(slugs))
    if not slugs:
        return
    # 2. 增量：已写 products_XX.jsonl 的 sku_id 不再爬
    existing_skus = set()
    if dirs["products"].exists():
        with open(dirs["products"], "r", encoding="utf-8") as f:
            for line in f:
                try:
                    obj = json.loads(line)
                    sid = obj.get("sku_id")
                    if sid:
                        existing_skus.add(sid.lower())
                except Exception:
                    pass
    # slug -> url
    url_template = adapter.get_product_url if hasattr(adapter, "get_product_url") else None
    to_process = []
    for slug in slugs:
        if slug.lower() in existing_skus:
            continue
        to_process.append(slug)
    if limit:
        to_process = to_process[:limit]
    logger.info("[ALL] 需新抓取 %d 商品，总 %d（已去重已存在 sku）",
                len(to_process), len(slugs))
    if not to_process:
        return
    # 3. 逐个详情
    processed = 0
    async with async_playwright() as pw:
        page = await _get_page_via_cdp(pw)
        try:
            for i, slug in enumerate(to_process, 1):
                # 每批次休息（防反爬）
                if processed > 0 and processed % adapter.batch_size == 0:
                    cd = random.uniform(*adapter.batch_cooldown_range)
                    logger.info("[ALL] 批次冷却 %.1f 秒（%d/%d）", cd, i, len(to_process))
                    await asyncio.sleep(cd)
                # 每 N 个商品长暂停
                if processed > 0 and processed % crawler_config.LONG_PAUSE_EVERY == 0:
                    lp = random.uniform(crawler_config.LONG_PAUSE_MIN_SEC,
                                        crawler_config.LONG_PAUSE_MAX_SEC)
                    logger.info("[ALL] 长暂停 %.1f 秒", lp)
                    await asyncio.sleep(lp)
                # 详情抓取（复用同一 page）
                product_url = url_template(slug) if url_template else slug
                try:
                    async with ResponseCapture(page, country, dirs["raw"]) as cap:
                        ok = await _safe_navigate(page, product_url,
                                                  wait_ms=crawler_config.DETAIL_PAGE_WAIT_MS)
                        if ok:
                            result = _extract_product(country, adapter, cap, product_url)
                            if result:
                                if not result["sku_id"].lower() in existing_skus:
                                    _append_jsonl(dirs["products"], result)
                                    existing_skus.add(result["sku_id"].lower())
                            # 库存
                            inventories = _extract_inventories(country, adapter, cap, product_url, result)
                            for inv in inventories:
                                _append_jsonl(dirs["inventories"], inv)
                except Exception as e:
                    logger.warning("抓取失败 %s: %s", slug, e)
                    # 失败就建个新 page，避免同一个页面出问题
                    try:
                        await page.close()
                    except Exception:
                        pass
                    page = await _get_page_via_cdp(pw)
                processed += 1
                # 请求间隔
                await asyncio.sleep(random.uniform(*adapter.request_interval_range))
        finally:
            try:
                await page.close()
            except Exception:
                pass
    logger.info("[ALL] %s 全部完成，共处理 %d 个商品", country, processed)


# ==================================================================
# CLI
# ==================================================================
def main():
    parser = argparse.ArgumentParser(description="LV 多国家官网爬虫（JP / KR / CN），包包类")
    parser.add_argument("--country", required=True,
                        choices=["JP", "KR", "CN", "FR", "GB", "CH", "DE", "IT", "ES"],
                        help="目标国家/地区")
    parser.add_argument("--mode", required=True,
                        choices=["list", "single", "all", "store-inventory"],
                        help="list=仅列表抽 slug；single=单商品详情；all=列表+所有详情；"
                             "store-inventory=批量补采门店库存")
    parser.add_argument("--url", default="",
                        help="single 模式必填：商品详情 URL 或 slug")
    parser.add_argument("--limit", type=int, default=0,
                        help="all 模式最多抓取多少个新详情（0=不限制）")
    parser.add_argument("--fetch-store-inventory", action="store_true",
                        help="single/all 模式下额外采集门店库存（DOM 交互，较慢）")
    args = parser.parse_args()

    adapter = get_brand("LV", args.country)
    logger.info("启动: 品牌=%s  国家=%s  货币=%s  模式=%s  门店库存=%s",
                adapter.brand_id, adapter.country, adapter.currency, args.mode,
                args.fetch_store_inventory)
    logger.info("站点: %s", adapter.base_url)

    if args.mode == "single":
        if not args.url:
            print("ERROR: --mode single 必须传 --url <详情页URL或slug>")
            sys.exit(2)
        asyncio.run(crawl_single(args.country, adapter, args.url,
                                   fetch_store_inventory=args.fetch_store_inventory))
    elif args.mode == "list":
        asyncio.run(crawl_list(args.country, adapter))
    elif args.mode == "store-inventory":
        asyncio.run(crawl_store_inventories_batch(args.country, adapter,
                                                    limit=args.limit))
        # 采集结束后，汇总无面板 SKU（需人工验证）
        no_panel_count = globals().get('_LAST_NO_PANEL_COUNT', 0)
        no_panel_file = globals().get('_LAST_NO_PANEL_FILE', '')
        if no_panel_count > 0 and no_panel_file:
            logger.warning("=" * 60)
            logger.warning("[需人工验证] %s 站发现 %d 个无库存面板SKU", args.country, no_panel_count)
            logger.warning("[需人工验证] 记录文件: %s", no_panel_file)
            logger.warning("[需人工验证] 可能原因: 新上市产品/线上专属/页面结构变更")
            logger.warning("=" * 60)
            # 输出无面板SKU列表（便于飞书通知）
            try:
                import json as _json
                with open(no_panel_file, "r", encoding="utf-8") as f:
                    skus = [_json.loads(l) for l in f if l.strip()]
                print(f"\n=== 无面板SKU清单（{args.country}）===")
                for s in skus:
                    print(f"  {s.get('sku_id')}  {s.get('source_url')}")
                print(f"=== 共 {len(skus)} 个，需人工验证 ===\n")
            except Exception:
                pass
    else:  # all
        asyncio.run(crawl_all(args.country, adapter, limit=args.limit,
                               fetch_store_inventory=args.fetch_store_inventory))


if __name__ == "__main__":
    main()
