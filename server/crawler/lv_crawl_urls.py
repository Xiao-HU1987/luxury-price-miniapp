"""LV 日本官网包包全量抓取（基于完整商品 URL 列表）

用法:
  cd server
  venv/bin/python3.11 -m crawler.lv_crawl_urls --country JP

输入: data/lv/{country}/product_urls_{country}.json  (完整商品 URL 列表)
输出: data/lv/{country}/products_{country}.jsonl     (解析后的商品数据)
      data/lv/{country}/inventories_{country}.jsonl  (门店库存数据)
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

# 清除代理环境变量
for _proxy_var in ("http_proxy", "https_proxy", "HTTP_PROXY", "HTTPS_PROXY",
                    "all_proxy", "ALL_PROXY"):
    os.environ.pop(_proxy_var, None)

from playwright.async_api import async_playwright, Page, Response

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from crawler import config as crawler_config
from crawler.brands import get_brand
from crawler.lv_crawler_multi import (
    ResponseCapture, _extract_product, _extract_inventories,
    _ensure_dirs, _append_jsonl, _load_existing_ids,
    _safe_navigate,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("lv_crawl_urls")


async def _ensure_browser_and_page(pw, browser=None, ctx=None, page=None):
    """重建 browser / context / page（任意一个失效时重建整棵树，避免半残状态）。

    反爬攻防核心：韩国LV在弹窗轰炸 / 超时 / 反爬后，会把 tab、context 悄悄销毁，
    导致后续操作全报错"page/context/browser has been closed"，但旧代码只重建page，
    实际上ctx也可能被销毁，需要全链路重建。
    """
    try:
        # 先尝试检测 page / ctx / browser 是否存活
        if page is not None:
            try:
                _ = await page.title()
            except Exception:
                page = None
        if ctx is not None and page is None:
            try:
                # 尝试拿一个新 page，如果失败则 ctx 已死
                test_page = await ctx.new_page()
                await test_page.close()
            except Exception:
                ctx = None
        if browser is not None and ctx is None:
            try:
                _ = await browser.contexts
                if not browser.contexts:
                    ctx = await browser.new_context()
                else:
                    ctx = browser.contexts[0]
            except Exception:
                browser = None
    except Exception:
        browser = None
        ctx = None
        page = None

    if browser is None:
        browser = await pw.chromium.connect_over_cdp(crawler_config.CDP_ENDPOINT)
        ctx = browser.contexts[0] if browser.contexts else await browser.new_context()
        page = await ctx.new_page()
    elif ctx is None:
        ctx = browser.contexts[0] if browser.contexts else await browser.new_context()
        page = await ctx.new_page()
    elif page is None:
        page = await ctx.new_page()
    return browser, ctx, page


async def _is_page_alive(page) -> bool:
    try:
        _ = await page.title()
        return True
    except Exception:
        return False


async def _detect_akamai_block(cap) -> bool:
    """从 ResponseCapture 中识别 Akamai/BotDefender 拦截。"""
    akamai_keys = ('akamai','bot defender','challenge','verif','captcha','blocked','forbidden','403','too many request','rate limit')
    # 1) json_responses 里的 _blocked / _akamai 标记
    for jr in cap.json_responses:
        if jr.get("_akamai") or jr.get("_blocked"):
            return True
    # 2) page 标题 / DOM 拦截检测
    try:
        title = (await cap.page.title()).lower()
        if any(k in title for k in ('akamai','challenge','verif','captcha','block','access denied')):
            return True
        html_hint = await cap.page.evaluate('''() => {
            try { return document.body ? document.body.innerText.substring(0,2000).toLowerCase() : ''; }
            catch(e){ return ''; }
        }''')
        if any(k in html_hint for k in akamai_keys):
            return True
    except Exception:
        pass
    return False


async def _browse_category_for_warmup(page, adapter):
    """模拟真实用户：先浏览一个分类页（滚动、点击、等待），给 Akamai 降温。

    KR 单独的路径：因为 KR Akamai 对连续详情页访问敏感，所以每次切换到保守
    模式都先访问一下女士/男士分类页，制造"用户正常浏览路径"，把风控分数降下来。
    """
    urls = getattr(adapter, 'category_urls', None) or [getattr(adapter, 'base_url', '')]
    if not urls:
        return
    cat_url = random.choice(urls)
    logger.info("[WARMUP] 模拟用户浏览分类页 %s", cat_url[50:])
    try:
        await page.goto(cat_url, timeout=60_000, wait_until="domcontentloaded")
        await asyncio.sleep(random.uniform(6, 10))
        # 关弹窗
        try:
            await page.evaluate('''() => {
                const sels = [
                    'button[aria-label*="닫기"]','button[aria-label*="close" i]',
                    'button[aria-label*="閉じる"]',
                    '.lv-popup-close','.lv-modal-close','[class*="popup"] button',
                    '[class*="newsletter"] button',
                ];
                for (const s of sels) {
                    try { document.querySelectorAll(s).forEach(b => {
                        const r=b.getBoundingClientRect();
                        if(r.width>0 && r.height>0) b.click();
                    })}catch(e){}
                }
            }''')
        except Exception:
            pass
        # 滚动几下
        for _ in range(random.randint(4, 8)):
            await page.evaluate(f'window.scrollTo(0, {random.randint(300, 1500)})')
            await asyncio.sleep(random.uniform(0.8, 2.0))
        # 随机点击一个商品链接
        try:
            href = await page.evaluate('''() => {
                const anchors = Array.from(document.querySelectorAll('a[href*="/products/"]'));
                if (!anchors.length) return null;
                const a = anchors[Math.floor(Math.random() * anchors.length)];
                const r = a.getBoundingClientRect();
                if (r.width>0 && r.height>0) { a.click(); return a.href; }
                return a.href;
            }''')
            if href:
                logger.info("[WARMUP] 点击预览商品 %s", href.split('/products/')[-1][:60])
                await asyncio.sleep(random.uniform(5, 10))
        except Exception:
            pass
    except Exception as e:
        logger.info("[WARMUP] 分类页预热跳过: %s", e)


async def _classify_failure(cap, ok: bool, antibot_detected: bool, product_url: str) -> dict:
    """多国家（JP/KR/CN）：动态判断失败原因（不固化），返回原因分类+建议动作。

    分类：
      - '404_gone'      : 商品真正下架（中/韩/英 404/not found/找不到页面且 Akamai 未触发）→ 直接跳过URL
      - 'akamai_challenge' : Akamai 启动验证挑战（中/韩/英 challenge/验证您的身份/滑块/인증/답변）
                             → BLOCKED + 冷却较久 + 建议手动过
      - 'akamai_403_rate'  : 403/forbidden/访问过于频繁/너무 많은 요청 → BLOCKED + 冷却换URL（不重试）
      - 'network_timeout'  : 纯超时/断网，没看到 Akamai 关键词 → WARMING 就够了
      - 'unknown_parse'    : 200 OK 但解析不到（最可能接口被拦截，DOM没渲染全）→ HOT/BLOCKED
    """
    info = {"kind": "unknown_parse", "http_statuses": [], "title": "", "dom_snippet": ""}
    # 收集状态码
    try:
        info["http_statuses"] = [int(jr.get("status", 0)) for jr in cap.json_responses if jr.get("status")]
    except Exception:
        pass
    try:
        info["title"] = (await asyncio.wait_for(cap.page.title(), timeout=10) or "").lower()
    except Exception:
        pass
    try:
        info["dom_snippet"] = (await asyncio.wait_for(cap.page.evaluate('''() => {
            try { return document.body ? document.body.innerText.substring(0,1500).toLowerCase() : ''; }
            catch(e){ return ''; }
        }'''), timeout=10)) or ""
    except Exception:
        info["dom_snippet"] = ""
    dom = info["dom_snippet"]
    title = info["title"]
    statuses = info["http_statuses"]
    any_404 = any(s == 404 for s in statuses)
    any_403 = any(s in (403, 302) for s in statuses)

    # 1) 404 且无反爬迹象 → 商品下架（中/韩/日/英）
    if (any_404 or "404" in title or "not found" in title or "페이지를 찾을 수 없습니다" in dom or
        "找不到页面" in dom or "页面不存在" in dom or "商品已下架" in dom or "no longer available" in dom or
        "ページが見つかりません" in dom):
        if not antibot_detected:
            info["kind"] = "404_gone"
            return info

    # 2) 明确 Akamai Challenge / Captcha 需要人工或长冷却（中/韩/日/英）
    challenge_keys = (
        'challenge','verif','captcha','prove you are human','bot defender',
        # CN
        '验证您的身份','请完成验证','验证您是真人','请验证您不是机器人','安全验证','请通过验证',
        '滑动验证','请按住滑块','拖动滑块','完成以下验证','请先通过验证','人机验证','登录验证',
        # KR
        '인증','답변','인증해 주세요','로봇이 아닙니다',
        # JP
        '本人確認','認証してください','ロボットではないことを確認',
    )
    if antibot_detected and any(k in dom or k in title for k in challenge_keys):
        info["kind"] = "akamai_challenge"
        return info

    # 3) 403 / rate limit 类（风控拦截但无挑战页，冷却换URL更划算）
    rate_keys = (
        'forbidden','403','too many request','rate limit','access denied','blocked',
        # CN
        '访问过于频繁','访问次数过多','请求过多','操作频繁','请稍后再试','频繁访问',
        '暂时无法访问','限制访问','当前访问人数过多','访问被拒绝',
        # KR
        '너무 많은 요청','차단','잠시 후 다시 시도',
        # JP
        'リクエストが多すぎます','アクセスが拒否されました','しばらくしてから',
    )
    if antibot_detected or any_403 or any(k in dom or k in title for k in rate_keys):
        info["kind"] = "akamai_403_rate"
        return info

    # 4) 超时/断网但无Akamai
    if not ok and not antibot_detected and not statuses:
        info["kind"] = "network_timeout"
        return info

    # 5) 默认：页面200但没解析到（接口被拦 / DOM不完整，最常见）
    info["kind"] = "unknown_parse"
    return info


async def crawl_from_urls(country: str, adapter, limit: int = 0):
    dirs = _ensure_dirs(country)
    urls_file = dirs["root"] / f"product_urls_{country}.json"

    if not urls_file.exists():
        logger.error("URL 列表文件不存在: %s", urls_file)
        return

    with open(urls_file, "r", encoding="utf-8") as f:
        all_urls = json.load(f)

    product_urls = []
    seen = set()
    for url in all_urls:
        if url in seen:
            continue
        seen.add(url)
        if "/products/" not in url:
            continue
        product_urls.append(url)

    logger.info("[URLS] 总 URL 数: %d", len(product_urls))

    existing_skus: set[str] = set()
    # 1) _load_existing_ids（如果实现是读 set，已经 lower 过）
    _loaded = _load_existing_ids(dirs["products"], "sku_id")
    existing_skus.update(s.lower() for s in _loaded)
    # 2) 兼容：从 JSONL 再扫一遍，_load_existing_ids 可能没覆盖全部（例如文件被写入后又追加）
    try:
        with open(dirs["products"], "r", encoding="utf-8") as _ff:
            for _line in _ff:
                try:
                    _d = json.loads(_line)
                    _s = (_d.get("sku_id") or "").strip()
                    if _s:
                        existing_skus.add(_s.lower())
                except Exception:
                    pass
    except Exception:
        pass

    to_process = []
    for url in product_urls:
        sku_from_url = url.rstrip("/").split("/")[-1].split("?")[0]
        if sku_from_url.lower() in existing_skus:
            continue
        to_process.append(url)

    if limit:
        to_process = to_process[:limit]

    logger.info("[URLS] 需新抓取 %d 商品（已去重已存在 %d）", len(to_process), len(existing_skus))

    if not to_process:
        logger.info("没有新商品需要抓取")
        return

    processed = 0
    success = 0
    fail = 0

    # ====== 四态自适应 + 动态失败分类（不固化策略，随KR页面反馈实时调整）======
    engine_state: str = "NORMAL"
    engine_state_counts: Dict[str, int] = {"NORMAL": 0, "WARMING": 0, "HOT": 0, "BLOCKED": 0}
    current_url_retries: int = 0

    # BLOCKED 冷却起步 60s；指数退避上限 15 min（按用户建议：> KR批次冷却5-10min 即可）
    blocked_cd = 60.0
    BLOCKED_CEILING_SEC = 15 * 60.0

    def _log_state_transition(new_state: str, reason: str):
        nonlocal engine_state
        if engine_state != new_state:
            logger.warning(
                "[STATE] %s → %s  (原因: %s, 累计 N=%d W=%d H=%d B=%d)",
                engine_state, new_state, reason,
                engine_state_counts["NORMAL"], engine_state_counts["WARMING"],
                engine_state_counts["HOT"], engine_state_counts["BLOCKED"])
            engine_state = new_state
        engine_state_counts[engine_state] += 1

    async with async_playwright() as pw:
        browser, ctx, page = await _ensure_browser_and_page(pw)

        try:
            i = 0
            while i < len(to_process):
                product_url = to_process[i]
                i += 1  # 默认 +1，重试时再 i-=1 回退

                # 批次冷却 / 长暂停（仅 NORMAL）
                if processed > 0 and processed % adapter.batch_size == 0 and engine_state == "NORMAL":
                    cd = random.uniform(*adapter.batch_cooldown_range)
                    logger.info("[BATCH] 批次冷却 %.1f 秒（已处理商品 %d/%d）", cd, processed, len(to_process))
                    await asyncio.sleep(cd)
                if processed > 0 and processed % crawler_config.LONG_PAUSE_EVERY == 0 and engine_state == "NORMAL":
                    lp = random.uniform(crawler_config.LONG_PAUSE_MIN_SEC, crawler_config.LONG_PAUSE_MAX_SEC)
                    logger.info("[PAUSE] 长暂停 %.1f 秒", lp)
                    await asyncio.sleep(lp)

                logger.info("[%d/%d] [状态=%s(retry=%d)] %s",
                            i, len(to_process), engine_state, current_url_retries, product_url)

                if not await _is_page_alive(page):
                    logger.warning("[RECOVER] page/context/browser 已销毁，整棵重建...")
                    browser, ctx, page = await _ensure_browser_and_page(pw, browser, ctx, page)

                antibot_detected = False
                fail_info = None
                _cdp_timeout_hit = False
                try:
                    async with ResponseCapture(page, country, dirs["raw"]) as cap:
                        try:
                            ok = await asyncio.wait_for(
                                _safe_navigate(page, product_url,
                                               wait_ms=crawler_config.DETAIL_PAGE_WAIT_MS),
                                timeout=45.0,  # CDP 总操作超时 45 秒：防断连卡死
                            )
                        except asyncio.TimeoutError:
                            logger.error("[CDP TIMEOUT] _safe_navigate 耗时 >45 秒，判定断连，强制重建 browser/page")
                            _cdp_timeout_hit = True
                            ok = False
                            antibot_detected = False
                        if not _cdp_timeout_hit and await _detect_akamai_block(cap):
                            logger.error("[ANTI-BOT] ⛔ Akamai/BotDefender 命中")
                            antibot_detected = True
                            ok = False

                    result = _extract_product(country, adapter, cap, product_url)
                    parsed_ok = bool(result and result.get("sku_id"))

                    # ========= 404 误判拦截：DOM兜底从URL提取了SKU但页面实为404 =========
                    if parsed_ok:
                        _name = (result.get("name_local") or "").strip()
                        _price = result.get("price", 0) or 0
                        _404_names = ("需要更多帮助", "access denied", "ページが見つかりません",
                                      "페이지를 찾을 수 없습니다", "页面不存在", "not found")
                        if _price == 0 and any(k in _name.lower() for k in _404_names):
                            logger.info("  🚫 404误判拦截 sku=%s name=%s — 不写入", result.get("sku_id",""), _name[:30])
                            parsed_ok = False
                            result = None

                    # ========= SKIP：非包包类被适配器主动过滤 =========
                    if parsed_ok and result.get("_skip_filter"):
                        sku_lc = (result.get("sku_id") or "").lower()
                        kw = result.get("_skip_keyword", "?")
                        logger.info("  ⏭  SKIP（关键词=%s）sku=%s name=%s price=%s — 过滤不计入反爬失败",
                                    kw, sku_lc or "(无)",
                                    (result.get("name_local", "") or "")[:25],
                                    result.get("price", 0))
                        if sku_lc and sku_lc not in existing_skus:
                            existing_skus.add(sku_lc)  # 下次启动跳过
                        # 不切状态、不重试、不触发 BLOCKED 冷却
                        processed += 1
                        current_url_retries = 0
                        lo, hi = adapter.request_interval_range
                        await asyncio.sleep(random.uniform(lo, hi))
                        continue

                    # ========= 成功：解析到 SKU =========
                    if parsed_ok:
                        sku_lc = result["sku_id"].lower()
                        if sku_lc not in existing_skus:
                            _append_jsonl(dirs["products"], result)
                            existing_skus.add(sku_lc)
                            success += 1
                            logger.info("  ✅ sku=%s name=%s price=%s  (来源: %s)",
                                        result["sku_id"],
                                        (result.get("name_local", "") or "")[:25],
                                        result.get("price", 0),
                                        "SKU API" if (result.get("skus") and len(result["skus"]) > 0) else "DOM 兜底")
                        else:
                            logger.info("  ✅ sku=%s 已存在", result["sku_id"])

                        if engine_state != "NORMAL":
                            _log_state_transition("NORMAL", reason=f"OK {result['sku_id']}")
                        blocked_cd = 60.0
                        current_url_retries = 0

                        try:
                            inventories = _extract_inventories(country, adapter, cap, product_url, result)
                            if inventories:
                                for inv in inventories:
                                    _append_jsonl(dirs["inventories"], inv)
                        except Exception as e:
                            logger.debug("  库存解析跳过: %s", e)

                        processed += 1
                        lo, hi = adapter.request_interval_range
                        if engine_state == "NORMAL":
                            await asyncio.sleep(random.uniform(lo, hi))
                        elif engine_state == "WARMING":
                            await asyncio.sleep(random.uniform(lo * 2.2, hi * 2.2))
                        else:
                            await asyncio.sleep(random.uniform(lo * 3.5, hi * 3.5))
                        continue

                    # ========= 失败：先处理 CDP 超时，再走常规失败分类 =========
                    if _cdp_timeout_hit:
                        # CDP 断连卡死：整棵重建 browser/ctx/page，重试当前 URL（不记为反爬失败）
                        logger.warning("[CDP RECOVER] 整棵重建（browser→ctx→page）")
                        try:
                            await page.close()
                        except Exception:
                            pass
                        try:
                            await ctx.close()
                        except Exception:
                            pass
                        browser, ctx, page = await _ensure_browser_and_page(pw, None, None, None)
                        wait_s = random.uniform(20, 40)
                        logger.info("[CDP RECOVER] 冷却 %.1fs，然后重试当前 URL", wait_s)
                        await asyncio.sleep(wait_s)
                        if current_url_retries < 3:
                            i -= 1  # 回退，重试当前 URL
                            current_url_retries += 1
                        else:
                            logger.error("[CDP RECOVER] CDP 超时已 3 次，放弃当前 URL: %s", product_url[-60:])
                            processed += 1
                            current_url_retries = 0
                        continue

                    fail += 1
                    current_url_retries += 1
                    fail_info = await _classify_failure(cap, ok, antibot_detected, product_url)
                    logger.warning(
                        "  ⚠️ 解析空  kind=%s  title=%s  statuses=%s  antibot=%s  retry=%d",
                        fail_info["kind"], (fail_info["title"] or "")[:50],
                        fail_info["http_statuses"], antibot_detected, current_url_retries)

                    # --------- 404 / 下架 ：一次都不重试，直接跳过（避免固执）---------
                    if fail_info["kind"] == "404_gone":
                        logger.error("[SKIP-404] 商品已下架/不存在，直接跳过：%s", product_url[-60:])
                        current_url_retries = 0
                        processed += 1
                        # 状态不升（这不是反爬问题），NORMAL 就保持，其他也至少回退到 WARMING
                        if engine_state in ("HOT", "BLOCKED"):
                            _log_state_transition("WARMING", reason="遇到 404，从 B/H 退到 W")
                        continue

                    # --------- 状态迁移（根据 kind 调整，不固化线性升级）---------
                    if fail_info["kind"] == "network_timeout":
                        # 纯网络超时：只升到 WARMING（不会直接 BLOCKED）
                        if engine_state == "NORMAL":
                            _log_state_transition("WARMING", reason="network_timeout")
                        # 已经在 W/H/B 的保持，不会进一步升级
                    elif fail_info["kind"] == "akamai_challenge":
                        # 挑战页出现：直接 BLOCKED（不是1/2/3线性），这是明确的风控信号
                        _log_state_transition("BLOCKED", reason="akamai_challenge 出现")
                    elif fail_info["kind"] == "akamai_403_rate":
                        # 403/rate_limit：如果在 NORMAL 就直接 HOT；W 升 B；H/B 保持 B
                        if engine_state == "NORMAL":
                            _log_state_transition("HOT", reason="akamai_403_rate (NORMAL→HOT)")
                        elif engine_state == "WARMING":
                            _log_state_transition("BLOCKED", reason="akamai_403_rate (W→B)")
                        else:
                            _log_state_transition("BLOCKED", reason="akamai_403_rate 保持")
                    else:  # unknown_parse
                        # 线性：N→W→H→B（保守做法，因为可能是接口被拦但没表现出特征）
                        if engine_state == "NORMAL":
                            _log_state_transition("WARMING", reason="unknown_parse N→W")
                        elif engine_state == "WARMING":
                            _log_state_transition("HOT", reason="unknown_parse W→H")
                        else:
                            _log_state_transition("BLOCKED", reason="unknown_parse 进入 BLOCKED")

                    # --------- 执行各状态动作（按 kind 动态调冷却时长）---------
                    if engine_state == "WARMING":
                        try: await page.close()
                        except Exception: pass
                        browser, ctx, page = await _ensure_browser_and_page(pw, browser, ctx, page)
                        wait_s = random.uniform(25, 55)
                        logger.info("[WARMING] 新 tab + 冷却 %.1fs 后决定是否重试同URL", wait_s)
                        await asyncio.sleep(wait_s)

                    elif engine_state == "HOT":
                        try: await page.close()
                        except Exception: pass
                        try: await ctx.close()
                        except Exception: pass
                        browser, ctx, page = await _ensure_browser_and_page(pw, None, None, None)
                        await _browse_category_for_warmup(page, adapter)
                        # 动态：akamai_403_rate 类冷却长一点，其他正常 HOT 90-150s
                        if fail_info["kind"] == "akamai_403_rate":
                            wait_s = random.uniform(150, 240)
                        else:
                            wait_s = random.uniform(90, 150)
                        logger.warning("[HOT] 整棵重建+分类页预热，冷却 %.1fs", wait_s)
                        await asyncio.sleep(wait_s)

                    else:  # BLOCKED
                        try: await page.close()
                        except Exception: pass
                        try: await ctx.close()
                        except Exception: pass
                        browser, ctx, page = await _ensure_browser_and_page(pw, None, None, None)
                        # 预热 1 次（challenge 50% 预热 2 次）
                        await _browse_category_for_warmup(page, adapter)
                        await asyncio.sleep(random.uniform(20, 40))
                        if fail_info["kind"] == "akamai_challenge" and random.random() < 0.5:
                            await _browse_category_for_warmup(page, adapter)
                            await asyncio.sleep(random.uniform(20, 40))
                        # 动态冷却（按 kind 给系数）
                        if fail_info["kind"] == "akamai_challenge":
                            k = 1.3  # challenge 最久
                            human_tip = "💡 建议：Chrome 打开任一 KR 商品，手动过滑块/验证，完成后脚本冷却结束会继续抓"
                        elif fail_info["kind"] == "akamai_403_rate":
                            k = 1.0
                            human_tip = "💡 403/Rate：切换到下一个商品（不固执重试当前URL），引擎自动降速"
                        else:
                            k = 0.8
                            human_tip = ""
                        wait_s = random.uniform(blocked_cd * 0.85 * k, blocked_cd * 1.2 * k)
                        logger.error(
                            "[BLOCKED] kind=%s 冷却 %.1fs（下次 %.0fs 起步，上限%.0fs）%s",
                            fail_info["kind"], wait_s,
                            min(blocked_cd * 1.5, BLOCKED_CEILING_SEC), BLOCKED_CEILING_SEC,
                            f"\n{human_tip}" if human_tip else "")
                        await asyncio.sleep(wait_s)
                        blocked_cd = min(blocked_cd * 1.5, BLOCKED_CEILING_SEC)

                    # --------- 重试 or 跳 URL（关键：反爬已启动时，不固执同URL）---------
                    # 规则：
                    #  - 404 已在上面直接跳过
                    #  - akamai_challenge / akamai_403_rate：反爬机制已启动 → 不重试同URL（重试没用）
                    #  - network_timeout / unknown_parse：同URL最多重试 3 次
                    is_antibot_active = fail_info["kind"] in ("akamai_challenge", "akamai_403_rate")
                    retry_cap = 0 if is_antibot_active else 3

                    if current_url_retries <= retry_cap and not is_antibot_active:
                        logger.warning(
                            "[RETRY] kind=%s  同URL 第 %d/%d 次重试: %s",
                            fail_info["kind"], current_url_retries, retry_cap, product_url[-60:])
                        i -= 1
                        continue
                    else:
                        # 反爬启动 or 达到重试上限 → 跳，脚本继续抓下一个（永不 ABORT）
                        if is_antibot_active:
                            logger.error(
                                "[SKIP-ANTIBOT] kind=%s：反爬机制已启动，不固执同URL，跳到下一个商品。URL=%s",
                                fail_info["kind"], product_url[-80:])
                        else:
                            logger.error(
                                "[SKIP-URL] kind=%s：同 URL 重试 %d 次，仍失败，跳过：%s",
                                fail_info["kind"], current_url_retries, product_url[-80:])
                        current_url_retries = 0
                        processed += 1
                        # 跳过 URL 不把状态降到 NORMAL（风控可能还在），保持当前状态的节奏
                        # 但 BLOCKED 的话拉回到 HOT（不然 BLOCKED 冷却每次都超长，后续所有URL都卡死）
                        if engine_state == "BLOCKED":
                            _log_state_transition("HOT", reason="跳过URL后 B→H（避免后续全被 BLOCKED 拖死）")

                except Exception as e:
                    logger.warning("  ❌ 抓取异常: %s (%s)", type(e).__name__, e)
                    fail += 1
                    current_url_retries += 1
                    # 异常分类：TimeoutError 类 → network_timeout；其他直接升状态
                    is_timeout = 'timeout' in type(e).__name__.lower() or 'timeout' in str(e).lower()
                    if engine_state == "NORMAL":
                        _log_state_transition("WARMING", reason=f"异常:{type(e).__name__} timeout={is_timeout}")
                    elif engine_state == "WARMING":
                        _log_state_transition("HOT", reason=f"W 下再异常:{type(e).__name__}")
                    else:
                        _log_state_transition("BLOCKED", reason=f"{engine_state} 下再异常")
                    # 动作：至少换 tab；严重则整棵重建 + 预热
                    try: await page.close()
                    except Exception: pass
                    if engine_state in ("HOT", "BLOCKED"):
                        try: await ctx.close()
                        except Exception: pass
                        browser, ctx, page = await _ensure_browser_and_page(pw, None, None, None)
                        await _browse_category_for_warmup(page, adapter)
                        wait_s = min(blocked_cd, 4 * 60.0) if engine_state == "BLOCKED" else random.uniform(60, 120)
                    else:
                        browser, ctx, page = await _ensure_browser_and_page(pw, browser, ctx, page)
                        wait_s = random.uniform(20, 45)
                    await asyncio.sleep(wait_s)
                    retry_cap = 1 if is_timeout else 0
                    if current_url_retries <= retry_cap:
                        logger.warning("[RETRY][异常] 同 URL 第 %d/%d 次重试", current_url_retries, retry_cap)
                        i -= 1
                        continue
                    else:
                        logger.error("[SKIP-URL] 异常重试 %d 次，跳过：%s", current_url_retries, product_url[-60:])
                        current_url_retries = 0
                        processed += 1
                        if engine_state == "BLOCKED":
                            _log_state_transition("HOT", reason="跳过异常URL B→H")

        finally:
            try:
                await page.close()
            except Exception:
                pass

    logger.info("========== 完成 ==========")
    logger.info("处理: %d  成功: %d  失败(跳过URL): %d", processed, success, fail)
    logger.info("[STATE统计] NORMAL=%d WARMING=%d HOT=%d BLOCKED=%d",
                engine_state_counts["NORMAL"], engine_state_counts["WARMING"],
                engine_state_counts["HOT"], engine_state_counts["BLOCKED"])


def main():
    parser = argparse.ArgumentParser(description="LV 全量抓取（基于完整 URL 列表）")
    parser.add_argument("--country", required=True, choices=["JP", "KR", "CN", "FR", "GB", "CH"])
    parser.add_argument("--limit", type=int, default=0, help="最多抓取多少个（0=不限制）")
    args = parser.parse_args()

    adapter = get_brand("LV", args.country)
    logger.info("启动: 品牌=%s  国家=%s  货币=%s", adapter.brand_id, adapter.country, adapter.currency)
    asyncio.run(crawl_from_urls(args.country, adapter, limit=args.limit))


if __name__ == "__main__":
    main()
