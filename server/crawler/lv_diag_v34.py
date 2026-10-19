"""方案A v34：从浏览器会话测试带 /lvcom/ 前缀的 stores/query，加 locale 头。

用法：venv/bin/python3.11 -m crawler.lv_diag_v34 <SKU>
"""
import asyncio
import os
import sys
import uuid

for v in ("http_proxy", "https_proxy", "HTTP_PROXY", "HTTPS_PROXY",
          "all_proxy", "ALL_PROXY"):
    os.environ.pop(v, None)

from playwright.async_api import async_playwright


async def main():
    sku = sys.argv[1] if len(sys.argv) > 1 else "M26763"
    async with async_playwright() as pw:
        browser = await pw.chromium.connect_over_cdp("http://127.0.0.1:9333")
        ctx = browser.contexts[0] if browser.contexts else await browser.new_context()
        page = await ctx.new_page()

        await page.goto(f"https://jp.louisvuitton.com/jpn-jp/products/-/{sku}",
                        wait_until="domcontentloaded", timeout=45000)
        await asyncio.sleep(4)

        base = {
            "Content-Type": "application/json", "Accept": "application/json",
            "client_id": "607e3016889f431fb8020693311016c9",
            "client_secret": "60bbcdcD722D411B88cBb72C8246a22F",
            "checkout-channel": "WEB",
            "x-device-id": str(uuid.uuid4()), "x-correlation-id": uuid.uuid4().hex[:16],
            "Referer": f"https://jp.louisvuitton.com/jpn-jp/products/-/{sku}",
        }
        localed = dict(base, **{
            "x-locale": "jpn-jp", "Accept-Language": "ja-JP,ja;q=0.9",
            "x-site": "jpn-jp",
        })
        body = {"country": "JP", "countryUrl": "jpn-jp", "skuId": sku,
                "query": "東京", "pageType": "product", "limit": 50,
                "useGeoCode": False, "province": "", "storeLang": "ja-JP",
                "flagShip": "false", "clickAndCollect": "false"}

        urls = [
            "https://jp.louisvuitton.com/lvcom/jpn-jp/stores/query",
            "https://jp.louisvuitton.com/jpn-jp/stores/query",
            "https://org-live.louisvuitton.com/lvcom/jpn-jp/stores/query",
        ]
        for u in urls:
            for h_name, h in (("base", base), ("localed", localed)):
                result = await page.evaluate(
                    r"""async ([url, headers, body]) => {
                        try {
                            const r = await fetch(url, {method:'POST', headers, body: JSON.stringify(body)});
                            const t = await r.text();
                            return {status: r.status, url: r.url, body: t.substring(0, 800)};
                        } catch (e) { return {error: String(e)}; }
                    }""", [u, h, body])
                print(f"\n[{u}] [{h_name}] status={result.get('status')} final={result.get('url','')[:70]}")
                if result.get("error"): print("  ERR:", result["error"])
                else: print("  ", result["body"].replace(chr(10), " ")[:300])
        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())