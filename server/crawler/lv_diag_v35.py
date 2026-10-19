"""方案A v35：打开门店弹窗后检查加载的地图服务(百度/Google)及地址补全API。

用法：venv/bin/python3.11 -m crawler.lv_diag_v35 <SKU|URL>
"""
import asyncio
import os
import sys

for v in ("http_proxy", "https_proxy", "HTTP_PROXY", "HTTPS_PROXY",
          "all_proxy", "ALL_PROXY"):
    os.environ.pop(v, None)

from playwright.async_api import async_playwright

SCRIPTS = []
FAILED = []


async def main():
    url = sys.argv[1] if len(sys.argv) > 1 else "https://jp.louisvuitton.com/jpn-jp/products/-/M26763"
    async with async_playwright() as pw:
        browser = await pw.chromium.connect_over_cdp("http://127.0.0.1:9333")
        ctx = browser.contexts[0] if browser.contexts else await browser.new_context()
        page = await ctx.new_page()

        async def on_req(req):
            if any(k in req.url.lower() for k in ("map.", "geocode", "places", "tile", "baidu", "maps/api", "autocomplete", "maptiler", "mapbox")):
                SCRIPTS.append({"url": req.url[:160], "method": req.method})
        page.on("request", on_req)
        async def on_fail(req):
            if any(k in req.url.lower() for k in ("map.", "geocode", "places", "tile", "baidu", "maps/api", "autocomplete", "maptiler", "mapbox")):
                FAILED.append({"url": req.url[:160], "err": req.failure})
        page.on("requestfailed", on_fail)

        await page.goto(url, wait_until="domcontentloaded", timeout=45000)
        await asyncio.sleep(8)

        # 打开弹窗
        await page.evaluate("""(txt) => {
            for (const p of document.querySelectorAll('.lv-expandable-panel'))
                if ((p.innerText||'').includes(txt)) {
                    const b=p.querySelector('button[aria-expanded]');
                    if(b&&b.getAttribute('aria-expanded')!=='true') b.click();
                }
        }""", "ストアの在庫状況を確認する")
        await asyncio.sleep(2)
        await page.evaluate("""() => {
            const b=document.querySelector('.lv-product-locate-in-store__container');
            if(b) b.click();
        }""")
        await asyncio.sleep(8)

        SCRIPTS.clear(); FAILED.clear()
        # 输入触发补全
        inp = page.locator("#address-search-input")
        await inp.first.click(); await inp.first.fill("")
        for ch in "東京":
            await inp.first.type(ch, delay=150); await asyncio.sleep(0.3)
        await asyncio.sleep(6)

        print(f"=== 地图/补全请求 ({len(SCRIPTS)}) ===")
        for s in SCRIPTS:
            print(f"  [{s['method']}] {s['url']}")
        print(f"=== 失败请求 ({len(FAILED)}) ===")
        for f in FAILED:
            print(f"  [FAIL] {f['url']} | {f['err']}")
        # 检查地图脚本
        ms = await page.evaluate("""() => {
            return Array.from(document.scripts)
                .filter(s=>/baidu|map\.|maps|geocode|maptiler|mapbox/i.test(s.src))
                .map(s=>s.src.slice(0,120));
        }""")
        print(f"=== 已加载地图脚本 ({len(ms)}) ===")
        for s in ms: print("  ", s)
        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())