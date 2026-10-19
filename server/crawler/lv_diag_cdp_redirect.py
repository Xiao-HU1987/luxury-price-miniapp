"""诊断：CDP方式下访问商品页，分析重定向过程与最终URL。

用法：
  cd server
  venv/bin/python3.11 -m crawler.lv_diag_cdp_redirect
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

        # 监听重定向
        redirects = []
        page.on("request", lambda req: redirects.append(
            f"{req.method} {req.url} -> {req.redirected_from and req.redirected_from.url}"
        ) if req.redirected_from else None)

        url = "https://jp.louisvuitton.com/jpn-jp/products/-/M28029"
        print(f"=== 访问 {url} ===")
        try:
            resp = await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            print(f"HTTP: {resp.status if resp else 'None'} 最终URL: {page.url}")
        except Exception as e:
            print(f"goto异常: {type(e).__name__}: {e}")
            print(f"当前URL: {page.url}")

        await asyncio.sleep(3)
        print("\n=== 重定向记录 ===")
        for r in redirects[-15:]:
            print(f"  {r}")

        # 尝试用 slug 格式
        await asyncio.sleep(2)
        url2 = "https://jp.louisvuitton.com/jpn-jp/products/-/M26763"
        print(f"\n=== 访问 {url2} (已采集参考) ===")
        try:
            resp = await page.goto(url2, wait_until="domcontentloaded", timeout=30000)
            print(f"HTTP: {resp.status if resp else 'None'} 最终URL: {page.url}")
        except Exception as e:
            print(f"goto异常: {type(e).__name__}: {e}")
            print(f"当前URL: {page.url}")

        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())