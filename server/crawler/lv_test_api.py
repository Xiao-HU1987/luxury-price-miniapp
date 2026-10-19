"""
验证带完整 headers 的 stores/query API 调用
"""
import asyncio
import json
from playwright.async_api import async_playwright

CDP = "http://127.0.0.1:9333"


async def main():
    async with async_playwright() as pw:
        browser = await pw.chromium.connect_over_cdp(CDP)
        ctx = browser.contexts[0]
        page = ctx.pages[0] if ctx.pages else await ctx.new_page()

        # 提取认证信息
        device_id = await page.evaluate(
            "() => localStorage.getItem('LV.jpn-jp.deviceId')"
        )
        html = await page.content()
        import re
        m = re.search(r'"([a-f0-9]{32})"\s*,\s*"([a-fA-F0-9]{32})"', html)
        if m:
            client_id = m.group(1)
            client_secret = m.group(2)
        else:
            client_id = "607e3016889f431fb8020693311016c9"
            client_secret = "60bbcdcD722D411B88cBb72C8246a22F"

        print(f"device_id: {device_id}")
        print(f"client_id: {client_id}")
        print(f"client_secret: {client_secret}")

        # 测试 stores/query
        sku = "N40909"
        city = "東京"
        print(f"\n--- 测试 stores/query: SKU={sku}, city={city} ---")

        result = await page.evaluate("""
            async ([sku, city, client_id, client_secret, device_id, referer]) => {
                const resp = await fetch(
                    'https://api.louisvuitton.com/eco-eu/search-merch-eapi/v1/jpn-jp/stores/query',
                    {
                        method: 'POST',
                        credentials: 'include',
                        headers: {
                            'Content-Type': 'application/json',
                            'Accept': 'application/json',
                            'client_id': client_id,
                            'client_secret': client_secret,
                            'x-device-id': device_id,
                            'x-correlation-id': crypto.randomUUID().replace(/-/g, '').substring(0, 16),
                            'Origin': 'https://jp.louisvuitton.com',
                            'Referer': referer,
                        },
                        body: JSON.stringify({
                            flagShip: false,
                            country: '',
                            query: city,
                            clickAndCollect: false,
                            skuId: sku,
                            pageType: 'productsheet'
                        })
                    }
                );
                const status = resp.status;
                let data = null;
                try { data = await resp.json(); } catch(e) { data = {error: String(e)}; }
                return {status, data};
            }
        """, [sku, city, client_id, client_secret, device_id, page.url])

        print(f"Status: {result['status']}")
        if result['status'] == 200:
            data = result['data']
            print(f"nbHits: {data.get('nbHits', 0)}")
            if data.get('hits'):
                first = data['hits'][0]
                print(f"Keys: {list(first.keys())}")
                print(json.dumps(first, indent=2, ensure_ascii=False)[:3000])
        else:
            print(f"Error: {json.dumps(result.get('data', {}), ensure_ascii=False)[:500]}")

        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())