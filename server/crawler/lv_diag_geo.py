"""诊断脚本：测试地理位置搜索后的弹窗状态。

用法：
  cd server
  venv/bin/python3.11 -m crawler.lv_diag_geo
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

        # 授权地理位置 + 设置东京坐标
        try:
            await context.grant_permissions(['geolocation'])
            await context.set_geolocation({"latitude": 35.6762, "longitude": 139.6503})
            print("已设置地理位置: 东京 (35.6762, 139.6503)")
        except Exception as e:
            print(f"地理位置设置失败: {e}")

        # 检查弹窗当前状态
        before = await page.evaluate(r"""() => {
            const first = document.querySelector('.lv-locate-in-store__first-step-modal');
            const second = document.querySelector('.lv-locate-in-store__second-step-modal');
            const geoBtn = document.querySelector('.lv-store-geolocation__get-button');
            const searchBtn = document.querySelector('.lv-address-search-form__button');
            const input = document.querySelector('.lv-address-search-form__input');
            return {
                firstVisible: first ? first.getBoundingClientRect().width > 0 : false,
                secondExists: !!second,
                secondVisible: second ? second.getBoundingClientRect().width > 0 : false,
                geoBtnVisible: geoBtn ? geoBtn.getBoundingClientRect().width > 0 : false,
                geoBtnDisabled: geoBtn ? geoBtn.hasAttribute('disabled') : null,
                searchBtnDisabled: searchBtn ? searchBtn.hasAttribute('disabled') : null,
                inputValue: input ? input.value : '',
            };
        }""")
        print(f"\n点击前状态: {before}")

        if not before.get("firstVisible"):
            print("弹窗未打开，请先运行 lv_diag_modal 打开弹窗")
            await browser.close()
            return

        # 点击「現在地で検索」按钮
        print("\n=== 点击「現在地で検索」按钮 ===")
        try:
            geo_btn = page.locator('.lv-store-geolocation__get-button')
            if await geo_btn.count() > 0:
                await geo_btn.first.click(timeout=5000)
                print("已点击 .lv-store-geolocation__get-button")
        except Exception as e:
            print(f"Playwright click 失败: {e}")

        # 渐进式等待，每2秒检查一次弹窗状态
        for wait_s in [2, 3, 5, 5, 5]:
            await page.wait_for_timeout(wait_s * 1000)
            state = await page.evaluate(r"""() => {
                const result = {};
                // 检查所有可能的结果容器
                const sels = [
                    '.lv-locate-in-store__first-step-modal',
                    '.lv-locate-in-store__second-step-modal',
                    '.lv-store-card-detailed',
                    '.lv-store-card',
                    '[class*="store-card"]',
                    '[class*="no-result"]',
                    '[class*="empty"]',
                    '[class*="not-found"]',
                    '.lv-address-search-form__suggestion',
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
                // 弹窗内所有可见文本
                const modal = document.querySelector('.lv-modal__content, .lv-locate-in-store');
                if (modal) {
                    result.modalText = (modal.innerText || '').substring(0, 500);
                }
                return result;
            }""")
            print(f"\n--- 等待 {wait_s}s 后状态 ---")
            for sel, info in state.items():
                if sel == 'modalText':
                    print(f"modalText: {info[:200]}")
                    continue
                print(f"{sel} (count={info['count']}):")
                for i, item in enumerate(info["items"]):
                    print(f"  [{i}] visible={item['visible']} w={item['w']} h={item['h']} text={item.get('text','')[:80]}")

            # 如果出现门店卡片或无结果提示，停止等待
            if any(k in state for k in ['.lv-store-card-detailed', '.lv-store-card']):
                print("发现门店卡片，停止等待")
                break
            if state.get('.lv-locate-in-store__second-step-modal', {}).get('items', [{}])[0].get('visible'):
                print("第二步弹窗已可见，停止等待")
                break

        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
