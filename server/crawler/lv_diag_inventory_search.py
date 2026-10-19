"""
诊断脚本：连接运行中的 Chrome (CDP 9333)，检查库存弹窗的搜索交互
"""
import asyncio
import json
import os
import sys
import time

# 清空代理
for v in ("http_proxy", "https_proxy", "HTTP_PROXY", "HTTPS_PROXY", "all_proxy", "ALL_PROXY"):
    os.environ.pop(v, None)

from playwright.async_api import async_playwright

CDP_ENDPOINT = "http://127.0.0.1:9333"


async def diagnose():
    async with async_playwright() as pw:
        print("=" * 60)
        print("连接 Chrome CDP...")
        browser = await pw.chromium.connect_over_cdp(CDP_ENDPOINT)
        ctx = browser.contexts[0]
        page = ctx.pages[0] if ctx.pages else await ctx.new_page()

        print(f"当前页面: {page.url}")
        print(f"页面标题: {await page.title()}")

        # ================================================================
        # 1. 检查库存面板是否存在
        # ================================================================
        print("\n" + "=" * 60)
        print("1. 检查库存面板 DOM 结构")
        panel_info = await page.evaluate(r"""
            () => {
                const result = {};

                // 查找 expandable-panel
                const panels = document.querySelectorAll('.lv-expandable-panel');
                result.panelCount = panels.length;
                result.panels = [];

                for (let i = 0; i < panels.length; i++) {
                    const p = panels[i];
                    const text = (p.innerText || '').substring(0, 200);
                    const btn = p.querySelector('button[aria-expanded]');
                    result.panels.push({
                        index: i,
                        text: text,
                        hasButton: !!btn,
                        isExpanded: btn ? btn.getAttribute('aria-expanded') : null,
                        btnText: btn ? (btn.innerText || '').substring(0, 100) : '',
                    });
                }

                // 查找库存相关文本
                const allText = document.body ? document.body.innerText : '';
                result.hasStoreText = allText.includes('ストアの在庫状況を確認する');
                result.hasStoreText2 = allText.includes('在庫状況');

                // 查找 locate-in-store 弹窗
                const firstModal = document.querySelector('.lv-locate-in-store__first-step-modal');
                const secondModal = document.querySelector('.lv-locate-in-store__second-step-modal');
                result.firstModal = firstModal ? {
                    visible: firstModal.getBoundingClientRect().width > 0,
                    display: firstModal.style.display || window.getComputedStyle(firstModal).display,
                } : null;
                result.secondModal = secondModal ? {
                    visible: secondModal.getBoundingClientRect().width > 0,
                    display: secondModal.style.display || window.getComputedStyle(secondModal).display,
                    storeCards: secondModal.querySelectorAll('.lv-store-card-detailed').length,
                } : null;

                return result;
            }
        """)
        print(json.dumps(panel_info, indent=2, ensure_ascii=False))

        # ================================================================
        # 2. 如果面板未展开，尝试展开它
        # ================================================================
        print("\n" + "=" * 60)
        print("2. 尝试展开库存面板...")

        stock_text = "ストアの在庫状況を確認する"

        # 先滚动页面确保面板可见
        await page.evaluate(r"""
            (stockText) => {
                const panels = document.querySelectorAll('.lv-expandable-panel');
                for (const panel of panels) {
                    if ((panel.innerText||'').includes(stockText)) {
                        panel.scrollIntoView({behavior: 'instant', block: 'center'});
                        return true;
                    }
                }
                return false;
            }
        """, stock_text)
        await asyncio.sleep(1)

        # 检查展开状态
        expanded = await page.evaluate(r"""
            (stockText) => {
                const panels = document.querySelectorAll('.lv-expandable-panel');
                for (const panel of panels) {
                    if ((panel.innerText||'').includes(stockText)) {
                        const btn = panel.querySelector('button[aria-expanded]');
                        return btn ? btn.getAttribute('aria-expanded') : null;
                    }
                }
                return null;
            }
        """, stock_text)
        print(f"面板展开状态: {expanded}")

        if expanded != "true":
            # 尝试 Playwright 点击
            try:
                await page.locator(f'button[aria-expanded]:has-text("{stock_text}")').first.click(timeout=5000)
                print("Playwright 点击成功")
            except Exception as e:
                print(f"Playwright 点击失败: {e}")
                # JS 点击
                await page.evaluate(r"""
                    (stockText) => {
                        const panels = document.querySelectorAll('.lv-expandable-panel');
                        for (const panel of panels) {
                            if ((panel.innerText||'').includes(stockText)) {
                                const btn = panel.querySelector('button[aria-expanded]');
                                if (btn) { btn.click(); return 'clicked'; }
                            }
                        }
                        return 'not found';
                    }
                """, stock_text)
                print("JS 点击执行")

            await asyncio.sleep(3)

        # ================================================================
        # 3. 检查面板展开后的内容
        # ================================================================
        print("\n" + "=" * 60)
        print("3. 检查面板展开后内容...")

        expanded_content = await page.evaluate(r"""
            (stockText) => {
                const result = {};
                const panels = document.querySelectorAll('.lv-expandable-panel');
                for (const panel of panels) {
                    if ((panel.innerText||'').includes(stockText)) {
                        result.panelHTML = panel.innerHTML.substring(0, 2000);

                        // 查找 locate-in-store 按钮
                        const locateBtn = panel.querySelector('.lv-product-locate-in-store__container');
                        result.hasLocateBtn = !!locateBtn;
                        if (locateBtn) {
                            const rect = locateBtn.getBoundingClientRect();
                            result.locateBtnRect = {x: rect.x, y: rect.y, w: rect.width, h: rect.height};
                            result.locateBtnText = (locateBtn.innerText || '').substring(0, 200);
                        }

                        // 查找所有按钮
                        const allBtns = panel.querySelectorAll('button');
                        result.buttons = [];
                        for (const b of allBtns) {
                            result.buttons.push({
                                text: (b.innerText || '').substring(0, 100),
                                visible: b.getBoundingClientRect().width > 0,
                            });
                        }

                        return result;
                    }
                }
                return {error: 'panel not found'};
            }
        """, stock_text)
        print(json.dumps(expanded_content, indent=2, ensure_ascii=False)[:3000])

        # ================================================================
        # 4. 尝试点击「在庫状況を見る」按钮
        # ================================================================
        if expanded_content.get("hasLocateBtn"):
            print("\n" + "=" * 60)
            print("4. 点击门店库存按钮...")

            # 禁用 backdrop
            await page.evaluate(r"""
                () => {
                    const backdrops = document.querySelectorAll('.lv-modal__backdrop, .lv-backdrop');
                    for (const b of backdrops) {
                        b.style.pointerEvents = 'none';
                        b.style.opacity = '0.3';
                    }
                }
            """)

            try:
                locate_btn = page.locator('.lv-product-locate-in-store__container')
                if await locate_btn.count() > 0:
                    await locate_btn.first.scroll_into_view_if_needed(timeout=3000)
                    await asyncio.sleep(1)
                    await locate_btn.first.click(force=True, timeout=5000)
                    print("Playwright 点击库存按钮成功")
                else:
                    print("未找到库存按钮")
            except Exception as e:
                print(f"Playwright 点击失败: {e}")
                # JS 点击
                await page.evaluate("""
                    () => {
                        const btn = document.querySelector('.lv-product-locate-in-store__container');
                        if (btn) btn.click();
                    }
                """)
                print("JS 点击执行")

            # 等待弹窗
            await asyncio.sleep(5)

            # ================================================================
            # 5. 检查弹窗 DOM
            # ================================================================
            print("\n" + "=" * 60)
            print("5. 检查弹窗 DOM...")

            modal_info = await page.evaluate(r"""
                () => {
                    const result = {};

                    const firstModal = document.querySelector('.lv-locate-in-store__first-step-modal');
                    const secondModal = document.querySelector('.lv-locate-in-store__second-step-modal');
                    const anyModal = document.querySelector('.lv-modal__container, .lv-modal, [class*="modal"]');

                    result.firstModal = firstModal ? {
                        visible: firstModal.getBoundingClientRect().width > 0,
                        html: firstModal.innerHTML.substring(0, 1500),
                    } : null;
                    result.secondModal = secondModal ? {
                        visible: secondModal.getBoundingClientRect().width > 0,
                        html: secondModal.innerHTML.substring(0, 1500),
                    } : null;
                    result.anyModal = anyModal ? {
                        className: anyModal.className,
                        visible: anyModal.getBoundingClientRect().width > 0,
                    } : null;

                    // 查找搜索输入框
                    const searchInputs = document.querySelectorAll('input[type="search"], input[type="text"], input');
                    result.searchInputs = [];
                    for (const inp of searchInputs) {
                        const rect = inp.getBoundingClientRect();
                        if (rect.width > 0) {
                            result.searchInputs.push({
                                type: inp.type,
                                placeholder: inp.placeholder || '',
                                id: inp.id || '',
                                className: (inp.className || '').substring(0, 100),
                                visible: true,
                            });
                        }
                    }

                    // 查找所有弹窗内的按钮
                    const modalBtns = document.querySelectorAll('.lv-modal__container button, .lv-modal button, [class*="modal"] button');
                    result.modalButtons = [];
                    for (const b of modalBtns) {
                        const rect = b.getBoundingClientRect();
                        if (rect.width > 0) {
                            result.modalButtons.push({
                                text: (b.innerText || '').substring(0, 80),
                                className: (b.className || '').substring(0, 80),
                            });
                        }
                    }

                    return result;
                }
            """)
            print(json.dumps(modal_info, indent=2, ensure_ascii=False)[:4000])

            # ================================================================
            # 6. 尝试搜索「東京」
            # ================================================================
            if modal_info.get("firstModal") or modal_info.get("searchInputs"):
                print("\n" + "=" * 60)
                print("6. 尝试搜索「東京」...")

                # 先尝试地理位置搜索
                try:
                    await ctx.grant_permissions(['geolocation'])
                    await ctx.set_geolocation({"latitude": 35.6762, "longitude": 139.6503})
                    print("地理位置已设置: 东京")
                except Exception as e:
                    print(f"地理位置设置失败: {e}")

                await asyncio.sleep(1)

                # 点击地理位置按钮
                geo_btn = page.locator('.lv-store-geolocation__get-button')
                if await geo_btn.count() > 0:
                    print("找到地理位置按钮，点击...")
                    await geo_btn.first.click(force=True, timeout=3000)
                    await asyncio.sleep(5)

                # 检查搜索结果
                search_result = await page.evaluate(r"""
                    () => {
                        const result = {};
                        const second = document.querySelector('.lv-locate-in-store__second-step-modal');
                        result.secondModalExists = !!second;

                        if (second) {
                            result.secondVisible = second.getBoundingClientRect().width > 0;
                            result.secondDisplay = second.style.display || window.getComputedStyle(second).display;
                            const cards = second.querySelectorAll('.lv-store-card-detailed');
                            result.storeCards = cards.length;

                            if (cards.length > 0) {
                                result.firstCard = {
                                    html: cards[0].innerHTML.substring(0, 500),
                                    text: cards[0].innerText.substring(0, 300),
                                };
                            }

                            // 检查是否有 "no result" 消息
                            const noResult = second.querySelector('[class*="no-result"], [class*="empty"], [class*="no-store"]');
                            result.hasNoResult = !!noResult;
                            if (noResult) {
                                result.noResultText = noResult.innerText.substring(0, 200);
                            }

                            result.secondHTML = second.innerHTML.substring(0, 2000);
                        }

                        return result;
                    }
                """)
                print(json.dumps(search_result, indent=2, ensure_ascii=False)[:4000])

                # 如果没有结果，尝试文本搜索
                if not search_result.get("storeCards"):
                    print("\n--- 地理位置搜索无结果，尝试文本搜索「東京」---")

                    # 先回到第一步
                    await page.evaluate("""
                        () => {
                            const first = document.querySelector('.lv-locate-in-store__first-step-modal');
                            const second = document.querySelector('.lv-locate-in-store__second-step-modal');
                            if (first && second) {
                                first.style.display = 'block';
                                second.style.display = 'none';
                            }
                        }
                    """)
                    await asyncio.sleep(1)

                    # 检查搜索输入框
                    search_input = page.locator('#address-search-input, .lv-address-search-form__input, input[type="search"], input[type="text"]')
                    input_count = await search_input.count()
                    print(f"搜索输入框数量: {input_count}")

                    if input_count > 0:
                        # 点击输入框
                        await search_input.first.click(force=True, timeout=3000)
                        await asyncio.sleep(0.5)

                        # 清空
                        await search_input.first.fill('')
                        await asyncio.sleep(0.3)
                        await search_input.first.evaluate("el => { el.value = ''; el.dispatchEvent(new Event('input', {bubbles: true})); }")
                        await asyncio.sleep(0.5)

                        # 输入城市名
                        await search_input.first.type("東京", delay=100)
                        print("已输入「東京」")
                        await asyncio.sleep(3)

                        # 检查是否有自动补全
                        suggestions = await page.evaluate("""
                            () => {
                                const modal = document.querySelector('.lv-modal__content') || document.querySelector('.lv-modal__container') || document;
                                const sels = modal.querySelectorAll('[class*="suggestion"] li, [role="option"], [class*="autocomplete"] li, [class*="dropdown"] li');
                                const result = [];
                                for (const s of sels) {
                                    if (s.getBoundingClientRect().width > 0) {
                                        result.push(s.innerText.substring(0, 100));
                                    }
                                }
                                return result;
                            }
                        """)
                        print(f"自动补全建议: {suggestions}")

                        if suggestions:
                            # 点击第一个建议
                            await page.evaluate("""
                                () => {
                                    const modal = document.querySelector('.lv-modal__content') || document.querySelector('.lv-modal__container') || document;
                                    const sels = modal.querySelectorAll('[class*="suggestion"] li, [role="option"]');
                                    for (const s of sels) {
                                        if (s.getBoundingClientRect().width > 0) {
                                            s.click();
                                            return 'clicked';
                                        }
                                    }
                                    return 'none';
                                }
                            """)
                            print("已点击第一个建议")
                            await asyncio.sleep(2)

                        # 点击搜索按钮
                        search_btn = page.locator('.lv-address-search-form__button, button:has-text("検索")')
                        btn_count = await search_btn.count()
                        print(f"搜索按钮数量: {btn_count}")

                        if btn_count > 0:
                            await search_btn.first.click(force=True, timeout=3000)
                            print("已点击搜索按钮")
                            await asyncio.sleep(5)

                        # 最终检查结果
                        final_result = await page.evaluate(r"""
                            () => {
                                const result = {};
                                const second = document.querySelector('.lv-locate-in-store__second-step-modal');
                                result.secondExists = !!second;
                                if (second) {
                                    result.secondVisible = second.getBoundingClientRect().width > 0;
                                    result.cards = second.querySelectorAll('.lv-store-card-detailed').length;
                                    result.secondHTML = second.innerHTML.substring(0, 2000);
                                }
                                const first = document.querySelector('.lv-locate-in-store__first-step-modal');
                                result.firstExists = !!first;
                                if (first) {
                                    result.firstVisible = first.getBoundingClientRect().width > 0;
                                }
                                return result;
                            }
                        """)
                        print("\n最终结果:")
                        print(json.dumps(final_result, indent=2, ensure_ascii=False)[:3000])

        # 截图
        try:
            await page.screenshot(path="/tmp/lv_diag_screenshot.png", full_page=False)
            print("\n截图已保存: /tmp/lv_diag_screenshot.png")
        except Exception as e:
            print(f"截图失败: {e}")

        await browser.close()
        print("\n诊断完成")


if __name__ == "__main__":
    asyncio.run(diagnose())