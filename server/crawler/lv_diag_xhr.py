"""监听所有 XHR/Fetch 请求（不限域名），确认点击'在庫状況を見る'后发出什么请求。

流程：打开弹窗 → 输入東京 → 点击'在庫状況を見る' → 打印所有 XHR/Fetch 请求。
"""
import asyncio
import os
import sys

for v in ("http_proxy", "https_proxy", "HTTP_PROXY", "HTTPS_PROXY",
          "all_proxy", "ALL_PROXY"):
    os.environ.pop(v, None)

from playwright.async_api import async_playwright

PANEL_TEXT = "ストアの在庫状況を確認する"
REQUESTS = []


async def main():
    url = sys.argv[1] if len(sys.argv) > 1 else "https://jp.louisvuitton.com/jpn-jp/products/-/M26763"
    async with async_playwright() as pw:
        browser = await pw.chromium.connect_over_cdp("http://127.0.0.1:9333")
        ctx = browser.contexts[0] if browser.contexts else await browser.new_context()
        page = await ctx.new_page()
        await page.set_viewport_size({"width": 1440, "height": 900})

        # 监听所有请求（XHR/Fetch/document）
        async def on_request(req):
            if req.resource_type in ("xhr", "fetch", "document"):
                REQUESTS.append(("REQ", req.method, req.url))
        async def on_response(resp):
            if resp.request.resource_type in ("xhr", "fetch", "document"):
                REQUESTS.append(("RESP", resp.status, resp.url))
        page.on("request", on_request)
        page.on("response", on_response)

        print(f"=== 导航: {url} ===")
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=45000)
        except Exception as e:
            print(f"导航异常: {str(e).split(chr(10))[0]}")
        await asyncio.sleep(8)

        # 展开面板 + 打开弹窗
        await page.evaluate("""(txt)=>{const ps=document.querySelectorAll('.lv-expandable-panel');
            for(const p of ps){if((p.innerText||'').includes(txt)){const b=p.querySelector('button[aria-expanded]');
            if(b&&b.getAttribute('aria-expanded')!=='true')b.click();return'ok';}}return'no';}""", PANEL_TEXT)
        await asyncio.sleep(2)
        await page.evaluate("""()=>{const b=document.querySelector('.lv-product-locate-in-store__container');
            if(b){b.click();return'ok';}return'no';}""")
        await asyncio.sleep(5)

        # 输入地址
        inp = page.locator(".-sidepanel.lv-locate-in-store .lv-address-search-form__input")
        if await inp.count() > 0:
            await inp.first.click(timeout=3000)
            await inp.first.fill("")
            await asyncio.sleep(0.3)
            await inp.first.type("東京", delay=130)
            await asyncio.sleep(3)
            print(f"输入值: '{await inp.first.input_value()}'")

        # 清空请求记录，专注点击后的请求
        REQUESTS.clear()

        # 点击'在庫状況を見る'
        print("\n=== 点击'在庫状況を見る' ===")
        see = page.locator(".-sidepanel.lv-locate-in-store button")
        clicked = False
        for i in range(await see.count()):
            t = await see.nth(i).inner_text()
            if "在庫状況を見る" in t:
                dis = await see.nth(i).is_disabled()
                print(f"按钮[{i}] disabled={dis}")
                if not dis:
                    await see.nth(i).click(timeout=5000)
                    clicked = True
                break
        print(f"clicked={clicked}")
        await asyncio.sleep(12)

        print(f"\n=== 点击后所有 XHR/Fetch/Document 请求 ({len(REQUESTS)} 条) ===")
        for kind, st, u in REQUESTS:
            print(f"  [{kind} {st}] {u[:200]}")

        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())