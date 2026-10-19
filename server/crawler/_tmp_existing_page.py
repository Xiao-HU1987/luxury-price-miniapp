"""使用当前已打开的页面（不重新导航），测试搜索"""
import asyncio, os
for _proxy_var in ("http_proxy", "https_proxy", "HTTP_PROXY", "HTTPS_PROXY",
                   "all_proxy", "ALL_PROXY"):
    os.environ.pop(_proxy_var, None)
from playwright.async_api import async_playwright
import json

CDP = "http://127.0.0.1:9333"

async def main():
    async with async_playwright() as pw:
        browser = await pw.chromium.connect_over_cdp(CDP)
        ctx = browser.contexts[0] if browser.contexts else await browser.new_context()

        # 找已打开的 LV 产品页
        page = None
        for p in ctx.pages:
            if "louisvuitton" in p.url and "products" in p.url:
                page = p
                break
        if not page:
            page = await ctx.new_page()
            await page.goto("https://jp.louisvuitton.com/jpn-jp/products/-/M26763", wait_until="networkidle", timeout=60000)
            await asyncio.sleep(10)
        print("页面:", page.url)

        # 检查当前弹窗状态
        state = await page.evaluate(r"""() => {
            const f = document.querySelector('.lv-locate-in-store__first-step-modal');
            const s = document.querySelector('.lv-locate-in-store__second-step-modal');
            const inp = document.querySelector('.lv-address-search-form__input');
            return {
                first: f ? {display: getComputedStyle(f).display, text: (f.innerText||'').substring(0,200)} : null,
                second: s ? {display: getComputedStyle(s).display, text: (s.innerText||'').substring(0,200)} : null,
                inp_val: inp ? inp.value : null
            };
        }""")
        print("当前状态:", json.dumps(state, ensure_ascii=False, indent=2))

        # 如果弹窗没打开，先打开
        if not state["first"] or state["first"]["display"] == "none":
            # 展开面板
            panel_btn = page.locator('.lv-expandable-panel:has-text("ストアの在庫状況を確認する") button[aria-expanded]')
            if await panel_btn.count() > 0:
                await panel_btn.first.scroll_into_view_if_needed(timeout=5000)
                await panel_btn.first.click(timeout=5000)
                await asyncio.sleep(3)
            # 点击库存按钮
            store_btn = page.locator('.lv-product-locate-in-store__container')
            if await store_btn.count() > 0:
                await store_btn.first.click(timeout=5000)
                await asyncio.sleep(5)
            await page.evaluate(r"""() => {
                document.querySelectorAll('.lv-modal__backdrop, .lv-backdrop').forEach(b => { b.style.pointerEvents='none'; b.style.opacity='0'; });
            }""")

        # 监听网络请求
        api_calls = []
        async def on_resp(resp):
            if "stores/query" in resp.url:
                try:
                    body = await resp.text()
                    api_calls.append({"status": resp.status, "body": body[:500]})
                except:
                    pass
        page.on("response", on_resp)

        # 输入并搜索
        inp = page.locator('.lv-address-search-form__input')
        if await inp.count() > 0:
            cur_val = await inp.first.input_value()
            print(f"当前输入值: '{cur_val}'")
            if cur_val:
                # 清空：全选+删除
                await inp.first.click(timeout=3000)
                await page.keyboard.press('Meta+A')
                await page.keyboard.press('Backspace')
                await asyncio.sleep(0.5)
            await page.keyboard.type("東京都", delay=200)
            await asyncio.sleep(3)
            val = await inp.first.input_value()
            print(f"输入后: '{val}'")
            await asyncio.sleep(3)

            # 点击搜索
            btn = page.locator('.lv-address-search-form__button')
            if await btn.count() > 0:
                dis = await btn.first.get_attribute('disabled')
                if dis is None:
                    await btn.first.click(timeout=5000)
                    print("已点击搜索")
            await asyncio.sleep(12)

        print(f"\nAPI调用: {len(api_calls)} 条")
        for i, c in enumerate(api_calls):
            print(f"  [{c['status']}] {c['body'][:300]}")

        # 最终状态
        state2 = await page.evaluate(r"""() => {
            const s = document.querySelector('.lv-locate-in-store__second-step-modal');
            const cards = s ? s.querySelectorAll('.lv-store-card-detailed') : [];
            return {second_exists: !!s, card_count: cards.length, text: s ? (s.innerText||'').substring(0,300) : ''};
        }""")
        print("最终:", json.dumps(state2, ensure_ascii=False))

        await browser.close()

asyncio.run(main())