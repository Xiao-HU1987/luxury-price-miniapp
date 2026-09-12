"""通过 monkey-patch fetch 捕获 stores/query 请求体"""
import asyncio, os
for _proxy_var in ("http_proxy", "https_proxy", "HTTP_PROXY", "HTTPS_PROXY",
                   "all_proxy", "ALL_PROXY"):
    os.environ.pop(_proxy_var, None)
from playwright.async_api import async_playwright
import json

CDP = "http://127.0.0.1:9333"

async def main():
    async with async_playwright() as pw:
        browser = await pw.chromium.connect_over_cdp(CDP)
        ctx = browser.contexts[0] if browser.contexts else await browser.new_context()
        page = await ctx.new_page()

        await page.goto("https://jp.louisvuitton.com/jpn-jp/products/-/M26763", wait_until="domcontentloaded", timeout=45000)
        await asyncio.sleep(5)

        # 注入 monkey-patch（页面加载后，交互前）
        await page.evaluate("""
            window.__LV_REQUESTS = [];
            const origFetch = window.fetch;
            window.fetch = function(input, init) {
                let url = '';
                try { url = typeof input === 'string' ? input : (input && input.url || ''); } catch(e) {}
                if (url && url.includes('stores/query')) {
                    try {
                        window.__LV_REQUESTS.push({url: url, method: (init||{}).method || 'GET', body: (init||{}).body || ''});
                    } catch(e) {}
                }
                return origFetch.call(this, input, init);
            };
        """)
        await asyncio.sleep(3)

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

        # 获取捕获的请求
        reqs = await page.evaluate("() => window.__LV_REQUESTS")
        print(f"捕获到 {len(reqs)} 条 stores/query 请求:")
        for i, r in enumerate(reqs):
            print(f"\n--- 请求 {i+1} ---")
            print(f"URL: {r['url'][:150]}")
            print(f"Method: {r['method']}")
            print(f"Body: {r['body']}")

        if not reqs:
            print("(未捕获到请求)")

        await browser.close()

asyncio.run(main())