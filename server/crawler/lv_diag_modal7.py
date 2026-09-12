"""关键测试：输入地址后按钮启用，点击'在庫状況を見る'捕获所有域名请求。

用法：cd server && env -u HTTP_PROXY -u HTTPS_PROXY -u http_proxy -u https_proxy -u ALL_PROXY -u all_proxy \
        venv/bin/python3.11 -m crawler.lv_diag_modal7 "https://jp.louisvuitton.com/jpn-jp/products/-/M29195"
"""
import asyncio
import os
import sys

for v in ("http_proxy", "https_proxy", "HTTP_PROXY", "HTTPS_PROXY",
          "all_proxy", "ALL_PROXY"):
    os.environ.pop(v, None)

from playwright.async_api import async_playwright

PANEL_TEXT = "ストアの在庫状況を確認する"
REQUESTS = []


async def catch_all(page):
    """捕获所有发出的请求（含被打断的），不依赖响应。"""
    async def on_req(req):
        rtype = req.resource_type
        if rtype in ("xhr", "fetch"):
            REQUESTS.append(("REQ", req.method, req.url[:200], ""))
    async def on_resp(resp):
        rtype = resp.request.resource_type
        if rtype not in ("xhr", "fetch"):
            return
        try:
            ct = resp.headers.get("content-type", "")
        except Exception:
            ct = ""
        body = ""
        if "json" in ct:
            try:
                body = (await resp.text())[:1500]
            except Exception:
                body = "<unreadable>"
        REQUESTS.append(("RESP", resp.status, resp.url[:200], body))
    page.on("request", on_req)
    page.on("response", on_resp)


async def open_modal(page):
    panel = page.locator(f".lv-expandable-panel:has-text('{PANEL_TEXT}')")
    if await panel.count() > 0:
        try:
            await panel.first.scroll_into_view_if_needed(timeout=8000)
            await asyncio.sleep(1)
        except Exception:
            pass
        eb = panel.first.locator("button[aria-expanded]")
        if await eb.count() > 0 and await eb.first.get_attribute("aria-expanded") != "true":
            await eb.first.click(timeout=5000)
        await asyncio.sleep(2)
    lb = page.locator(".lv-product-locate-in-store__container")
    if await lb.count() > 0:
        try:
            await lb.first.scroll_into_view_if_needed(timeout=8000)
            await asyncio.sleep(0.8)
            await lb.first.click(timeout=5000)
        except Exception as e:
            print(f"打开弹窗失败: {e}")
    await asyncio.sleep(5)


def btn_disabled(page):
    return page.evaluate("""
        () => {
            const btns = document.querySelectorAll('.lv-loading-button');
            for (const b of btns) if ((b.innerText||'').includes('在庫状況を見る')) return b.disabled;
            return 'NO_BTN';
        }
    """)


async def main():
    url = sys.argv[1] if len(sys.argv) > 1 else "https://jp.louisvuitton.com/jpn-jp/products/-/M29195"
    REQUESTS.clear()
    async with async_playwright() as pw:
        browser = await pw.chromium.connect_over_cdp("http://127.0.0.1:9333")
        ctx = browser.contexts[0] if browser.contexts else await browser.new_context()
        page = await ctx.new_page()
        await page.set_viewport_size({"width": 1440, "height": 900})
        await catch_all(page)

        print(f"=== 导航: {url} ===")
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=45000)
        except Exception as e:
            print(f"导航异常: {str(e).splitlines()[0]}")
        await asyncio.sleep(8)
        REQUESTS.clear()
        await open_modal(page)

        # 输入地址（不选尺寸）
        inp = page.locator("#address-search-input")
        await inp.click(timeout=3000)
        await asyncio.sleep(0.3)
        await inp.type("東京", delay=200)
        await asyncio.sleep(1)
        val = await inp.input_value()
        print(f"输入后 input.value={val!r}")
        print(f"输入'東京'后 按钮disabled={await btn_disabled(page)}")

        # 按 Enter 触发搜索
        REQUESTS.clear()
        print("\n=== 按 Enter ===")
        await inp.press("Enter")
        await asyncio.sleep(8)
        print(f"--- 点击后所有请求 ({len(REQUESTS)}) ---")
        for t, a, u, b in REQUESTS:
            print(f"  [{t}] {a} {u}")
            if b:
                print(f"      BODY: {b[:300]}")

        # dump 弹窗当前状态
        state = await page.evaluate("""
            () => {
                const m = document.querySelector('.-sidepanel.lv-locate-in-store');
                if (!m) return 'NO_MODAL';
                const text = (m.innerText||'').substring(0, 500);
                const cards = m.querySelectorAll('[class*="store-card"], [class*="pos"], [class*="store-item"]');
                const visible = [];
                for (const c of cards) { const r=c.getBoundingClientRect(); if(r.width>0&&r.height>0) visible.push((c.innerText||'').substring(0,120)); }
                return {text, cards: visible};
            }
        """)
        print(f"\n弹窗文本: {state['text'] if isinstance(state,dict) else state}")
        if isinstance(state, dict):
            print(f"可见门店卡片: {len(state['cards'])}")
            for c in state['cards'][:8]:
                print(f"  - {c}")
        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())