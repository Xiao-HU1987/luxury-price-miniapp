"""通过 CDP Network 域直接捕获 stores/query 请求体"""
import asyncio, os
for _proxy_var in ("http_proxy", "https_proxy", "HTTP_PROXY", "HTTPS_PROXY",
                   "all_proxy", "ALL_PROXY"):
    os.environ.pop(_proxy_var, None)
from playwright.async_api import async_playwright
import json

CDP_ENDPOINT = "http://127.0.0.1:9333"

async def main():
    async with async_playwright() as pw:
        browser = await pw.chromium.connect_over_cdp(CDP_ENDPOINT)
        ctx = browser.contexts[0] if browser.contexts else await browser.new_context()
        page = await ctx.new_page()

        # 通过 CDP session 启用 Network 域
        cdp = await ctx.new_cdp_session(page)
        await cdp.send("Network.enable")

        captured = []

        def on_request_received(params):
            req = params.get("request", {})
            url = req.get("url", "")
            if "stores/query" in url:
                post_data = req.get("postData", "")
                captured.append({"url": url, "method": req.get("method", ""), "body": post_data})

        cdp.on("Network.requestWillBeSent", on_request_received)

        await page.goto("https://jp.louisvuitton.com/jpn-jp/products/-/M26763", wait_until="domcontentloaded", timeout=45000)
        await asyncio.sleep(8)

        # 展开面板
        await page.evaluate(r"""() => {
            const panels = document.querySelectorAll('.lv-expandable-panel');
            for (const p of panels) {
                if ((p.innerText||'').includes('ストアの在庫状況を確認する')) {
                    p.scrollIntoView({block:'center'});
                    const btn = p.querySelector('button[aria-expanded]');
                    if (btn && btn.getAttribute('aria-expanded') !== 'true') btn.click();
                    break;
                }
            }
        }""")
        await asyncio.sleep(2)

        # 点击库存按钮
        await page.evaluate(r"""() => {
            const btn = document.querySelector('.lv-product-locate-in-store__container');
            if (btn) btn.click();
        }""")
        await asyncio.sleep(4)
        await page.evaluate(r"""() => {
            document.querySelectorAll('.lv-modal__backdrop, .lv-backdrop').forEach(b => { b.style.pointerEvents='none'; b.style.opacity='0'; });
        }""")

        # 输入"東京"并搜索
        inp = page.locator('.lv-address-search-form__input')
        if await inp.count() > 0:
            await inp.first.click(timeout=3000)
            await asyncio.sleep(0.5)
            await inp.first.press_sequentially("東京", delay=200)
            await asyncio.sleep(6)
            btn = page.locator('.lv-address-search-form__button')
            if await btn.count() > 0:
                if await btn.first.get_attribute('disabled') is None:
                    await btn.first.click(timeout=5000)
            await asyncio.sleep(10)

        print(f"捕获到 {len(captured)} 条 stores/query 请求:")
        for i, r in enumerate(captured):
            print(f"\n--- 请求 {i+1} ---")
            print(f"URL: {r['url'][:150]}")
            print(f"Method: {r['method']}")
            print(f"Body: {r['body']}")

        if not captured:
            print("(未捕获)")

        await browser.close()

asyncio.run(main())