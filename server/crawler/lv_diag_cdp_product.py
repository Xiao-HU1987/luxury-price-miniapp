"""诊断：CDP连接方式下访问商品页，确认是否规避403。

用法：
  cd server
  venv/bin/python3.11 -m crawler.lv_diag_cdp_product
"""
import asyncio
import os

for v in ("http_proxy", "https_proxy", "HTTP_PROXY", "HTTPS_PROXY",
          "all_proxy", "ALL_PROXY"):
    os.environ.pop(v, None)

from playwright.async_api import async_playwright


async def main():
    async with async_playwright() as pw:
        browser = await pw.chromium.connect_over_cdp("http://127.0.0.1:9333")
        ctx = browser.contexts[0] if browser.contexts else await browser.new_context()
        page = await ctx.new_page()

        # 先访问首页建立基线
        resp = await page.goto("https://jp.louisvuitton.com/jpn-jp/homepage",
                               wait_until="domcontentloaded", timeout=45000)
        print(f"首页 HTTP: {resp.status if resp else 'None'}")
        body = await page.evaluate("document.body ? document.body.innerText.substring(0,100) : ''")
        print(f"首页 body: {body[:80]}")
        await asyncio.sleep(3)

        # 访问商品页
        url = "https://jp.louisvuitton.com/jpn-jp/products/-/M28029"
        print(f"\n=== 访问商品页 {url} ===")
        resp2 = await page.goto(url, wait_until="domcontentloaded", timeout=45000)
        print(f"HTTP: {resp2.status if resp2 else 'None'}")
        await asyncio.sleep(6)
        try:
            title = await page.title()
            print(f"标题: {title}")
        except Exception as e:
            print(f"title异常: {e}")
        try:
            body2 = await page.evaluate("document.body ? document.body.innerText.substring(0,300) : ''")
            print(f"body: {body2[:260]}")
        except Exception as e:
            print(f"body异常: {e}")
        print(f"URL: {page.url}")
        # 检查价格元素
        try:
            has_price = await page.evaluate("""() => {
                const els = document.querySelectorAll('.lv-price, [itemprop="price"]');
                for (const el of els) { const t=(el.innerText||'').trim(); if(t && /[0-9]/.test(t)) return t; }
                return '';
            }""")
            print(f"价格: {has_price}")
        except Exception as e:
            print(f"价格检查异常: {e}")

        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())