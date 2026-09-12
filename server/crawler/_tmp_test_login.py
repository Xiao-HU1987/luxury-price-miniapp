import asyncio, json, os
# 清空代理环境变量
for _proxy_var in ("http_proxy", "https_proxy", "HTTP_PROXY", "HTTPS_PROXY",
                   "all_proxy", "ALL_PROXY"):
    os.environ.pop(_proxy_var, None)
from playwright.async_api import async_playwright

CDP = "http://127.0.0.1:9333"

async def main():
    async with async_playwright() as pw:
        browser = await pw.chromium.connect_over_cdp(CDP)
        ctx = browser.contexts[0] if browser.contexts else await browser.new_context()
        page = None
        for p in ctx.pages:
            if "louisvuitton" in p.url:
                page = p
                break
        if not page:
            page = await ctx.new_page()
        print("当前URL:", page.url)
        login_info = await page.evaluate("""() => {
            const btns = document.querySelectorAll('button, a');
            const out = [];
            for (const b of btns) {
                const t = (b.innerText||'').trim();
                if (t && (t.includes('My LV') || t.includes('ログイン') || t.includes('ログアウト') || t.includes('アカウント') || t.includes('マイ')) && t.length < 30) {
                    out.push(t);
                }
            }
            return out.slice(0,10);
        }""")
        print("登录相关元素:", login_info)
        await browser.close()

asyncio.run(main())