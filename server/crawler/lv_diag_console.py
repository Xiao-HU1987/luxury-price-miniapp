"""捕获页面 console 错误 / pageerror / 未捕获异常，排查前端 JS 报错。

用法：env -u HTTP_PROXY -u HTTPS_PROXY -u http_proxy -u https_proxy -u ALL_PROXY -u all_proxy \
        venv/bin/python3.11 -m crawler.lv_diag_console "https://jp.louisvuitton.com/jpn-jp/products/-/M29195"
"""
import asyncio
import os
import sys

for v in ("http_proxy", "https_proxy", "HTTP_PROXY", "HTTPS_PROXY",
          "all_proxy", "ALL_PROXY"):
    os.environ.pop(v, None)

from playwright.async_api import async_playwright

PANEL_TEXT = "ストアの在庫状況を確認する"
ERRS = []


async def main():
    url = sys.argv[1] if len(sys.argv) > 1 else "https://jp.louisvuitton.com/jpn-jp/products/-/M29195"
    async with async_playwright() as pw:
        browser = await pw.chromium.connect_over_cdp("http://127.0.0.1:9333")
        ctx = browser.contexts[0] if browser.contexts else await browser.new_context()
        page = await ctx.new_page()

        async def on_console(msg):
            if msg.type in ("error", "warning"):
                ERRS.append(("console", msg.type, msg.text[:300]))
        async def on_pageerror(e):
            ERRS.append(("pageerror", "error", str(e)[:300]))
        page.on("console", on_console)
        page.on("pageerror", on_pageerror)

        print(f"=== 导航: {url} ===")
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=45000)
        except Exception as e:
            print(f"导航异常: {str(e).splitlines()[0]}")
        await asyncio.sleep(8)
        print(f"导航后 console/pageerror: {len(ERRS)}")

        # 打开弹窗
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
        print(f"打开弹窗后 console/pageerror: {len(ERRS)}")

        # 输入地址 + 点击
        inp = page.locator("#address-search-input")
        if await inp.count() > 0:
            await inp.click(timeout=3000)
            await asyncio.sleep(0.3)
            await inp.type("東京", delay=200)
            await asyncio.sleep(3)
        see = page.locator(".lv-loading-button:has-text('在庫状況を見る')")
        if await see.count() > 0:
            await see.first.click(timeout=5000)
            await asyncio.sleep(6)
        print(f"输入+点击后 console/pageerror: {len(ERRS)}")

        print("\n=== 所有错误 ===")
        for kind, lvl, text in ERRS[:40]:
            print(f"  [{kind}/{lvl}] {text}")
        if not ERRS:
            print("  (无错误)")
        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())