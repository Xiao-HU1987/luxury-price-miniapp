"""快速连通性测试：通过CDP在Chrome内访问JP官网，确认Akamai是否解封。"""
import asyncio
import sys
from playwright.async_api import async_playwright

CDP_ENDPOINT = "http://127.0.0.1:9333"


async def main():
    url = sys.argv[1] if len(sys.argv) > 1 else "https://jp.louisvuitton.com/jpn-jp/homepage"
    async with async_playwright() as pw:
        browser = await pw.chromium.connect_over_cdp(CDP_ENDPOINT)
        ctx = browser.contexts[0] if browser.contexts else await browser.new_context(
            locale="ja-JP", timezone_id="Asia/Tokyo")
        page = await ctx.new_page()
        try:
            resp = await page.goto(url, wait_until="domcontentloaded", timeout=45000)
            status = resp.status if resp else None
            print(f"[连通性] HTTP {status} -> {page.url}")
            # 检测是否被Akamai拦截（页面标题含browser check / verify）
            title = await page.title()
            print(f"[标题] {title}")
            body = await page.evaluate("document.body ? document.body.innerText.substring(0,300) : ''")
            print(f"[正文前300] {body}")
            if status == 200 and "louisvuitton" in page.url:
                print(">>> 结论：Akamai 已解封，网页正常访问")
            else:
                print(">>> 结论：可能仍被拦截")
        except Exception as e:
            print(f"[异常] {str(e).split(chr(10))[0]}")
        finally:
            await page.close()
            await browser.close()


if __name__ == "__main__":
    asyncio.run(main())