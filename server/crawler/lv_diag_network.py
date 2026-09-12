"""
诊断脚本：检查地理位置搜索的网络请求 + 自动补全
"""
import asyncio
import json
import os

for v in ("http_proxy", "https_proxy", "HTTP_PROXY", "HTTPS_PROXY", "all_proxy", "ALL_PROXY"):
    os.environ.pop(v, None)

from playwright.async_api import async_playwright

CDP_ENDPOINT = "http://127.0.0.1:9333"


async def diagnose():
    async with async_playwright() as pw:
        print("连接 Chrome CDP...")
        browser = await pw.chromium.connect_over_cdp(CDP_ENDPOINT)
        ctx = browser.contexts[0]
        page = ctx.pages[0] if ctx.pages else await ctx.new_page()

        print(f"当前页面: {page.url}")

        # 检查当前弹窗状态
        modal_state = await page.evaluate("""
            () => {
                const first = document.querySelector('.lv-locate-in-store__first-step-modal');
                const second = document.querySelector('.lv-locate-in-store__second-step-modal');
                return {
                    firstExists: !!first,
                    firstVisible: first ? first.getBoundingClientRect().width > 0 : false,
                    secondExists: !!second,
                    secondVisible: second ? second.getBoundingClientRect().width > 0 : false,
                    secondCards: second ? second.querySelectorAll('.lv-store-card-detailed').length : 0,
                };
            }
        """)
        print(f"弹窗状态: {json.dumps(modal_state, indent=2, ensure_ascii=False)}")

        # 如果弹窗已关闭，重新打开
        if not modal_state.get("firstVisible"):
            print("弹窗未打开，尝试重新打开...")
            # 点击库存按钮
            locate_btn = page.locator('.lv-product-locate-in-store__container')
            if await locate_btn.count() > 0:
                await locate_btn.first.click(force=True, timeout=5000)
                await asyncio.sleep(4)
                print("弹窗已重新打开")
            else:
                print("未找到库存按钮，退出")
                await browser.close()
                return

        # 回到第一步（如果当前在第二步）
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

        # ================================================================
        # 1. 测试：直接输入城市名 + 回车（不依赖自动补全）
        # ================================================================
        print("\n" + "=" * 60)
        print("测试1: 直接输入「東京」+ 回车提交")

        search_input = page.locator('#address-search-input')
        if await search_input.count() > 0:
            await search_input.first.click(force=True, timeout=3000)
            await asyncio.sleep(0.5)

            # 清空
            await search_input.first.fill('')
            await asyncio.sleep(0.3)
            await search_input.first.evaluate("el => { el.value = ''; el.dispatchEvent(new Event('input', {bubbles: true})); }")
            await asyncio.sleep(0.5)

            # 输入
            await search_input.first.type("東京", delay=100)
            print("已输入「東京」")
            await asyncio.sleep(3)

            # 检查自动补全
            suggestions = await page.evaluate("""
                () => {
                    const result = [];
                    // 更广泛的搜索
                    const all = document.querySelectorAll('[role="listbox"], [role="option"], [class*="suggestion"], [class*="autocomplete"], [class*="dropdown"], [class*="combobox"], ul[class*="result"]');
                    for (const el of all) {
                        const rect = el.getBoundingClientRect();
                        if (rect.width > 0 && rect.height > 0) {
                            result.push({
                                tag: el.tagName,
                                role: el.getAttribute('role'),
                                className: (el.className || '').substring(0, 100),
                                text: (el.innerText || '').substring(0, 200),
                                childCount: el.children.length,
                            });
                        }
                    }
                    return result;
                }
            """)
            print(f"自动补全元素: {json.dumps(suggestions, indent=2, ensure_ascii=False)[:2000]}")

            # 按回车提交搜索
            await search_input.first.press("Enter")
            print("已按回车提交")
            await asyncio.sleep(5)

            # 检查结果
            result = await page.evaluate("""
                () => {
                    const second = document.querySelector('.lv-locate-in-store__second-step-modal');
                    if (!second) return {error: 'no second modal'};
                    const cards = second.querySelectorAll('.lv-store-card-detailed');
                    return {
                        visible: second.getBoundingClientRect().width > 0,
                        cards: cards.length,
                        html: second.innerHTML.substring(0, 3000),
                    };
                }
            """)
            print(f"回车搜索结果: cards={result.get('cards')}, visible={result.get('visible')}")

            # 回到第一步
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

        # ================================================================
        # 2. 测试：使用搜索按钮（精确选择器）
        # ================================================================
        print("\n" + "=" * 60)
        print("测试2: 使用搜索按钮提交")

        search_input2 = page.locator('#address-search-input')
        if await search_input2.count() > 0:
            await search_input2.first.click(force=True, timeout=3000)
            await asyncio.sleep(0.5)
            await search_input2.first.fill('')
            await asyncio.sleep(0.3)
            await search_input2.first.evaluate("el => { el.value = ''; el.dispatchEvent(new Event('input', {bubbles: true})); }")
            await asyncio.sleep(0.5)
            await search_input2.first.type("大阪", delay=100)
            print("已输入「大阪」")
            await asyncio.sleep(3)

            # 在弹窗内查找搜索按钮
            search_btn = page.locator('.lv-modal__content .lv-address-search-form__button, #modalContent .lv-address-search-form__button')
            btn_count = await search_btn.count()
            print(f"弹窗内搜索按钮数量: {btn_count}")

            if btn_count > 0:
                await search_btn.first.click(force=True, timeout=3000)
                print("已点击弹窗内搜索按钮")
                await asyncio.sleep(5)

                result2 = await page.evaluate("""
                    () => {
                        const second = document.querySelector('.lv-locate-in-store__second-step-modal');
                        if (!second) return {error: 'no second modal'};
                        const cards = second.querySelectorAll('.lv-store-card-detailed');
                        const noResult = second.querySelector('[class*="no-result"], [class*="empty"], [class*="no-store"]');
                        return {
                            visible: second.getBoundingClientRect().width > 0,
                            cards: cards.length,
                            noResult: noResult ? noResult.innerText.substring(0, 200) : null,
                            html: second.innerHTML.substring(0, 3000),
                        };
                    }
                """)
                print(f"搜索按钮结果: cards={result2.get('cards')}, noResult={result2.get('noResult')}")
                print(f"HTML片段: {result2.get('html', '')[:1500]}")

        # ================================================================
        # 3. 测试：检查 Vue 组件状态
        # ================================================================
        print("\n" + "=" * 60)
        print("测试3: 检查 Vue 数据状态")

        vue_state = await page.evaluate("""
            () => {
                const result = {};
                const app = document.querySelector('#app');
                if (app && app.__vue_app__) {
                    result.hasVueApp = true;
                }

                // 查找所有 input 元素的状态
                const inputs = document.querySelectorAll('#address-search-input');
                result.inputs = [];
                for (const inp of inputs) {
                    result.inputs.push({
                        value: inp.value,
                        id: inp.id,
                        rect: {
                            x: inp.getBoundingClientRect().x,
                            y: inp.getBoundingClientRect().y,
                            w: inp.getBoundingClientRect().width,
                            h: inp.getBoundingClientRect().height,
                        },
                    });
                }

                // 检查搜索表单
                const form = document.querySelector('.lv-address-search-form__form');
                if (form) {
                    result.formAction = form.getAttribute('action') || 'none';
                    result.formMethod = form.getAttribute('method') || 'none';
                }

                return result;
            }
        """)
        print(f"Vue状态: {json.dumps(vue_state, indent=2, ensure_ascii=False)[:2000]}")

        # ================================================================
        # 4. 截图
        # ================================================================
        try:
            await page.screenshot(path="/tmp/lv_diag_network.png", full_page=False)
            print("\n截图已保存: /tmp/lv_diag_network.png")
        except Exception as e:
            print(f"截图失败: {e}")

        await browser.close()
        print("\n诊断完成")


if __name__ == "__main__":
    asyncio.run(diagnose())