"""用 page.route() 拦截 stores/query 请求，捕获完整请求体"""
import asyncio, os
for _proxy_var in ("http_proxy", "https_proxy", "HTTP_PROXY", "HTTPS_PROXY",
                   "all_proxy", "ALL_PROXY"):
    os.environ.pop(_proxy_var, None)
from playwright.async_api import async_playwright, Route
import json

CDP = "http://127.0.0.1:9333"

async def main():
    async with async_playwright() as pw:
        browser = await pw.chromium.connect_over_cdp(CDP)
        ctx = browser.contexts[0] if browser.contexts else await browser.new_context()
        page = await ctx.new_page()

        captured = {}

        async def handle_route(route: Route):
            url = route.request.url
            if "stores/query" in url:
                body = route.request.post_data
                headers = dict(route.request.headers)
                captured["url"] = url
                captured["method"] = route.request.method
                captured["body"] = body
                captured["headers"] = {k: v for k, v in headers.items() if k.lower() not in ('cookie', 'authorization')}
                print(f"=== 拦截到 stores/query ===")
                print(f"URL: {url[:150]}")
                print(f"Method: {route.request.method}")
                print(f"Headers: {json.dumps(captured['headers'], ensure_ascii=False)}")
                print(f"Body: {body}")
            await route.continue_()

        await page.route("**/stores/query", handle_route)

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

        # 输入并搜索
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

        if not captured:
            print("未拦截到 stores/query 请求")

        await browser.close()

asyncio.run(main())