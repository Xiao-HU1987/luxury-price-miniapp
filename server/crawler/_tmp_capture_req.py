"""捕获真实弹窗搜索触发的 API 请求体"""
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
        await asyncio.sleep(8)
        print("页面加载完成")

        # 捕获所有 stores/query 请求
        requests_captured = []
        async def on_request(req):
            if "stores/query" in req.url:
                try:
                    body = req.post_data
                    requests_captured.append({"url": req.url[:150], "method": req.method, "body": body, "headers": dict(req.headers)})
                except Exception as e:
                    requests_captured.append({"err": str(e)})
        page.on("request", on_request)

        async def on_response(resp):
            if "stores/query" in resp.url:
                try:
                    body = await resp.text()
                    requests_captured.append({"response_status": resp.status, "response_body": body[:2000]})
                except Exception as e:
                    requests_captured.append({"resp_err": str(e)})
        page.on("response", on_response)

        # 展开库存面板
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
            await inp.first.press_sequentially("東京都", delay=200)
            await asyncio.sleep(6)
            btn = page.locator('.lv-address-search-form__button')
            if await btn.count() > 0:
                dis = await btn.first.get_attribute('disabled')
                print("搜索按钮disabled:", dis)
                if dis is None:
                    await btn.first.click(timeout=5000)
            await asyncio.sleep(10)

        print(f"\n=== 捕获到 {len(requests_captured)} 条记录 ===")
        for i, r in enumerate(requests_captured):
            print(f"\n--- 记录 {i+1} ---")
            print(json.dumps(r, ensure_ascii=False, indent=2)[:1500])

        await browser.close()

asyncio.run(main())