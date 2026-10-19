"""每个城市重新加载页面，确保输入框干净，验证库存数据采集"""
import asyncio, os
for _proxy_var in ("http_proxy", "https_proxy", "HTTP_PROXY", "HTTPS_PROXY",
                   "all_proxy", "ALL_PROXY"):
    os.environ.pop(_proxy_var, None)
from playwright.async_api import async_playwright
import json

CDP = "http://127.0.0.1:9333"
SKU = "M26763"
CITIES = ["東京都", "大阪府", "京都府", "愛知県", "福岡県", "北海道"]

async def main():
    async with async_playwright() as pw:
        browser = await pw.chromium.connect_over_cdp(CDP)
        ctx = browser.contexts[0] if browser.contexts else await browser.new_context()
        page = await ctx.new_page()

        all_results = {}

        for CITY in CITIES:
            print(f"\n{'='*50}")
            print(f"搜索: {CITY}")
            print(f"{'='*50}")

            # 重新加载页面（确保输入框干净）
            await page.goto(f"https://jp.louisvuitton.com/jpn-jp/products/-/{SKU}", wait_until="domcontentloaded", timeout=45000)
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

            # 点击库存按钮
            await page.evaluate(r"""() => {
                const btn = document.querySelector('.lv-product-locate-in-store__container');
                if (btn) btn.click();
            }""")
            await asyncio.sleep(4)
            await page.evaluate(r"""() => {
                document.querySelectorAll('.lv-modal__backdrop, .lv-backdrop').forEach(b => { b.style.pointerEvents='none'; b.style.opacity='0'; });
            }""")

            # 输入城市名
            inp = page.locator('.lv-address-search-form__input')
            if await inp.count() > 0:
                await inp.first.click(timeout=3000)
                await asyncio.sleep(0.5)
                await inp.first.press_sequentially(CITY, delay=200)
                await asyncio.sleep(6)

                # 点击搜索按钮
                btn = page.locator('.lv-address-search-form__button')
                if await btn.count() > 0:
                    if await btn.first.get_attribute('disabled') is None:
                        await btn.first.click(timeout=5000)
                        print("已点击搜索")

                # 等待第二步弹窗出现
                await asyncio.sleep(10)

            # 提取门店数据
            stores = await page.evaluate(r"""() => {
                const second = document.querySelector('.lv-locate-in-store__second-step-modal');
                if (!second) return {found: false, msg: 'no_second_modal'};
                const cards = second.querySelectorAll('.lv-store-card-detailed');
                const results = [];
                for (const c of cards) {
                    const nameEl = c.querySelector('.lv-store-card-detailed__name');
                    const info = c.querySelector('.lv-store-card-detailed__info');
                    const stock = c.querySelector('.lv-store-card-detailed__stock');
                    const link = c.querySelector('a[href*="point-of-sale"]');
                    results.push({
                        name: nameEl ? nameEl.innerText.trim() : '',
                        addr: info ? info.innerText.trim().replace(/\n/g,' ') : '',
                        stock: stock ? stock.innerText.trim() : '',
                        store_id: link ? (link.getAttribute('href')||'').split('japan/')[1]?.split('?')[0] || '' : ''
                    });
                }
                return {found: true, count: cards.length, stores: results};
            }""")

            print(f"门店数: {stores.get('count', 0)}")
            for s in stores.get("stores", []):
                has_stock = "在庫あり" in s["stock"] or "在庫僅少" in s["stock"]
                key = s["store_id"] or s["name"]
                if key and key not in all_results:
                    all_results[key] = {**s, "has_stock": has_stock, "city": CITY}
                print(f"  {'✓' if has_stock else '✗'} {s['name']} [{s['store_id']}] | {s['stock']} | {s['addr'][:60]}")

        print(f"\n\n{'='*50}")
        print(f"汇总: {len(all_results)} 家门店")
        print(f"{'='*50}")
        in_stock = [v for v in all_results.values() if v["has_stock"]]
        out_stock = [v for v in all_results.values() if not v["has_stock"]]
        print(f"有库存: {len(in_stock)} 家")
        for s in in_stock:
            print(f"  ✓ {s['name']} [{s['store_id']}] | {s['addr'][:60]}")
        print(f"无库存: {len(out_stock)} 家")
        for s in out_stock[:5]:
            print(f"  ✗ {s['name']} [{s['store_id']}] | {s['addr'][:60]}")
        if len(out_stock) > 5:
            print(f"  ... 及其他 {len(out_stock) - 5} 家")

        await browser.close()

asyncio.run(main())