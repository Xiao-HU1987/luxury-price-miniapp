"""展开第一步弹窗完整结构，检查输入框和按钮"""
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

        # 确保弹窗打开
        await page.evaluate(r"""() => {
            const btn = document.querySelector('.lv-product-locate-in-store__container');
            if (btn) btn.click();
        }""")
        await asyncio.sleep(3)

        # 检查地理位置权限
        perm = await page.evaluate(r"""() => {
            return navigator.permissions.query({name:'geolocation'}).then(s => s.state).catch(e => 'err:'+e);
        }""")
        print("地理权限:", perm)

        # 转储第一步弹窗内所有可见元素
        els = await page.evaluate(r"""() => {
            const first = document.querySelector('.lv-locate-in-store__first-step-modal');
            if (!first) return {exists:false};
            const out = {exists:true, elements:[]};
            const tags = 'button,input,select,a,textarea,[role="button"]'.split(',');
            for (const tag of tags) {
                const nodes = first.querySelectorAll(tag);
                for (const el of nodes) {
                    const r = el.getBoundingClientRect();
                    if (r.width>0 && r.height>0) {
                        out.elements.push({
                            tag: el.tagName,
                            type: el.getAttribute('type')||'',
                            cls: (el.className||'').toString().substring(0,60),
                            text: (el.innerText||el.value||el.getAttribute('placeholder')||'').trim().substring(0,50),
                            disabled: el.disabled || el.getAttribute('disabled')
                        });
                    }
                }
            }
            return out;
        }""")
        import json
        print(json.dumps(els, ensure_ascii=False, indent=2))

        await browser.close()

asyncio.run(main())