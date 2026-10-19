"""用地址搜索框输入城市名，观察补全和搜索结果"""
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

        # 网络监听
        reqs = []
        async def on_req(req):
            url = req.url
            if "louisvuitton" in url and ("store" in url or "inventory" in url or "address" in url or "suggest" in url or "search" in url or "pos" in url or "locate" in url or "geo" in url):
                reqs.append({"method": req.method, "url": url[:160]})
        async def on_resp(resp):
            url = resp.url
            if "louisvuitton" in url and ("store" in url or "inventory" in url or "address" in url or "suggest" in url or "search" in url or "pos" in url or "locate" in url or "geo" in url):
                reqs.append({"status": resp.status, "url": url[:160]})
        page.on("request", on_req)
        page.on("response", on_resp)

        # 确保弹窗打开
        await page.evaluate(r"""() => {
            const btn = document.querySelector('.lv-product-locate-in-store__container');
            if (btn) btn.click();
        }""")
        await asyncio.sleep(3)

        # 输入城市名
        inp = page.locator('.lv-address-search-form__input')
        print("输入框数量:", await inp.count())
        if await inp.count() > 0:
            await inp.first.click(timeout=3000)
            await inp.first.fill(CITY)
            print(f"已输入: {CITY}")
            await asyncio.sleep(6)  # 等待补全

            # 检查补全下拉
            sugg = await page.evaluate(r"""() => {
                const modal = document.querySelector('.lv-locate-in-store__first-step-modal') || document.querySelector('.lv-modal__content');
                if (!modal) return {found:false};
                const lists = modal.querySelectorAll('[class*="suggestion"], [class*="suggestions"], [role="listbox"], [class*="autocomplete"]');
                const out = {lists: lists.length, items: []};
                const items = modal.querySelectorAll('[role="option"], [class*="suggestion"] li, [class*="result"] li');
                for (const it of items) {
                    const r = it.getBoundingClientRect();
                    if (r.width>0 && r.height>0) out.items.push((it.innerText||'').trim().substring(0,60));
                }
                return out;
            }""")
            print("补全下拉:", json.dumps(sugg, ensure_ascii=False))

            # 检查搜索按钮状态
            btn = page.locator('.lv-address-search-form__button')
            if await btn.count() > 0:
                dis = await btn.first.get_attribute('disabled')
                print("搜索按钮disabled:", dis)

        await asyncio.sleep(3)
        print("\n=== 网络请求 ===")
        for r in reqs:
            print(f"  {r.get('method','')} [{r.get('status','')}] {r['url']}")
        if not reqs:
            print("  (无请求)")

        await browser.close()

asyncio.run(main())