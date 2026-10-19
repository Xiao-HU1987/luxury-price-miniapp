"""诊断v5：测试文本搜索完整流程。

用法：
  cd server
  venv/bin/python3.11 -m crawler.lv_diag_text
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

        # === 0. 导航并等待 ===
        url = "https://jp.louisvuitton.com/jpn-jp/products/-/M46955"
        print(f"=== 导航到 {url} ===")
        try:
            await page.goto(url, timeout=30_000, wait_until="commit")
        except Exception:
            await page.goto(url, timeout=60_000, wait_until="domcontentloaded")

        # 等待价格元素
        try:
            await page.wait_for_function(
                """() => {
                    const els = document.querySelectorAll('.lv-price, [itemprop="price"]');
                    for (const el of els) {
                        const t = (el.innerText || el.textContent || '').trim();
                        if (t && /[0-9]/.test(t)) return true;
                    }
                    return false;
                }""",
                timeout=30_000,
            )
        except Exception:
            pass

        await page.wait_for_timeout(5000)

        # === 1. 强制展开面板 ===
        await page.evaluate(r"""() => {
            const panels = document.querySelectorAll('.lv-expandable-panel');
            for (const panel of panels) {
                if ((panel.innerText||'').includes('ストアの在庫状況を確認する')) {
                    const btn = panel.querySelector('button[aria-expanded]');
                    const content = panel.querySelector('.lv-expandable-panel__content');
                    if (btn) { btn.setAttribute('aria-expanded', 'true'); btn.setAttribute('aria-disabled', 'false'); }
                    if (content) { content.style.display = 'block'; content.setAttribute('aria-hidden', 'false'); }
                    return;
                }
            }
        }""")
        await page.wait_for_timeout(1000)

        # === 2. 点击库存按钮 ===
        try:
            locate_btn = page.locator('.lv-product-locate-in-store__container')
            if await locate_btn.count() > 0:
                await locate_btn.first.click(timeout=5000, force=True)
                print("库存按钮点击成功")
        except Exception as e:
            print(f"库存按钮点击失败: {e}")
            await page.evaluate(r"""() => { const b = document.querySelector('.lv-product-locate-in-store__container'); if (b) b.click(); }""")

        await page.wait_for_timeout(5000)

        # 检查弹窗
        modal_check = await page.evaluate(r"""() => {
            const first = document.querySelector('.lv-locate-in-store__first-step-modal');
            const input = document.querySelector('.lv-address-search-form__input');
            const searchBtn = document.querySelector('.lv-address-search-form__button');
            return {
                firstVisible: first ? first.getBoundingClientRect().width > 0 : false,
                inputVisible: input ? input.getBoundingClientRect().width > 0 : false,
                searchBtnDisabled: searchBtn ? searchBtn.hasAttribute('disabled') : null,
            };
        }""")
        print(f"弹窗状态: {modal_check}")

        if not modal_check.get("firstVisible"):
            print("弹窗未打开，终止")
            await browser.close()
            return

        # === 3. 文本搜索：输入"東京" ===
        print("\n=== 文本搜索：输入「東京」 ===")
        search_input = page.locator('.lv-address-search-form__input')
        if await search_input.count() > 0:
            await search_input.first.click(timeout=3000, force=True)
            await search_input.first.fill("東京")
            print("已输入「東京」")

            # 等待补全建议出现
            for wait_ms in [1000, 2000, 3000, 3000]:
                await page.wait_for_timeout(wait_ms)
                suggestions = await page.evaluate(r"""() => {
                    const modal = document.querySelector('.lv-locate-in-store__first-step-modal, .lv-modal__content');
                    if (!modal) return { count: 0 };
                    // 查找所有可能的补全项
                    const sels = [
                        '[class*="suggestion"] li',
                        '[class*="suggestion"] > *',
                        '[role="option"]',
                        '.lv-address-search-form__suggestion-item',
                        '[class*="autocomplete"] li',
                        '[class*="dropdown"] li',
                        'li[class*="result"]',
                    ];
                    const result = [];
                    for (const sel of sels) {
                        const els = modal.querySelectorAll(sel);
                        if (els.length > 0) {
                            for (const el of els) {
                                const rect = el.getBoundingClientRect();
                                result.push({
                                    sel: sel,
                                    text: (el.innerText || '').substring(0, 80),
                                    visible: rect.width > 0 && rect.height > 0,
                                    classes: (el.className || '').substring(0, 60),
                                });
                            }
                            break;
                        }
                    }
                    // 检查搜索按钮状态
                    const searchBtn = document.querySelector('.lv-address-search-form__button');
                    const btnDisabled = searchBtn ? searchBtn.hasAttribute('disabled') : null;
                    return { count: result.length, items: result, btnDisabled };
                }""")
                print(f"  等待 {wait_ms}ms 后: 补全项={suggestions.get('count',0)}, 搜索按钮disabled={suggestions.get('btnDisabled')}")
                for s in suggestions.get("items", [])[:5]:
                    print(f"    - sel={s['sel']} visible={s['visible']} text={s['text']} class={s.get('classes','')}")

                if suggestions.get("count", 0) > 0:
                    print("  发现补全建议！")
                    # 选择第一个补全项
                    selected = await page.evaluate(r"""() => {
                        const modal = document.querySelector('.lv-locate-in-store__first-step-modal, .lv-modal__content');
                        if (!modal) return { ok: false };
                        const sels = [
                            '[class*="suggestion"] li',
                            '[role="option"]',
                            '.lv-address-search-form__suggestion-item',
                            '[class*="autocomplete"] li',
                        ];
                        for (const sel of sels) {
                            const els = modal.querySelectorAll(sel);
                            if (els.length > 0) {
                                const first = els[0];
                                const rect = first.getBoundingClientRect();
                                if (rect.width > 0 && rect.height > 0) {
                                    first.click();
                                    return { ok: true, sel: sel, text: (first.innerText || '').substring(0, 80) };
                                }
                            }
                        }
                        return { ok: false };
                    }""")
                    print(f"  选择补全项: {selected}")
                    await page.wait_for_timeout(2000)
                    break

            # 检查搜索按钮状态
            btn_disabled = await page.evaluate(r"""() => {
                const btn = document.querySelector('.lv-address-search-form__button');
                return btn ? btn.hasAttribute('disabled') : null;
            }""")
            print(f"\n搜索按钮 disabled={btn_disabled}")

            # 点击搜索按钮
            if not btn_disabled:
                print("点击搜索按钮...")
                try:
                    search_btn = page.locator('.lv-address-search-form__button')
                    if await search_btn.count() > 0:
                        await search_btn.first.click(timeout=5000)
                        print("搜索按钮点击成功")
                except Exception as e:
                    print(f"搜索按钮点击失败: {e}")

                # 等待结果
                for wait_s in [3, 5, 5, 5, 5, 5]:
                    await page.wait_for_timeout(wait_s * 1000)
                    state = await page.evaluate(r"""() => {
                        const result = {};
                        const sels = [
                            '.lv-locate-in-store__second-step-modal',
                            '.lv-store-card-detailed',
                            '.lv-store-card',
                            '[class*="store-card"]',
                            '[class*="no-result"]',
                            '[class*="not-found"]',
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
                                        text: (el.innerText || '').substring(0, 200),
                                        classes: (el.className || '').substring(0, 80),
                                    });
                                    if (info.length >= 3) break;
                                }
                                result[sel] = { count: els.length, items: info };
                            }
                        }
                        const modal = document.querySelector('.lv-locate-in-store__first-step-modal, .lv-modal__content');
                        if (modal) result.modalText = (modal.innerText || '').substring(0, 500);
                        return result;
                    }""")
                    print(f"\n--- 等待 {wait_s}s 后 ---")
                    for sel, info in state.items():
                        if sel == 'modalText':
                            print(f"modalText:\n{info[:300]}")
                            continue
                        print(f"{sel} (count={info['count']}):")
                        for i, item in enumerate(info["items"]):
                            print(f"  [{i}] visible={item['visible']} w={item['w']} h={item['h']} text={item.get('text','')[:80]}")

                    if '.lv-store-card-detailed' in state or '.lv-store-card' in state:
                        print("\n✅ 发现门店卡片！")
                        break
                    if state.get('.lv-locate-in-store__second-step-modal', {}).get('items', [{}])[0].get('visible'):
                        print("\n✅ 第二步弹窗已可见！")
                        break

        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
