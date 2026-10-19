"""方案A v36：完整流程（输入→点主按钮），捕获所有请求，定位门店查询。

用法：venv/bin/python3.11 -m crawler.lv_diag_v36 <SKU|URL>
"""
import asyncio
import os
import sys

for v in ("http_proxy", "https_proxy", "HTTP_PROXY", "HTTPS_PROXY",
          "all_proxy", "ALL_PROXY"):
    os.environ.pop(v, None)

from playwright.async_api import async_playwright

REQS = []


async def main():
    url = sys.argv[1] if len(sys.argv) > 1 else "https://jp.louisvuitton.com/jpn-jp/products/-/M26763"
    async with async_playwright() as pw:
        browser = await pw.chromium.connect_over_cdp("http://127.0.0.1:9333")
        ctx = browser.contexts[0] if browser.contexts else await browser.new_context()
        page = await ctx.new_page()
        await page.set_viewport_size({"width": 1440, "height": 900})

        async def on_req(req):
            if req.resource_type in ("xhr", "fetch") and "doubleclick" not in req.url and "googletag" not in req.url:
                REQS.append({"m": req.method, "url": req.url[:200], "post": (req.post_data or "")[:300]})
        page.on("request", on_req)

        await page.goto(url, wait_until="domcontentloaded", timeout=45000)
        await asyncio.sleep(8)
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
        await asyncio.sleep(6)

        REQS.clear()
        inp = page.locator("#address-search-input")
        await inp.first.click(); await inp.first.fill("")
        for ch in "東京":
            await inp.first.type(ch, delay=150); await asyncio.sleep(0.3)
        await asyncio.sleep(3)

        # 点击所有可见的 lv-button（找主按钮"在庫状況を見る"）
        clicked = await page.evaluate("""() => {
            const btns = Array.from(document.querySelectorAll('.lv-locate-in-store button, .lv-store-geolocation button'));
            const vis = btns.filter(b=>{const r=b.getBoundingClientRect(); return r.width>0&&r.height>0;});
            const out = [];
            for (const b of vis) {
                const txt=(b.innerText||'').trim();
                if (txt) out.push(txt.substring(0,30));
            }
            return out;
        }""")
        print(f"弹窗内按钮: {clicked}")
        # 点击文本含'在庫状況を見る'的按钮
        await page.evaluate("""() => {
            const btns = Array.from(document.querySelectorAll('.lv-locate-in-store button, .lv-store-geolocation button'));
            for (const b of btns) {
                if ((b.innerText||'').includes('在庫状況を見る') && !b.disabled) { b.click(); return 'clicked'; }
            }
            return 'not_found_or_disabled';
        }""")
        await asyncio.sleep(8)

        print(f"\n=== 请求 ({len(REQS)}) ===")
        for r in REQS:
            print(f"  [{r['m']}] {r['url']}")
            if r["post"]: print(f"      BODY: {r['post']}")

        mtxt = await page.evaluate("""() => {
            const m=document.querySelector('.lv-store-geolocation , .lv-locate-in-store');
            return m? (m.innerText||'').substring(0,1200):'NO';
        }""")
        print(f"\n=== 弹窗文本 ===\n{mtxt}")
        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())