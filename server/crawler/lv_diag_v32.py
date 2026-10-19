"""方案A v32：捕获 availability API 的真实请求头，用于复刻 stores/query 调用。

用法：venv/bin/python3.11 -m crawler.lv_diag_v32 <SKU>
"""
import asyncio
import os
import sys

for v in ("http_proxy", "https_proxy", "HTTP_PROXY", "HTTPS_PROXY",
          "all_proxy", "ALL_PROXY"):
    os.environ.pop(v, None)

from playwright.async_api import async_playwright

CAPTURED = []


async def main():
    sku = sys.argv[1] if len(sys.argv) > 1 else "M26763"
    async with async_playwright() as pw:
        browser = await pw.chromium.connect_over_cdp("http://127.0.0.1:9333")
        ctx = browser.contexts[0] if browser.contexts else await browser.new_context()
        page = await ctx.new_page()

        async def on_req(req):
            if "stores/query" in req.url or ("availability" in req.url and "api.louisvuitton" in req.url):
                CAPTURED.append({
                    "method": req.method,
                    "url": req.url[:220],
                    "headers": dict(req.headers),
                    "post_data": req.post_data,
                })
        page.on("request", on_req)

        await page.goto(f"https://jp.louisvuitton.com/jpn-jp/products/-/{sku}",
                        wait_until="domcontentloaded", timeout=45000)
        await asyncio.sleep(6)

        print(f"=== 捕获 {len(CAPTURED)} 个请求 ===")
        for c in CAPTURED:
            print(f"\nMETHOD: {c['method']}")
            print(f"URL: {c['url']}")
            print("HEADERS:")
            for k, v in c["headers"].items():
                print(f"  {k}: {v[:120]}")
            if c["post_data"]:
                print(f"BODY: {c['post_data'][:500]}")
        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())