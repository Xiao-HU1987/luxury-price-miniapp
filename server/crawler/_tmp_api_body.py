"""检查第二步弹窗内容 + 捕获 stores/query API 响应体"""
import asyncio, os
for _proxy_var in ("http_proxy", "https_proxy", "HTTP_PROXY", "HTTPS_PROXY",
                   "all_proxy", "ALL_PROXY"):
    os.environ.pop(_proxy_var, None)
from playwright.async_api import async_playwright
import json

CDP = "http://127.0.0.1:9333"
CITY = "東京"

async def main():
    async with async_playwright() as pw:
        browser = await pw.chromium.connect_over_cdp(CDP)
        ctx = browser.contexts[0] if browser.contexts else await browser.new_context()
        page = None
        for p in ctx.pages:
            if "louisvuitton" in p.url and "products" in p.url:
                page = p
                break
        if not page:
            page = await ctx.new_page()
            await page.goto("https://jp.louisvuitton.com/jpn-jp/products/-/M26763", wait_until="domcontentloaded", timeout=45000)
            await asyncio.sleep(8)
        print("当前URL:", page.url)

        api_body = {}
        async def on_resp(resp):
            url = resp.url
            if "stores/query" in url:
                try:
                    body = await resp.text()
                    api_body["url"] = url[:120]
                    api_body["status"] = resp.status
                    api_body["body"] = body[:2000]
                except Exception as e:
                    api_body["err"] = str(e)
        page.on("response", on_resp)

        # 确保弹窗打开
        await page.evaluate(r"""() => {
            const el = document.querySelector('.lv-product-locate-in-store__container');
            if (el) el.click();
        }""")
        await asyncio.sleep(3)

        inp = page.locator('.lv-address-search-form__input')
        if await inp.count() > 0:
            await inp.first.click(timeout=3000)
            await asyncio.sleep(1)
            for ch in CITY:
                await inp.first.press_sequentially(ch, delay=250)
                await asyncio.sleep(0.5)
            await asyncio.sleep(5)  # 等补全

            # 如果有补全项则选择第一个
            picked = await page.evaluate(r"""() => {
                const modal = document.querySelector('.lv-locate-in-store__first-step-modal') || document.querySelector('.lv-modal__content');
                if (!modal) return null;
                const items = modal.querySelectorAll('[role="option"], [class*="suggestion"] li, [class*="item"]');
                for (const it of items) {
                    const r = it.getBoundingClientRect();
                    if (r.width>0 && r.height>0) { it.click(); return (it.innerText||'').trim().substring(0,60); }
                }
                return null;
            }""")
            print("选择的补全项:", picked)
            await asyncio.sleep(3)

            btn = page.locator('.lv-address-search-form__button')
            if await btn.count() > 0:
                await btn.first.click(timeout=5000)
                print("已点击搜索按钮")
            await asyncio.sleep(12)

        print("\n=== stores/query API 响应 ===")
        if api_body:
            print(f"status: {api_body.get('status')}")
            print(f"body前1500: {api_body.get('body','')[:1500]}")
        else:
            print("(未捕获到 stores/query 响应)")

        print("\n=== 第二步弹窗内容 ===")
        second = await page.evaluate(r"""() => {
            const s = document.querySelector('.lv-locate-in-store__second-step-modal');
            if (!s) return 'NO_SECOND';
            return {html_len: s.outerHTML.length, text: (s.innerText||'').substring(0,800)};
        }""")
        print(json.dumps(second, ensure_ascii=False, indent=2))

        await browser.close()

asyncio.run(main())