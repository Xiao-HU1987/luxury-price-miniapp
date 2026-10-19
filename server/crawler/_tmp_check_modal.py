"""检查库存弹窗当前状态（诊断第二步弹窗为何未出现）"""
import asyncio, os
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
            if "louisvuitton" in p.url and "products" in p.url:
                page = p
                break
        if not page:
            page = await ctx.new_page()
            await page.goto("https://jp.louisvuitton.com/jpn-jp/products/-/M26763", wait_until="domcontentloaded", timeout=45000)
            await asyncio.sleep(8)
        print("当前URL:", page.url)

        # 检查弹窗整体状态
        state = await page.evaluate(r"""() => {
            const modal = document.querySelector('.lv-locate-in-store');
            const first = document.querySelector('.lv-locate-in-store__first-step-modal');
            const second = document.querySelector('.lv-locate-in-store__second-step-modal');
            const backdrops = document.querySelectorAll('.lv-modal');
            const out = {modal_exists: !!modal, first_exists: !!first, second_exists: !!second,
                         backdrop_count: backdrops.length};
            if (first) {
                out.first_display = getComputedStyle(first).display;
                out.first_visible = first.getBoundingClientRect().width > 0;
                out.first_text = (first.innerText||'').substring(0,300);
            }
            if (second) {
                out.second_display = getComputedStyle(second).display;
                out.second_visible = second.getBoundingClientRect().width > 0;
                out.second_text = (second.innerText||'').substring(0,300);
            }
            // 页面上的错误提示
            const errs = document.querySelectorAll('[class*="error"], [class*="alert"], [class*="message"]');
            const errList = [];
            for (const e of errs) {
                const t = (e.innerText||'').trim();
                if (t && t.length < 200) errList.push(t);
            }
            out.page_errors = errList.slice(0,5);
            return out;
        }""")
        import json
        print(json.dumps(state, ensure_ascii=False, indent=2))

        await browser.close()

asyncio.run(main())