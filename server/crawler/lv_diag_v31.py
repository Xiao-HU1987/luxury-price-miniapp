"""方案A v31：直接调用 /jpn-jp/stores/query API 测试门店库存。

用法：venv/bin/python3.11 -m crawler.lv_diag_v31 <SKU> [城市]
"""
import asyncio
import os
import sys
import json

for v in ("http_proxy", "https_proxy", "HTTP_PROXY", "HTTPS_PROXY",
          "all_proxy", "ALL_PROXY"):
    os.environ.pop(v, None)

from playwright.async_api import async_playwright


async def main():
    args = sys.argv[1:]
    sku = args[0] if args else "M26763"
    city = args[1] if len(args) > 1 else "東京"
    async with async_playwright() as pw:
        browser = await pw.chromium.connect_over_cdp("http://127.0.0.1:9333")
        ctx = browser.contexts[0] if browser.contexts else await browser.new_context()
        page = await ctx.new_page()

        # 先访问商品页建立会话
        await page.goto(f"https://jp.louisvuitton.com/jpn-jp/products/-/{sku}",
                        wait_until="domcontentloaded", timeout=45000)
        await asyncio.sleep(4)

        # 直接调用 API
        payload = {
            "country": "JP", "countryUrl": "jpn-jp", "skuId": sku,
            "query": city, "pageType": "product", "limit": 50,
            "useGeoCode": False, "province": "", "storeLang": "ja-JP",
            "clickAndCollect": "false", "flagShip": "false",
        }
        result = await page.evaluate(
            r"""async ([url, payload]) => {
                try {
                    const r = await fetch(url, {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify(payload),
                    });
                    const text = await r.text();
                    let json = null;
                    try { json = JSON.parse(text); } catch(e) {}
                    return {status: r.status, body: text.substring(0, 4000), json: json};
                } catch (e) { return {error: String(e)}; }
            }""",
            [f"https://jp.louisvuitton.com/jpn-jp/stores/query", payload],
        )

        print(f"=== stores/query API (SKU={sku}, city={city}) ===")
        if result.get("error"):
            print("错误:", result["error"])
            return
        print("状态:", result["status"])
        if result.get("json"):
            try:
                print(json.dumps(result["json"], ensure_ascii=False, indent=2)[:4000])
            except Exception as e:
                print("JSON未解析:", e, result["body"][:500])
        else:
            print("BODY:", result["body"][:1000])

        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())