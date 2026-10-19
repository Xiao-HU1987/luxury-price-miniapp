"""直接用浏览器 fetch 调用 stores/query API，测试多城市"""
import asyncio, os
for _proxy_var in ("http_proxy", "https_proxy", "HTTP_PROXY", "HTTPS_PROXY",
                   "all_proxy", "ALL_PROXY"):
    os.environ.pop(_proxy_var, None)
from playwright.async_api import async_playwright
import json

CDP = "http://127.0.0.1:9333"
CITIES = ["東京都", "大阪府", "京都府", "神奈川県", "愛知県", "福岡県", "北海道"]

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

        all_results = {}

        for CITY in CITIES:
            print(f"\n搜索: {CITY} ...", end=" ", flush=True)
            # 直接在浏览器中 fetch API（自动带 cookies）
            result = await page.evaluate(
                r"""
                async ([city]) => {
                    try {
                        const resp = await fetch(
                            'https://api.louisvuitton.com/eco-eu/search-merch-eapi/v1/jpn-jp/stores/query',
                            {
                                method: 'POST',
                                headers: { 'Content-Type': 'application/json' },
                                body: JSON.stringify({
                                    query: city,
                                    hitsPerPage: 1000,
                                    page: 0
                                })
                            }
                        );
                        const json = await resp.json();
                        return { status: resp.status, data: json };
                    } catch (e) {
                        return { error: String(e) };
                    }
                }
                """,
                [CITY],
            )

            if result.get("error"):
                print(f"ERROR: {result['error'][:80]}")
                continue

            data = result.get("data", {})
            hits = data.get("hits", [])
            nb = data.get("nbHits", 0)
            print(f"nbHits={nb}")

            if nb == 0:
                continue

            for h in hits:
                name = h.get("name", "")
                addr = h.get("address", {})
                stock = None
                for prop in h.get("additionalProperty", []):
                    if prop.get("name") == "stockAvailability":
                        stock = prop.get("value")
                addr_str = f"{addr.get('state','')} {addr.get('addressLocality','')} {addr.get('streetAddress','')}"
                identifier = h.get("identifier", "")
                has_stock = stock == "true"
                key = identifier or name
                if key not in all_results:
                    all_results[key] = {"name": name, "stock": stock, "has_stock": has_stock, "addr": addr_str}
                print(f"  {name} [{identifier}] stock={stock} | {addr_str}")

            await asyncio.sleep(2)  # 避免请求太快

        print(f"\n\n=== 汇总 ({len(all_results)} 家门店) ===")
        in_stock = [v for v in all_results.values() if v["has_stock"]]
        out_stock = [v for v in all_results.values() if not v["has_stock"]]
        print(f"有库存: {len(in_stock)} 家")
        for s in in_stock:
            print(f"  ✓ {s['name']} | {s['addr']}")
        print(f"无库存: {len(out_stock)} 家")
        for s in out_stock[:5]:
            print(f"  ✗ {s['name']} | {s['addr']}")
        if len(out_stock) > 5:
            print(f"  ... 及其他 {len(out_stock) - 5} 家")

        await browser.close()

asyncio.run(main())