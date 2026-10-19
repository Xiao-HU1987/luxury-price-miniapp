"""完整捕获 stores/query API 响应，测试多个城市，确认库存状态字段"""
import asyncio, os
for _proxy_var in ("http_proxy", "https_proxy", "HTTP_PROXY", "HTTPS_PROXY",
                   "all_proxy", "ALL_PROXY"):
    os.environ.pop(_proxy_var, None)
from playwright.async_api import async_playwright
import json

CDP = "http://127.0.0.1:9333"
CITIES = ["東京都", "大阪府"]

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
            if "stores/query" in resp.url:
                try:
                    api_body["status"] = resp.status
                    api_body["body"] = await resp.text()
                except Exception as e:
                    api_body["err"] = str(e)
        page.on("response", on_resp)

        all_results = {}

        for CITY in CITIES:
            print(f"\n{'='*50}\n搜索: {CITY}\n{'='*50}")
            # 重新加载页面，确保弹窗状态是全新的
            await page.goto("https://jp.louisvuitton.com/jpn-jp/products/-/M26763", wait_until="domcontentloaded", timeout=45000)
            await asyncio.sleep(8)

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

            # 点击库存按钮打开弹窗
            await page.evaluate(r"""() => {
                const btn = document.querySelector('.lv-product-locate-in-store__container');
                if (btn) btn.click();
            }""")
            await asyncio.sleep(4)
            await page.evaluate(r"""() => {
                document.querySelectorAll('.lv-modal__backdrop, .lv-backdrop').forEach(b => { b.style.pointerEvents='none'; b.style.opacity='0'; });
            }""")

            api_body.clear()
            inp = page.locator('.lv-address-search-form__input')
            if await inp.count() > 0:
                await inp.first.click(timeout=3000)
                await asyncio.sleep(0.5)
                await inp.first.press_sequentially(CITY, delay=200)
                await asyncio.sleep(6)
                btn = page.locator('.lv-address-search-form__button')
                if await btn.count() > 0:
                    dis = await btn.first.get_attribute('disabled')
                    if dis is None:
                        await btn.first.click(timeout=5000)
            await asyncio.sleep(10)

            if api_body.get("body"):
                try:
                    data = json.loads(api_body["body"])
                    hits = data.get("hits", [])
                    print(f"nbHits: {data.get('nbHits')}, 返回门店数: {len(hits)}")
                    for h in hits:
                        name = h.get("name", "")
                        addr = h.get("address", {})
                        stock = None
                        for prop in h.get("additionalProperty", []):
                            if prop.get("name") == "stockAvailability":
                                stock = prop.get("value")
                        addr_str = f"{addr.get('state','')} {addr.get('addressLocality','')} {addr.get('streetAddress','')}"
                        identifier = h.get("identifier", "")
                        print(f"  - {name} [{identifier}] stock={stock}")
                        print(f"      地址: {addr_str}")
                        all_results[name] = {"stock": stock, "addr": addr_str, "id": identifier}
                except Exception as e:
                    print("解析失败:", str(e)[:100])
            else:
                print("(未捕获到 API 响应)")

        print(f"\n\n=== 汇总 ({len(all_results)} 家门店) ===")
        for name, info in all_results.items():
            print(f"  {name}: stock={info['stock']} | {info['addr']}")

        await browser.close()

asyncio.run(main())