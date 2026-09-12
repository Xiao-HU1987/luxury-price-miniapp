"""用真实键盘逐字输入城市名，捕获所有网络请求"""
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

        # 捕获所有 louisvuitton 请求
        reqs = []
        async def on_resp(resp):
            url = resp.url
            if "louisvuitton.com" in url:
                reqs.append({"status": resp.status, "url": url[:180]})
        page.on("response", on_resp)

        # 确保弹窗打开
        await page.evaluate(r"""() => {
            const btn = document.querySelector('.lv-product-locate-in-store__container');
            if (btn) btn.click();
        }""")
        await asyncio.sleep(3)

        inp = page.locator('.lv-address-search-form__input')
        if await inp.count() > 0:
            await inp.first.click(timeout=3000)
            await asyncio.sleep(1)
            # 逐字输入
            for ch in CITY:
                await inp.first.press_sequentially(ch, delay=250)
                await asyncio.sleep(0.5)
            print(f"已逐字输入: {CITY}")
            await asyncio.sleep(6)

            # 检查补全下拉
            sugg = await page.evaluate(r"""() => {
                const modal = document.querySelector('.lv-locate-in-store__first-step-modal') || document.querySelector('.lv-modal__content');
                if (!modal) return {found:false};
                const items = modal.querySelectorAll('[role="option"], [class*="suggestion"] li, [class*="item"], [class*="result"] li');
                const out = {items: []};
                for (const it of items) {
                    const r = it.getBoundingClientRect();
                    if (r.width>0 && r.height>0) out.items.push((it.innerText||'').trim().substring(0,60));
                }
                return out;
            }""")
            print("补全下拉:", json.dumps(sugg, ensure_ascii=False))

            # 点击搜索按钮
            btn = page.locator('.lv-address-search-form__button')
            if await btn.count() > 0:
                await btn.first.click(timeout=5000)
                print("已点击搜索按钮")
            await asyncio.sleep(10)

        print("\n=== 所有 louisvuitton 网络请求 ===")
        for r in reqs:
            print(f"  [{r['status']}] {r['url']}")
        if not reqs:
            print("  (无请求)")

        # 检查弹窗状态
        state = await page.evaluate(r"""() => {
            const second = document.querySelector('.lv-locate-in-store__second-step-modal');
            const first = document.querySelector('.lv-locate-in-store__first-step-modal');
            const modal = document.querySelector('.lv-locate-in-store');
            const out = {second_exists: !!second};
            if (modal) out.modal_text = (modal.innerText||'').substring(0,600);
            const cards = document.querySelectorAll('[class*="store-card"], [class*="pos-card"]');
            out.store_cards = cards.length;
            return out;
        }""")
        print("\n=== AFTER ===")
        print(json.dumps(state, ensure_ascii=False, indent=2))

        await browser.close()

asyncio.run(main())