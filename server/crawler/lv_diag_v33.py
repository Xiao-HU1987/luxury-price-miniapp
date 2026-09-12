"""方案A v33：用availability请求头调用 stores/query，尝试多种载荷。

用法：venv/bin/python3.11 -m crawler.lv_diag_v33 <SKU>
"""
import asyncio
import os
import sys
import json
import uuid

for v in ("http_proxy", "https_proxy", "HTTP_PROXY", "HTTPS_PROXY",
          "all_proxy", "ALL_PROXY"):
    os.environ.pop(v, None)

from playwright.async_api import async_playwright

# 东京坐标
TOKYO = {"lat": 35.6762, "lng": 139.6503}


async def main():
    sku = sys.argv[1] if len(sys.argv) > 1 else "M26763"
    async with async_playwright() as pw:
        browser = await pw.chromium.connect_over_cdp("http://127.0.0.1:9333")
        ctx = browser.contexts[0] if browser.contexts else await browser.new_context()
        page = await ctx.new_page()

        await page.goto(f"https://jp.louisvuitton.com/jpn-jp/products/-/{sku}",
                        wait_until="domcontentloaded", timeout=45000)
        await asyncio.sleep(4)

        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "client_id": "607e3016889f431fb8020693311016c9",
            "client_secret": "60bbcdcD722D411B88cBb72C8246a22F",
            "checkout-channel": "WEB",
            "x-device-id": str(uuid.uuid4()),
            "x-correlation-id": uuid.uuid4().hex[:16],
            "Referer": f"https://jp.louisvuitton.com/jpn-jp/products/-/{sku}",
        }

        payloads = {
            "query_name": {
                "country": "JP", "countryUrl": "jpn-jp", "skuId": sku,
                "query": "東京", "pageType": "product", "limit": 50,
                "useGeoCode": False, "province": "", "storeLang": "ja-JP",
                "flagShip": "false", "clickAndCollect": "false",
            },
            "query_coords": {
                "country": "JP", "countryUrl": "jpn-jp", "skuId": sku,
                "query": "東京", "pageType": "product", "limit": 50,
                "useGeoCode": True,
                "latitudeCenter": str(TOKYO["lat"]), "longitudeCenter": str(TOKYO["lng"]),
                "province": "", "storeLang": "ja-JP",
                "flagShip": "false", "clickAndCollect": "false",
            },
            "minimal": {
                "country": "JP", "skuId": sku, "query": "東京",
                "pageType": "product", "limit": 50,
            },
        }

        for name, payload in payloads.items():
            result = await page.evaluate(
                r"""async ([url, headers, payload]) => {
                    try {
                        const r = await fetch(url, {method:'POST', headers, body: JSON.stringify(payload)});
                        const text = await r.text();
                        return {status: r.status, body: text.substring(0, 2000)};
                    } catch (e) { return {error: String(e)}; }
                }""",
                ["https://jp.louisvuitton.com/jpn-jp/stores/query", headers, payload],
            )
            print(f"\n=== 载荷[{name}] 状态={result.get('status')} ===")
            if result.get("error"):
                print("错误:", result["error"])
            else:
                print(result["body"][:1200])

        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())