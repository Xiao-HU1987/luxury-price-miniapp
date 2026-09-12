"""诊断弹窗切换状态"""
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

        await page.goto("https://jp.louisvuitton.com/jpn-jp/products/-/M26763", wait_until="domcontentloaded", timeout=45000)
        await asyncio.sleep(8)

        # 展开面板
        await page.evaluate(r"""() => {
            const panels = document.querySelectorAll('.lv-expandable-panel');
            for (const p of panels) {
                if ((p.innerText||'').includes('ストアの在庫状況を確認する')) {
                    p.scrollIntoView({block:'center'});
                    const btn = p.querySelector('button[aria-expanded]');
                    if (btn && btn.getAttribute('aria-expanded') !== 'true') btn.click();
                    break;
                }
            }
        }""")
        await asyncio.sleep(2)

        # 点击库存按钮
        await page.evaluate(r"""() => {
            const btn = document.querySelector('.lv-product-locate-in-store__container');
            if (btn) btn.click();
        }""")
        await asyncio.sleep(4)
        await page.evaluate(r"""() => {
            document.querySelectorAll('.lv-modal__backdrop, .lv-backdrop').forEach(b => { b.style.pointerEvents='none'; b.style.opacity='0'; });
        }""")

        # 检查弹窗初始状态
        s0 = await page.evaluate(r"""() => {
            const f = document.querySelector('.lv-locate-in-store__first-step-modal');
            const s = document.querySelector('.lv-locate-in-store__second-step-modal');
            const inp = document.querySelector('.lv-address-search-form__input');
            return { first: !!f, second: !!s, inp_val: inp ? inp.value : 'NO_INPUT', inp_len: inp ? inp.value.length : 0 };
        }""")
        print("弹窗初始状态:", json.dumps(s0, ensure_ascii=False))

        # 输入并搜索
        inp = page.locator('.lv-address-search-form__input')
        if await inp.count() > 0:
            await inp.first.click(timeout=3000)
            await asyncio.sleep(0.5)
            await inp.first.press_sequentially("東京都", delay=200)
            await asyncio.sleep(6)

            # 检查输入后
            s1 = await page.evaluate(r"""() => {
                const inp = document.querySelector('.lv-address-search-form__input');
                const btn = document.querySelector('.lv-address-search-form__button');
                return { inp_val: inp ? inp.value : '', btn_disabled: btn ? btn.disabled : 'NO_BTN' };
            }""")
            print("输入后:", json.dumps(s1, ensure_ascii=False))

            btn = page.locator('.lv-address-search-form__button')
            if await btn.count() > 0:
                if await btn.first.get_attribute('disabled') is None:
                    await btn.first.click(timeout=5000)
                    print("已点击搜索")

            await asyncio.sleep(12)

            # 检查切换后
            s2 = await page.evaluate(r"""() => {
                const f = document.querySelector('.lv-locate-in-store__first-step-modal');
                const s = document.querySelector('.lv-locate-in-store__second-step-modal');
                const cards = s ? s.querySelectorAll('.lv-store-card-detailed') : [];
                const noResults = s ? s.querySelector('[class*="no-result"], [class*="no-results"]') : null;
                return {
                    first_display: f ? getComputedStyle(f).display : 'NO_FIRST',
                    second_display: s ? getComputedStyle(s).display : 'NO_SECOND',
                    card_count: cards.length,
                    no_results_text: noResults ? noResults.innerText.trim() : '',
                    second_text: s ? (s.innerText||'').substring(0,400) : ''
                };
            }""")
            print("搜索后:", json.dumps(s2, ensure_ascii=False, indent=2))

        await browser.close()

asyncio.run(main())