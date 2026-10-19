"""
诊断脚本：尝试触发 Vue 组件内部方法 + 模拟真实键盘输入
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

        # 确保弹窗打开
        modal_state = await page.evaluate("""
            () => document.querySelector('.lv-locate-in-store__first-step-modal')?.getBoundingClientRect().width > 0
        """)
        if not modal_state:
            locate_btn = page.locator('.lv-product-locate-in-store__container')
            if await locate_btn.count() > 0:
                await locate_btn.first.click(force=True, timeout=5000)
                await asyncio.sleep(4)
                print("弹窗已打开")

        # ================================================================
        # 测试1: 使用 page.keyboard.type() 模拟键盘输入
        # ================================================================
        print("\n" + "=" * 60)
        print("测试1: page.keyboard.type() 模拟键盘输入")

        search_input = page.locator('#address-search-input')
        if await search_input.count() > 0:
            # 先聚焦输入框
            await search_input.first.click(force=True, timeout=3000)
            await asyncio.sleep(0.5)

            # 全选并删除
            await page.keyboard.press("Meta+A")
            await asyncio.sleep(0.2)
            await page.keyboard.press("Backspace")
            await asyncio.sleep(0.3)

            # 使用 page.keyboard.type 输入
            await page.keyboard.type("東京", delay=80)
            print("已通过 keyboard.type 输入「東京」")
            await asyncio.sleep(3)

            # 检查自动补全
            suggestions = await page.evaluate("""
                () => {
                    const result = [];
                    const all = document.querySelectorAll('[role="listbox"], [role="option"], [class*="suggestion"], [class*="autocomplete"], [class*="dropdown"], ul');
                    for (const el of all) {
                        const rect = el.getBoundingClientRect();
                        if (rect.width > 0 && rect.height > 0) {
                            result.push({
                                tag: el.tagName,
                                className: (el.className || '').substring(0, 80),
                                text: (el.innerText || '').substring(0, 200),
                            });
                        }
                    }
                    return result;
                }
            """)
            print(f"自动补全: {json.dumps(suggestions, indent=2, ensure_ascii=False)[:2000]}")

            # 按 Enter 提交
            await page.keyboard.press("Enter")
            await asyncio.sleep(5)

            result = await page.evaluate("""
                () => {
                    const second = document.querySelector('.lv-locate-in-store__second-step-modal');
                    return {
                        secondExists: !!second,
                        visible: second ? second.getBoundingClientRect().width > 0 : false,
                        cards: second ? second.querySelectorAll('.lv-store-card-detailed').length : 0,
                        html: second ? second.innerHTML.substring(0, 1000) : '',
                    };
                }
            """)
            print(f"keyboard.type 结果: {json.dumps(result, indent=2, ensure_ascii=False)[:1500]}")

        # ================================================================
        # 测试2: 检查 Vue 组件实例并尝试调用方法
        # ================================================================
        print("\n" + "=" * 60)
        print("测试2: 遍历 Vue 组件树查找搜索组件")

        vue_info = await page.evaluate("""
            () => {
                const result = {};

                // 遍历所有元素查找 __vue_app__
                const appEl = document.querySelector('#app');
                if (!appEl || !appEl.__vue_app__) {
                    result.error = 'no vue app';
                    return result;
                }

                const app = appEl.__vue_app__;
                result.appExists = true;

                // 递归查找组件
                function findComponent(instance, depth = 0) {
                    if (depth > 10) return null;
                    if (!instance) return null;

                    const type = instance.type;
                    const name = type?.name || type?.__name || '';

                    // 检查是否是地址搜索组件
                    if (name && (name.includes('address') || name.includes('store') || name.includes('locat') || name.includes('search'))) {
                        return {
                            name,
                            depth,
                            setup: !!instance.setupState,
                            props: Object.keys(instance.props || {}),
                            data: Object.keys(instance.setupState || {}).slice(0, 20),
                        };
                    }

                    // 检查子组件
                    if (instance.subTree?.component) {
                        const found = findComponent(instance.subTree.component, depth + 1);
                        if (found) return found;
                    }

                    return null;
                }

                const root = app._instance;
                if (root) {
                    result.rootName = root.type?.name || root.type?.__name || 'unknown';
                    const found = findComponent(root);
                    if (found) result.foundComponent = found;
                }

                return result;
            }
        """)
        print(f"Vue 组件: {json.dumps(vue_info, indent=2, ensure_ascii=False)[:3000]}")

        # ================================================================
        # 测试3: 直接修改输入值并触发 Vue 的 input 事件
        # ================================================================
        print("\n" + "=" * 60)
        print("测试3: 使用原生 setter + composition events")

        comp_result = await page.evaluate("""
            async () => {
                const input = document.querySelector('#address-search-input');
                if (!input) return {error: 'no input'};

                // 方法1: 使用原生 value setter
                const nativeSetter = Object.getOwnPropertyDescriptor(
                    window.HTMLInputElement.prototype, 'value'
                ).set;
                nativeSetter.call(input, '大阪');

                // 触发 composition events（用于日文输入法）
                input.dispatchEvent(new CompositionEvent('compositionstart', { bubbles: true, data: '大' }));
                input.dispatchEvent(new CompositionEvent('compositionupdate', { bubbles: true, data: '大阪' }));
                input.dispatchEvent(new CompositionEvent('compositionend', { bubbles: true, data: '大阪' }));

                // 触发 input + change
                input.dispatchEvent(new Event('input', { bubbles: true }));
                input.dispatchEvent(new Event('change', { bubbles: true }));

                await new Promise(r => setTimeout(r, 3000));

                // 检查自动补全
                const suggestions = [];
                const all = document.querySelectorAll('[role="listbox"], [role="option"], [class*="suggestion"]');
                for (const el of all) {
                    if (el.getBoundingClientRect().width > 0) {
                        suggestions.push(el.innerText.substring(0, 100));
                    }
                }

                return {
                    inputValue: input.value,
                    suggestions,
                };
            }
        """)
        print(f"Composition events 结果: {json.dumps(comp_result, indent=2, ensure_ascii=False)[:2000]}")

        # ================================================================
        # 测试4: 监控网络请求，点击「現在地で検索」
        # ================================================================
        print("\n" + "=" * 60)
        print("测试4: 监控网络 + 点击「現在地で検索」")

        captured = []

        async def on_request(req):
            if any(k in req.url for k in ['store', 'query', 'availability', 'locate']):
                captured.append({'url': req.url[:200], 'method': req.method})

        async def on_response(resp):
            if any(k in resp.url for k in ['store', 'query', 'availability', 'locate']):
                try:
                    body = await resp.body()
                    captured.append({'url': resp.url[:200], 'status': resp.status, 'body': body[:500].decode('utf-8', errors='replace')})
                except:
                    pass

        page.on('request', on_request)
        page.on('response', on_response)

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

        # 设置地理位置
        try:
            await ctx.grant_permissions(['geolocation'])
            await ctx.set_geolocation({"latitude": 35.6762, "longitude": 139.6503})
        except:
            pass

        # 点击「現在地で検索」
        geo_btn = page.locator('button:has-text("現在地で検索"), .lv-store-geolocation__get-button')
        if await geo_btn.count() > 0:
            print("点击「現在地で検索」...")
            await geo_btn.first.click(force=True, timeout=5000)
            await asyncio.sleep(8)

        print(f"捕获的请求/响应 ({len(captured)}):")
        for c in captured:
            print(f"  {json.dumps(c, ensure_ascii=False)[:500]}")

        # 截图
        try:
            await page.screenshot(path="/tmp/lv_diag_keyboard.png", full_page=False)
            print("\n截图已保存: /tmp/lv_diag_keyboard.png")
        except Exception as e:
            print(f"截图失败: {e}")

        await browser.close()
        print("\n诊断完成")


if __name__ == "__main__":
    asyncio.run(diagnose())