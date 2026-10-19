"""点击現在地で検索后，检查第一步弹窗内是否就地渲染门店列表"""
import asyncio, os
for _proxy_var in ("http_proxy", "https_proxy", "HTTP_PROXY", "HTTPS_PROXY",
                   "all_proxy", "ALL_PROXY"):
    os.environ.pop(_proxy_var, None)
from playwright.async_api import async_playwright

CDP = "http://127.0.0.1:9333"

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
        import json
        requests_log = []
        async def on_resp(resp):
            url = resp.url
            if "louisvuitton" in url and ("store" in url or "inventory" in url or "availability" in url or "geo" in url or "point-of-sale" in url or "locate" in url):
                requests_log.append({"status": resp.status, "url": url[:160]})
        page.on("response", on_resp)

        # 确保弹窗打开
        opened = await page.evaluate(r"""() => {
            const btn = document.querySelector('.lv-product-locate-in-store__container');
            if (btn) { btn.click(); return true; }
            return false;
        }""")
        print("弹窗打开:", opened)
        await asyncio.sleep(3)

        # 检查当前弹窗状态
        before = await page.evaluate(r"""() => {
            const first = document.querySelector('.lv-locate-in-store__first-step-modal');
            return first ? (first.innerText||'').substring(0,300) : 'NO_FIRST';
        }""")
        print("打开后第一步文本:", before[:200])

        # 设置地理坐标
        try:
            await ctx.grant_permissions(['geolocation'])
            await ctx.set_geolocation({"latitude": 35.6762, "longitude": 139.6503})
            print("已设置东京坐标")
        except Exception as e:
            print("坐标异常:", str(e)[:80])
        await asyncio.sleep(2)

        # 点击現在地で検索
        geo = page.locator('.lv-store-geolocation__get-button')
        if await geo.count() > 0:
            await geo.first.click(timeout=5000)
            print("已点击現在地で検索")
        await asyncio.sleep(12)

        print("\n=== 网络请求 ===")
        for r in requests_log:
            print(f"  [{r['status']}] {r['url']}")

        print("\n=== AFTER 弹窗状态 ===")
        after = await page.evaluate(r"""() => {
            const first = document.querySelector('.lv-locate-in-store__first-step-modal');
            const second = document.querySelector('.lv-locate-in-store__second-step-modal');
            const modal = document.querySelector('.lv-locate-in-store');
            const out = {second: !!second};
            if (modal) out.modal_text = (modal.innerText||'').substring(0,500);
            if (first) out.first_text = (first.innerText||'').substring(0,300);
            // 所有含store的卡片
            const cards = document.querySelectorAll('[class*="store-card"], [class*="pos-card"], [class*="store-item"]');
            out.store_cards = cards.length;
            if (cards.length > 0) {
                out.first_card = (cards[0].innerText||'').substring(0,200);
            }
            return out;
        }""")
        print(json.dumps(after, ensure_ascii=False, indent=2))

        await browser.close()

asyncio.run(main())