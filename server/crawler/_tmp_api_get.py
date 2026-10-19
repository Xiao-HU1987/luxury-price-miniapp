"""测试直接调用 API（GET 请求格式）"""
import asyncio, os, urllib.parse
for _proxy_var in ("http_proxy", "https_proxy", "HTTP_PROXY", "HTTPS_PROXY",
                   "all_proxy", "ALL_PROXY"):
    os.environ.pop(_proxy_var, None)
from playwright.async_api import async_playwright
import json

CDP = "http://127.0.0.1:9333"

async def main():
    async with async_playwright() as pw:
        browser = await pw.chromium.connect_over_cdp(CDP)
        ctx = browser.contexts[0] if browser.contexts else await browser.new_context()
        page = await ctx.new_page()
        await page.goto("https://jp.louisvuitton.com/jpn-jp/homepage", wait_until="domcontentloaded", timeout=45000)
        await asyncio.sleep(5)

        # 从之前捕获的 params 构建 API 参数
        base_params = {
            "getRankingInfo": True,
            "attributesToRetrieve": ["storeName","defaultStoreName","internalName","city","streetAddress","postalCode","distance","phoneNumber","images","storeHours","seoChunk","_geoloc","visible","country","callCenter","clickAndCollectEnabled","flagShipStoreMention","books","jewelry","leatherGoodsAndAccessories","myLV","perfume","readyToWearMen","readyToWearWomen","shoeMen","shoeWomen","sunGlasses","watches","writing","closingDays","displayLocateInStore","displayPriority","newBorn","state","timeZone","migratedToXStore","beauty"],
            "facetFilters": [["visible:true"]],
            "attributesToHighlight": [""],
            "page": 0,
            "hitsPerPage": 1000,
            "ruleContexts": [None],
        }

        results = []

        for query in ["東京", "東京都", "大阪", "大阪府"]:
            query_params = base_params.copy()
            query_params["query"] = query

            print(f"\n查询: {query}")
            result = await page.evaluate(
                r"""
                async ([params]) => {
                    try {
                        const resp = await fetch(
                            'https://api.louisvuitton.com/eco-eu/search-merch-eapi/v1/jpn-jp/stores/query',
                            {
                                method: 'POST',
                                headers: {
                                    'Content-Type': 'application/json',
                                    'Accept': 'application/json'
                                },
                                credentials: 'include',
                                body: JSON.stringify(params)
                            }
                        );
                        const json = await resp.json();
                        return { status: resp.status, data: json };
                    } catch (e) {
                        return { error: String(e) };
                    }
                }
                """,
                [query_params],
            )
            if result.get("error"):
                print(f"  ERROR: {result['error'][:80]}")
                continue
            data = result.get("data", {})
            nb = data.get("nbHits", 0)
            print(f"  nbHits: {nb}")
            for h in data.get("hits", [])[:3]:
                name = h.get("name", "")
                addr = h.get("address", {})
                stock = None
                for p in h.get("additionalProperty", []):
                    if p.get("name") == "stockAvailability":
                        stock = p.get("value")
                print(f"    {name} | stock={stock} | {addr.get('state','')} {addr.get('addressLocality','')}")

            await asyncio.sleep(2)

        await browser.close()

asyncio.run(main())