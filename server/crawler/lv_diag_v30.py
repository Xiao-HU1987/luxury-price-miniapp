"""方案A v30：捕获失败请求 + JS bundle，定位地址补全API端点。

用法：venv/bin/python3.11 -m crawler.lv_diag_v30 <SKU|URL>
"""
import asyncio
import os
import sys

for v in ("http_proxy", "https_proxy", "HTTP_PROXY", "HTTPS_PROXY",
          "all_proxy", "ALL_PROXY"):
    os.environ.pop(v, None)

from playwright.async_api import async_playwright

FAILED = []
ALL = []
JS_BUNDLES = []


async def setup(page):
    async def on_resp(resp):
        url = resp.url
        if "louisvuitton.com" in url or "api." in url:
            ALL.append({"url": url[:220], "status": resp.status})
            if url.endswith(".js") and "nuxt" in url:
                JS_BUNDLES.append(url)
    page.on("response", on_resp)

    async def on_fail(req):
        if "louisvuitton.com" in req.url or "api." in req.url:
            FAILED.append({"url": req.url[:220], "err": req.failure})
    page.on("requestfailed", on_fail)


async def open_modal(page):
    await page.evaluate("""(txt) => {
        const ps = document.querySelectorAll('.lv-expandable-panel');
        for (const p of ps) if ((p.innerText||'').includes(txt)) {
            const b = p.querySelector('button[aria-expanded]');
            if (b && b.getAttribute('aria-expanded') !== 'true') b.click();
        }
    }""", "ストアの在庫状況を確認する")
    await asyncio.sleep(2)
    await page.evaluate("""() => {
        const b = document.querySelector('.lv-product-locate-in-store__container');
        if (b) b.click();
    }""")
    await asyncio.sleep(5)


async def main():
    url = sys.argv[1] if len(sys.argv) > 1 else "https://jp.louisvuitton.com/jpn-jp/products/-/M26763"
    async with async_playwright() as pw:
        browser = await pw.chromium.connect_over_cdp("http://127.0.0.1:9333")
        ctx = browser.contexts[0] if browser.contexts else await browser.new_context()
        page = await ctx.new_page()
        await page.set_viewport_size({"width": 1440, "height": 900})
        await setup(page)

        print(f"=== 导航: {url} ===")
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=45000)
        except Exception as e:
            print(f"导航异常: {str(e).split(chr(10))[0]}")
        await asyncio.sleep(8)
        open_modal

        ALL.clear(); FAILED.clear()
        await open_modal(page)

        # 输入城市触发补全
        inp = page.locator("#address-search-input")
        await inp.first.click()
        await inp.first.fill("")
        for ch in "兵庫県":
            await inp.first.type(ch, delay=150)
            await asyncio.sleep(0.3)
        await asyncio.sleep(5)

        print(f"\n=== 失败请求 ({len(FAILED)} 条) ===")
        for f in FAILED:
            print(f"  [FAIL] {f['url']} | {f['err']}")

        print(f"\n=== 捕获请求 ({len(ALL)} 条) ===")
        for r in ALL:
            print(f"  [RESP {r['status']}] {r['url']}")

        print(f"\n=== JS bundle ({len(JS_BUNDLES)} 个) ===")
        for u in JS_BUNDLES:
            print(f"  {u}")

        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())