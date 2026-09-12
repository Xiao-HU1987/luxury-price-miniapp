"""清理多余标签页，只保留一个干净页面并导航到 LV 首页。"""
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
        pages = ctx.pages
        print(f"当前标签页: {len(pages)}")
        # 保留第一个 page，关闭其余
        keep = None
        for p in pages:
            if p.url.startswith("chrome://"):
                try:
                    await p.close()
                except Exception:
                    pass
                continue
            if keep is None:
                keep = p
            else:
                try:
                    await p.close()
                except Exception:
                    pass
        if keep is None:
            keep = await ctx.new_page()
        # 导航到 LV 首页
        try:
            await keep.goto("https://jp.louisvuitton.com/jpn-jp/homepage",
                            wait_until="domcontentloaded", timeout=45000)
            await asyncio.sleep(4)
            print(f"已导航到首页: {keep.url}")
        except Exception as e:
            print(f"导航异常: {str(e).split(chr(10))[0]}")
        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())