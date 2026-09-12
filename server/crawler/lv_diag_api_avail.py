"""诊断：直接调用 LV 官方库存 API，查看返回结构。

用法：
  cd server
  venv/bin/python3.11 -m crawler.lv_diag_api_avail <SKU>
"""
import asyncio
import os
import sys

for v in ("http_proxy", "https_proxy", "HTTP_PROXY", "HTTPS_PROXY",
          "all_proxy", "ALL_PROXY"):
    os.environ.pop(v, None)

from playwright.async_api import async_playwright

API_URL = (
    "https://api.louisvuitton.com/eco-as/lvcom-prodct-dtl-eapi/"
    "v2/products/jpn-jp/availability"
)


async def main():
    sku = sys.argv[1] if len(sys.argv) > 1 else "M26763"
    async with async_playwright() as pw:
        browser = await pw.chromium.connect_over_cdp("http://127.0.0.1:9333")
        ctx = browser.contexts[0] if browser.contexts else await browser.new_context()
        page = await ctx.new_page()

        # 先访问商品页建立 cookie
        await page.goto(f"https://jp.louisvuitton.com/jpn-jp/products/-/{sku}",
                        wait_until="domcontentloaded", timeout=45000)
        await asyncio.sleep(3)

        # 调用 API
        result = await page.evaluate(
            r"""
            async ([url, skuId]) => {
                try {
                    const r = await fetch(url, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ skuIds: [skuId] }),
                    });
                    const text = await r.text();
                    let json = null;
                    try { json = JSON.parse(text); } catch(e) {}
                    return { status: r.status, body: text.substring(0, 3000), json: json };
                } catch (e) {
                    return { error: String(e) };
                }
            }
            """,
            [API_URL, sku],
        )

        print(f"=== API 响应 (SKU={sku}) ===")
        if result.get("error"):
            print(f"错误: {result['error']}")
        else:
            print(f"状态: {result['status']}")
            print(f"body前500字符: {result['body'][:500]}")
            print(f"\n=== 解析后的JSON ===")
            import json
            print(json.dumps(result.get("json"), ensure_ascii=False, indent=2)[:3000])

        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())