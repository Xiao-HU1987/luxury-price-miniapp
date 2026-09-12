"""快速网络连通性诊断：用真实 Chrome(CDP) 导航商品页，验证当前 IP 能否通过 Akamai。"""
import asyncio
import sys
import time

from playwright.async_api import async_playwright

CDP_ENDPOINT = "http://127.0.0.1:9333"


async def main():
    sku = sys.argv[1] if len(sys.argv) > 1 else "M26763"
    url = f"https://jp.louisvuitton.com/jpn-jp/products/-/{sku}"

    async with async_playwright() as pw:
        browser = await pw.chromium.connect_over_cdp(CDP_ENDPOINT)
        ctx = browser.contexts[0] if browser.contexts else await browser.new_context(
            locale="ja-JP", timezone_id="Asia/Tokyo")
        page = await ctx.new_page()

        print(f"=== 导航: {url} ===")
        t0 = time.time()
        try:
            resp = await page.goto(url, wait_until="domcontentloaded", timeout=45000)
            status = resp.status if resp else "None"
        except Exception as e:
            status = f"EXC:{str(e).splitlines()[0]}"
        print(f"HTTP {status} | 耗时 {time.time()-t0:.1f}s | URL={page.url}")

        # 页面标题与 SKU 校验
        title = await page.title()
        print(f"标题: {title}")
        has_sku = await page.locator("text=" + sku).count()
        print(f"页面含SKU文本: {has_sku}")

        # 检查是否被 Akamai 拦截页
        body_has_block = await page.locator(".akamai-block, .fp-block, #fp").count()
        print(f"Akamai拦截标记: {body_has_block}")

        await page.close()
        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())