"""输入更完整地址，检查补全下拉和 API 响应，处理弹窗覆盖问题"""
import asyncio, os
for _proxy_var in ("http_proxy", "https_proxy", "HTTP_PROXY", "HTTPS_PROXY",
                   "all_proxy", "ALL_PROXY"):
    os.environ.pop(_proxy_var, None)
from playwright.async_api import async_playwright
import json

CDP = "http://127.0.0.1:9333"
CITY = "東京都"

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

        api_body = {}
        async def on_resp(resp):
            if "stores/query" in resp.url:
                try:
                    body = await resp.text()
                    api_body["status"] = resp.status
                    api_body["url"] = resp.url[:120]
                    api_body["body"] = body[:3000]
                except Exception as e:
                    api_body["err"] = str(e)
        page.on("response", on_resp)

        # 确保弹窗打开（先关闭旧弹窗）
        await page.evaluate(r"""() => {
            const closeBtn = document.querySelector('.lv-locate-in-store__second-step-modal [class*="close"]');
            if (closeBtn) closeBtn.click();
            const el = document.querySelector('.lv-product-locate-in-store__container');
            if (el) el.click();
        }""")
        await asyncio.sleep(4)

        # 禁用 backdrop 干扰
        await page.evaluate(r"""() => {
            document.querySelectorAll('.lv-modal__backdrop, .lv-backdrop').forEach(b => { b.style.pointerEvents='none'; b.style.opacity='0'; });
        }""")

        inp = page.locator('.lv-address-search-form__input')
        if await inp.count() > 0:
            # 用 evaluate 直接聚焦输入
            await page.evaluate(r"""() => {
                const i = document.querySelector('.lv-address-search-form__input');
                if (i) i.focus();
            }""")
            await asyncio.sleep(1)
            await inp.first.press_sequentially(CITY, delay=200)
            print(f"已输入: {CITY}")
            await asyncio.sleep(8)  # 等补全

            # 检查补全下拉（更宽泛）
            sugg = await page.evaluate(r"""() => {
                const out = {items: []};
                document.querySelectorAll('[role="option"], [class*="suggestion"], [class*="autocomplete"] li, [class*="result-list"] li, [class*="dropdown"] li').forEach(it => {
                    const r = it.getBoundingClientRect();
                    if (r.width>0 && r.height>0) out.items.push((it.innerText||'').trim().substring(0,80));
                });
                return out;
            }""")
            print("补全下拉:", json.dumps(sugg, ensure_ascii=False))

            # 点击补全项（如果有）
            picked = await page.evaluate(r"""() => {
                const items = document.querySelectorAll('[role="option"], [class*="suggestion"] li, [class*="autocomplete"] li, [class*="result-list"] li');
                for (const it of items) {
                    const r = it.getBoundingClientRect();
                    if (r.width>0 && r.height>0) { it.click(); return (it.innerText||'').trim().substring(0,80); }
                }
                return null;
            }""")
            print("选中的补全项:", picked)
            await asyncio.sleep(3)

            # 点击搜索按钮
            btn = page.locator('.lv-address-search-form__button')
            if await btn.count() > 0:
                dis = await btn.first.get_attribute('disabled')
                print("搜索按钮disabled:", dis)
                if dis is None:
                    await btn.first.click(timeout=5000)
                    print("已点击搜索按钮")
            await asyncio.sleep(12)

        print("\n=== stores/query API 响应 ===")
        if api_body:
            print(f"status: {api_body.get('status')}")
            print(f"body前2000: {api_body.get('body','')[:2000]}")
        else:
            print("(未捕获)")

        print("\n=== 第二步弹窗内容 ===")
        second = await page.evaluate(r"""() => {
            const s = document.querySelector('.lv-locate-in-store__second-step-modal');
            if (!s) return 'NO_SECOND';
            return {text: (s.innerText||'').substring(0,800), cards: s.querySelectorAll('[class*="store-card"]').length};
        }""")
        print(json.dumps(second, ensure_ascii=False, indent=2))

        await browser.close()

asyncio.run(main())