"""验证登录后库存查询能否返回门店数据（临时诊断脚本）"""
import asyncio, os
for _proxy_var in ("http_proxy", "https_proxy", "HTTP_PROXY", "HTTPS_PROXY",
                   "all_proxy", "ALL_PROXY"):
    os.environ.pop(_proxy_var, None)
from playwright.async_api import async_playwright

CDP = "http://127.0.0.1:9333"
URL = "https://jp.louisvuitton.com/jpn-jp/products/-/M26763"

async def main():
    async with async_playwright() as pw:
        browser = await pw.chromium.connect_over_cdp(CDP)
        ctx = browser.contexts[0] if browser.contexts else await browser.new_context()
        page = await ctx.new_page()

        print(f"导航: {URL}")
        resp = await page.goto(URL, wait_until="domcontentloaded", timeout=45000)
        print(f"HTTP: {resp.status if resp else 'None'} -> {page.url}")
        await asyncio.sleep(8)

        # 展开库存面板
        expanded = await page.evaluate(r"""() => {
            const panels = document.querySelectorAll('.lv-expandable-panel');
            for (const p of panels) {
                if ((p.innerText||'').includes('ストアの在庫状況を確認する')) {
                    p.scrollIntoView({block:'center'});
                    const btn = p.querySelector('button[aria-expanded]');
                    if (btn && btn.getAttribute('aria-expanded') !== 'true') btn.click();
                    return true;
                }
            }
            return false;
        }""")
        print("展开面板:", expanded)
        await asyncio.sleep(2)

        # 点击库存按钮（真实 Playwright click）
        btn = page.locator('.lv-product-locate-in-store__container')
        print("库存按钮数量:", await btn.count())
        if await btn.count() > 0:
            try:
                await btn.first.scroll_into_view_if_needed(timeout=5000)
                await btn.first.click(timeout=5000)
                print("已点击库存按钮")
            except Exception as e:
                print("点击异常:", str(e)[:100])
        await asyncio.sleep(5)

        # 禁用 backdrop
        await page.evaluate(r"""() => {
            const b = document.querySelectorAll('.lv-modal__backdrop, .lv-backdrop');
            for (const x of b) { x.style.pointerEvents='none'; x.style.opacity='0.3'; }
        }""")

        # 设置地理坐标并点击"現在地で検索"
        try:
            await ctx.grant_permissions(['geolocation'])
            await ctx.set_geolocation({"latitude": 35.6762, "longitude": 139.6503})
            print("已设置东京坐标")
        except Exception as e:
            print("设置坐标异常:", str(e)[:80])
        await asyncio.sleep(2)

        geo = page.locator('.lv-store-geolocation__get-button')
        print("地理按钮数量:", await geo.count())
        if await geo.count() > 0:
            dis = await geo.first.get_attribute('disabled')
            print("地理按钮disabled:", dis)
            if dis is None:
                try:
                    await geo.first.click(timeout=5000)
                    print("已点击現在地で検索")
                except Exception as e:
                    print("地理点击异常:", str(e)[:100])
        await asyncio.sleep(10)

        # 提取门店
        stores = await page.evaluate(r"""() => {
            const second = document.querySelector('.lv-locate-in-store__second-step-modal');
            if (!second) return {found:false, msg:'no second modal'};
            const cards = second.querySelectorAll('.lv-store-card-detailed');
            const out = [];
            for (const c of cards) {
                const nameEl = c.querySelector('.lv-store-card-detailed__name');
                const info = c.querySelector('.lv-store-card-detailed__info');
                const stock = c.querySelector('.lv-store-card-detailed__stock');
                out.push({
                    name: nameEl ? nameEl.innerText.trim() : '',
                    addr: info ? info.innerText.trim().replace(/\n/g,' ').substring(0,80) : '',
                    stock: stock ? stock.innerText.trim() : ''
                });
            }
            return {found:true, count:cards.length, stores:out.slice(0,5), no_result: !!second.querySelector('[class*="no-result"],[class*="empty"]')};
        }""")
        print("门店结果:", stores)

        await browser.close()

asyncio.run(main())