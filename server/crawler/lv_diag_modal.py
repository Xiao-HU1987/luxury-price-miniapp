"""诊断脚本：通过 CDP 9333 检查 LV JP 商品页弹窗 DOM 结构。

用法：
  cd server
  venv/bin/python3.11 -m crawler.lv_diag_modal
"""
import asyncio
import os

for v in ("http_proxy", "https_proxy", "HTTP_PROXY", "HTTPS_PROXY",
          "all_proxy", "ALL_PROXY"):
    os.environ.pop(v, None)

from playwright.async_api import async_playwright


async def main():
    async with async_playwright() as pw:
        browser = await pw.chromium.connect_over_cdp("http://127.0.0.1:9333")
        context = browser.contexts[0] if browser.contexts else await browser.new_context()
        page = context.pages[0] if context.pages else await context.new_page()

        print(f"当前页面 URL: {page.url}")
        print(f"当前页面 title: {await page.title()}")

        # === 第1步：检查库存面板的完整 HTML 结构 ===
        panel_html = await page.evaluate(r"""() => {
            const panels = document.querySelectorAll('.lv-expandable-panel');
            for (const panel of panels) {
                if ((panel.innerText||'').includes('ストアの在庫状況')) {
                    return {
                        outerHTML: panel.outerHTML.substring(0, 3000),
                        innerHTML: panel.innerHTML.substring(0, 3000),
                        ariaExpanded: panel.getAttribute('aria-expanded'),
                        classes: panel.className,
                        childCount: panel.children.length,
                    };
                }
            }
            return { found: false };
        }""")
        print("\n=== 库存面板 HTML 结构 ===")
        if panel_html.get("found") is False:
            print("未找到库存面板")
        else:
            print(f"classes: {panel_html.get('classes')}")
            print(f"aria-expanded: {panel_html.get('ariaExpanded')}")
            print(f"childCount: {panel_html.get('childCount')}")
            print(f"innerHTML:\n{panel_html.get('innerHTML','')[:2000]}")

        # === 第2步：找到并点击「ストアの在庫状況を確認する」按钮 ===
        print("\n=== 点击库存面板按钮 ===")
        click_result = await page.evaluate(r"""() => {
            // 方法1：找所有按钮，文本匹配
            const btns = document.querySelectorAll('button, a, [role="button"]');
            for (const btn of btns) {
                const text = (btn.innerText || '').trim();
                if (text === 'ストアの在庫状況を確認する' || text.includes('ストアの在庫状況')) {
                    const rect = btn.getBoundingClientRect();
                    if (rect.width > 0 && rect.height > 0) {
                        btn.click();
                        return { ok: true, method: 'text_match', tag: btn.tagName, classes: btn.className, text: text.substring(0,50) };
                    }
                }
            }
            // 方法2：在 lv-expandable-panel 内找按钮
            const panels = document.querySelectorAll('.lv-expandable-panel');
            for (const panel of panels) {
                if ((panel.innerText||'').includes('ストアの在庫状況')) {
                    const btn = panel.querySelector('button, a, [role="button"], .lv-expandable-panel__button');
                    if (btn) {
                        btn.click();
                        return { ok: true, method: 'panel_btn', tag: btn.tagName, classes: btn.className, text: (btn.innerText||'').substring(0,50) };
                    }
                    // 直接点击 panel 本身
                    panel.click();
                    return { ok: true, method: 'panel_click', tag: panel.tagName, classes: panel.className };
                }
            }
            return { ok: false };
        }""")
        print(f"点击结果: {click_result}")

        # 等待面板展开
        await page.wait_for_timeout(3000)

        # === 第3步：检查面板展开后的状态 ===
        after_expand = await page.evaluate(r"""() => {
            const result = {};
            const panel = Array.from(document.querySelectorAll('.lv-expandable-panel'))
                .find(p => (p.innerText||'').includes('ストアの在庫状況'));
            if (panel) {
                const btn = panel.querySelector('button, [role="button"]');
                const content = panel.querySelector('.lv-expandable-panel__content, .lv-expandable-panel__body');
                const locateBtn = panel.querySelector('.lv-product-locate-in-store, .lv-product-locate-in-store__container');
                result.panelExpanded = panel.getAttribute('aria-expanded');
                result.btnExpanded = btn ? btn.getAttribute('aria-expanded') : null;
                result.contentVisible = content ? (content.getAttribute('aria-hidden') !== 'true' && content.style.display !== 'none') : null;
                if (content) {
                    result.contentDisplay = content.style.display;
                    result.contentAriaHidden = content.getAttribute('aria-hidden');
                }
                if (locateBtn) {
                    const rect = locateBtn.getBoundingClientRect();
                    result.locateBtnVisible = rect.width > 0 && rect.height > 0;
                    result.locateBtnW = Math.round(rect.width);
                    result.locateBtnH = Math.round(rect.height);
                    result.locateBtnText = (locateBtn.innerText || '').substring(0, 100);
                }
            }
            return result;
        }""")
        print(f"\n面板展开后状态: {after_expand}")

        # === 第4步：如果库存按钮可见，点击它打开弹窗 ===
        if after_expand.get("locateBtnVisible"):
            print("\n=== 点击库存按钮打开弹窗 ===")
            try:
                locate_btn = page.locator('.lv-product-locate-in-store__container')
                if await locate_btn.count() > 0:
                    await locate_btn.first.click(timeout=5000)
                    print("已点击 .lv-product-locate-in-store__container")
            except Exception as e:
                print(f"Playwright click 失败: {e}")
                # 回退 JS click
                clicked = await page.evaluate(r"""() => {
                    const btn = document.querySelector('.lv-product-locate-in-store__container');
                    if (btn) { btn.click(); return true; }
                    return false;
                }""")
                print(f"JS click 结果: {clicked}")

            # 等待弹窗加载
            await page.wait_for_timeout(5000)

            # === 第5步：检查弹窗状态 ===
            modal_state = await page.evaluate(r"""() => {
                const result = {};
                const sels = [
                    '.lv-modal__container', '.lv-modal__content', '.lv-modal',
                    '.lv-locate-in-store', '.lv-locate-in-store__first-step-modal',
                    '.lv-locate-in-store__second-step-modal',
                    '.lv-address-search-form', '.lv-address-search-form__input',
                    '.lv-address-search-form__button',
                    '.lv-store-geolocation', '.lv-store-geolocation__get-button',
                    '.lv-store-card-detailed',
                ];
                for (const sel of sels) {
                    const els = document.querySelectorAll(sel);
                    if (els.length > 0) {
                        const info = [];
                        for (const el of els) {
                            const rect = el.getBoundingClientRect();
                            info.push({
                                visible: rect.width > 0 && rect.height > 0,
                                w: Math.round(rect.width), h: Math.round(rect.height),
                                text: (el.innerText || '').substring(0, 150),
                                classes: (el.className || '').substring(0, 80),
                                disabled: el.hasAttribute && el.hasAttribute('disabled'),
                            });
                            if (info.length >= 2) break;
                        }
                        result[sel] = { count: els.length, items: info };
                    }
                }
                // 所有可见按钮
                const visibleBtns = [];
                document.querySelectorAll('button').forEach(btn => {
                    const rect = btn.getBoundingClientRect();
                    if (rect.width > 0 && rect.height > 0) {
                        const text = (btn.innerText || '').trim();
                        if (text && text.length < 50) {
                            visibleBtns.push({ text, classes: (btn.className||'').substring(0,60), disabled: btn.hasAttribute('disabled') });
                        }
                    }
                });
                result.visibleBtns = visibleBtns.slice(0, 15);
                // 所有可见 input
                const visibleInputs = [];
                document.querySelectorAll('input').forEach(inp => {
                    const rect = inp.getBoundingClientRect();
                    if (rect.width > 0 && rect.height > 0) {
                        visibleInputs.push({ type: inp.type, placeholder: inp.getAttribute('placeholder')||'', value: inp.value, classes: (inp.className||'').substring(0,60) });
                    }
                });
                result.visibleInputs = visibleInputs;
                return result;
            }""")
            print(f"\n=== 弹窗状态 ===")
            for sel, info in modal_state.items():
                if sel in ('visibleBtns', 'visibleInputs'): continue
                print(f"\n{sel} (count={info['count']}):")
                for i, item in enumerate(info["items"]):
                    print(f"  [{i}] visible={item['visible']} w={item['w']} h={item['h']} disabled={item.get('disabled')}")
                    if item.get('text'): print(f"      text: {item['text'][:100]}")
                    if item.get('classes'): print(f"      class: {item['classes']}")
            print(f"\n可见按钮:")
            for btn in modal_state.get("visibleBtns", []):
                print(f"  [{btn['text']}] disabled={btn.get('disabled')} class={btn.get('classes','')}")
            print(f"\n可见 input:")
            for inp in modal_state.get("visibleInputs", []):
                print(f"  type={inp['type']} placeholder={inp.get('placeholder','')[:40]} value={inp.get('value','')[:20]} class={inp.get('classes','')}")
        else:
            print("\n库存按钮不可见，面板可能未展开")

        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
