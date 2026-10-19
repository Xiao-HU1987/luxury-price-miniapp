"""全部用 Playwright 真实点击，触发 Vue 组件事件"""
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
        page = await ctx.new_page()

        resp = await page.goto("https://jp.louisvuitton.com/jpn-jp/products/-/M26763", wait_until="networkidle", timeout=60000)
        print(f"HTTP: {resp.status if resp else 'None'}, URL: {page.url}")
        await asyncio.sleep(10)  # 额外等待 Vue 组件初始化

        # 1. Playwright 真实点击展开面板按钮
        panel_btn = page.locator('.lv-expandable-panel:has-text("ストアの在庫状況を確認する") button[aria-expanded]')
        if await panel_btn.count() > 0:
            await panel_btn.first.scroll_into_view_if_needed(timeout=5000)
            await panel_btn.first.click(timeout=5000)
            print("已展开库存面板")
        else:
            print("未找到面板按钮")
        await asyncio.sleep(3)

        # 2. Playwright 真实点击库存按钮
        store_btn = page.locator('.lv-product-locate-in-store__container')
        if await store_btn.count() > 0:
            await store_btn.first.scroll_into_view_if_needed(timeout=5000)
            await store_btn.first.click(timeout=5000)
            print("已打开库存弹窗")
        await asyncio.sleep(5)
        await page.evaluate(r"""() => {
            document.querySelectorAll('.lv-modal__backdrop, .lv-backdrop').forEach(b => { b.style.pointerEvents='none'; b.style.opacity='0'; });
        }""")

        # 检查弹窗
        s0 = await page.evaluate(r"""() => {
            const f = document.querySelector('.lv-locate-in-store__first-step-modal');
            const s = document.querySelector('.lv-locate-in-store__second-step-modal');
            return { first: !!f, second: !!s };
        }""")
        print("弹窗:", s0)

        # 3. Playwright 真实输入并搜索
        inp = page.locator('.lv-address-search-form__input')
        if await inp.count() > 0:
            await inp.first.click(timeout=3000)
            await asyncio.sleep(0.5)
            # 用 type() 代替 press_sequentially，确保键盘事件完整
            await page.keyboard.type("東京都", delay=200)
            await asyncio.sleep(3)
            # 确认输入值
            val = await inp.first.input_value()
            print(f"输入值: '{val}'")
            await asyncio.sleep(6)

            # 尝试按 Enter 提交
            await inp.first.press('Enter')
            print("已按Enter搜索")
            await asyncio.sleep(5)

            # 如果还没有第二步弹窗，尝试直接触发提交
            s_check = await page.evaluate("() => !!document.querySelector('.lv-locate-in-store__second-step-modal')")
            if not s_check:
                print("第二步弹窗未出现，尝试提交表单...")
                await page.evaluate(r"""() => {
                    const form = document.querySelector('.lv-address-search-form');
                    if (form) {
                        form.dispatchEvent(new Event('submit', {bubbles: true, cancelable: true}));
                        return 'submitted';
                    }
                    // 尝试找 Vue 实例
                    const input = document.querySelector('.lv-address-search-form__input');
                    if (input && input.__vue__) {
                        input.__vue__.$emit('search');
                        return 'vue_emit';
                    }
                    // 尝试所有 Vue 实例
                    const allEls = document.querySelectorAll('[class*="lv-"]');
                    for (const el of allEls) {
                        if (el.__vue__ && el.__vue__.search) {
                            el.__vue__.search();
                            return 'vue_search';
                        }
                    }
                    return 'not_found';
                }""")
            await asyncio.sleep(15)

        # 检查结果
        s2 = await page.evaluate(r"""() => {
            const f = document.querySelector('.lv-locate-in-store__first-step-modal');
            const s = document.querySelector('.lv-locate-in-store__second-step-modal');
            const cards = s ? s.querySelectorAll('.lv-store-card-detailed') : [];
            return {
                first_display: f ? getComputedStyle(f).display : 'NO',
                second_exists: !!s,
                second_visible: s ? s.getBoundingClientRect().width > 0 : false,
                card_count: cards.length,
                second_text: s ? (s.innerText||'').substring(0,500) : ''
            };
        }""")
        print("结果:", json.dumps(s2, ensure_ascii=False, indent=2))

        if s2["card_count"] > 0:
            stores = await page.evaluate(r"""() => {
                const cards = document.querySelectorAll('.lv-store-card-detailed');
                const out = [];
                for (const c of cards) {
                    const n = c.querySelector('.lv-store-card-detailed__name');
                    const i = c.querySelector('.lv-store-card-detailed__info');
                    const s = c.querySelector('.lv-store-card-detailed__stock');
                    out.push({name: n?n.innerText.trim():'', addr: i?i.innerText.trim().replace(/\n/g,' '):'', stock: s?s.innerText.trim():''});
                }
                return out;
            }""")
            for s in stores:
                print(f"  {s['name']} | {s['stock']} | {s['addr'][:60]}")

        await browser.close()

asyncio.run(main())