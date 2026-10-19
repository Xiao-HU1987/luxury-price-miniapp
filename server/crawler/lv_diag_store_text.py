"""诊断：测试文本搜索门店流程，确认能否通过输入城市名获取门店。

用法：
  cd server
  venv/bin/python3.11 -m crawler.lv_diag_store_text <SKU或URL>
"""
import asyncio
import os
import sys

for v in ("http_proxy", "https_proxy", "HTTP_PROXY", "HTTPS_PROXY",
          "all_proxy", "ALL_PROXY"):
    os.environ.pop(v, None)

from playwright.async_api import async_playwright


async def js_eval(page, script, label):
    try:
        r = await page.evaluate(script)
        print(f"[{label}] -> {r}")
        return r
    except Exception as e:
        print(f"[{label}] 异常: {e}")
        return None


async def main():
    url = sys.argv[1] if len(sys.argv) > 1 else "https://jp.louisvuitton.com/jpn-jp/products/rush-bumbag-g72-nvprod7260027v/M26763"
    async with async_playwright() as pw:
        browser = await pw.chromium.connect_over_cdp("http://127.0.0.1:9333")
        ctx = browser.contexts[0] if browser.contexts else await browser.new_context()
        page = await ctx.new_page()

        print(f"导航到: {url}")
        try:
            resp = await page.goto(url, wait_until="domcontentloaded", timeout=45000)
            print(f"HTTP: {resp.status if resp else 'None'} -> {page.url}")
        except Exception as e:
            print(f"导航异常: {str(e).split(chr(10))[0]}")
        await asyncio.sleep(6)

        # 展开面板
        await js_eval(page, r"""() => {
            const panels = document.querySelectorAll('.lv-expandable-panel');
            for (const p of panels) {
                if ((p.innerText||'').includes('ストアの在庫状況を確認する')) {
                    const btn = p.querySelector('button[aria-expanded]');
                    if (btn) { btn.setAttribute('aria-expanded','true'); btn.setAttribute('aria-disabled','false'); btn.click(); }
                    const content = p.querySelector('.lv-expandable-panel__content');
                    if (content) { content.style.display='block'; content.setAttribute('aria-hidden','false'); }
                }
            }
        }""", "展开面板")
        await asyncio.sleep(3)

        # 点击库存按钮
        await js_eval(page, r"""() => {
            const btn = document.querySelector('.lv-product-locate-in-store__container');
            if (btn) { btn.click(); return {clicked:true}; }
            return {clicked:false};
        }""", "点击库存按钮")
        await asyncio.sleep(5)

        # 输入城市名 - 用 Playwright fill
        input_el = page.locator('.lv-address-search-form__input')
        if await input_el.count() > 0:
            await input_el.first.click()
            await asyncio.sleep(1)
            await input_el.first.fill("東京")
            print("[输入] -> 東京")

            # 等待补全建议
            for wait_ms in [1500, 2000, 3000, 3000]:
                await asyncio.sleep(wait_ms / 1000)
                sugg = await js_eval(page, r"""() => {
                    const modal = document.querySelector('.lv-locate-in-store__first-step-modal, .lv-modal__content');
                    if (!modal) return {count:0};
                    const sels = [
                        '[class*="suggestion"] li', '[class*="suggestion"] > *',
                        '[role="option"]', '.lv-address-search-form__suggestion-item',
                        '[class*="autocomplete"] li', '[class*="dropdown"] li',
                        'li[class*="result"]', '[class*="result"] li'
                    ];
                    const out = [];
                    for (const sel of sels) {
                        const els = modal.querySelectorAll(sel);
                        if (els.length > 0) {
                            for (const el of els) {
                                const rect = el.getBoundingClientRect();
                                out.push({sel, text:(el.innerText||'').substring(0,80), visible: rect.width>0&&rect.height>0});
                            }
                            break;
                        }
                    }
                    const sbtn = document.querySelector('.lv-address-search-form__button');
                    return {count: out.length, items: out.slice(0,5), searchBtnDisabled: sbtn ? sbtn.hasAttribute('disabled') : null};
                }""", f"补全建议({int(wait_ms)}ms)")
                if sugg and sugg.get("count", 0) > 0:
                    print("✅ 发现补全建议！")
                    # 点击第一个补全项
                    await js_eval(page, r"""() => {
                        const modal = document.querySelector('.lv-locate-in-store__first-step-modal, .lv-modal__content');
                        if (!modal) return {ok:false};
                        const sels = [
                            '[class*="suggestion"] li', '[role="option"]',
                            '.lv-address-search-form__suggestion-item',
                            '[class*="autocomplete"] li', '[class*="dropdown"] li'
                        ];
                        for (const sel of sels) {
                            const els = modal.querySelectorAll(sel);
                            for (const el of els) {
                                const rect = el.getBoundingClientRect();
                                if (rect.width>0 && rect.height>0) { el.click(); return {ok:true, sel, text:(el.innerText||'').substring(0,60)}; }
                            }
                        }
                        return {ok:false};
                    }""", "点击补全项")
                    await asyncio.sleep(2)
                    break

            # 检查搜索按钮状态并点击
            disabled = await js_eval(page, r"""() => {
                const btn = document.querySelector('.lv-address-search-form__button');
                if (!btn) return 'no-btn';
                return {disabled: btn.hasAttribute('disabled'), text:(btn.innerText||'').substring(0,30)};
            }""", "搜索按钮状态")
            if disabled and isinstance(disabled, dict) and not disabled.get("disabled"):
                await js_eval(page, r"""() => {
                    const btn = document.querySelector('.lv-address-search-form__button');
                    if (btn) { btn.click(); return {clicked:true}; }
                    return {clicked:false};
                }""", "点击搜索按钮")

            # 等待结果
            for wait_s in [3,5,5,5]:
                await asyncio.sleep(wait_s)
                info = await js_eval(page, r"""() => {
                    const result = {};
                    const sels = ['.lv-locate-in-store__second-step-modal','.lv-store-card-detailed','.lv-store-card','[class*="store-card"]','[class*="no-result"]','[class*="empty"]'];
                    for (const sel of sels) {
                        const els = document.querySelectorAll(sel);
                        if (els.length > 0) {
                            const items = [];
                            for (const el of els) {
                                const rect = el.getBoundingClientRect();
                                items.push({visible: rect.width>0&&rect.height>0, text:(el.innerText||'').substring(0,120), classes:(el.className||'').substring(0,60)});
                            }
                            result[sel] = {count: els.length, items: items.slice(0,3)};
                        }
                    }
                    const step = document.querySelector('.lv-locate-in-store__second-step-modal');
                    if (step) result.secondText = (step.innerText||'').substring(0,400);
                    return result;
                }""", f"等待{wait_s}s后状态")
                if info and ('.lv-store-card-detailed' in info or '.lv-store-card' in info):
                    print("\n✅ 发现门店卡片！")
                    break

        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())