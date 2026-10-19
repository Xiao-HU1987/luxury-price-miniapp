"""完整诊断v3：强制展开面板 + 测试搜索。

用法：
  cd server
  venv/bin/python3.11 -m crawler.lv_diag_full
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

        # 等待价格元素出现（比面板文本更可靠）
        print("等待价格元素出现...")
        try:
            await page.wait_for_function(
                """() => {
                    const els = document.querySelectorAll('.lv-price .notranslate, .lv-price, [itemprop="price"]');
                    for (const el of els) {
                        const t = (el.innerText || el.textContent || '').trim();
                        if (t && /[0-9]/.test(t)) return true;
                    }
                    return false;
                }""",
                timeout=30_000,
            )
            print("价格元素已出现")
        except Exception as e:
            print(f"等待价格元素超时: {e}")

        # 等待页面完全加载（networkidle）
        print("等待 networkidle...")
        try:
            await page.wait_for_load_state("networkidle", timeout=30_000)
            print("networkidle 已达到")
        except Exception as e:
            print(f"networkidle 超时: {e}")

        # 额外等待
        await page.wait_for_timeout(3000)

        # === 1. 用 JS 直接展开面板（强制修改属性）===
        print("\n=== 强制展开面板 ===")
        expand_result = await page.evaluate(r"""() => {
            const panels = document.querySelectorAll('.lv-expandable-panel');
            for (const panel of panels) {
                if ((panel.innerText||'').includes('ストアの在庫状況を確認する')) {
                    const btn = panel.querySelector('button[aria-expanded]');
                    const content = panel.querySelector('.lv-expandable-panel__content');
                    if (btn) {
                        btn.setAttribute('aria-expanded', 'true');
                        btn.setAttribute('aria-disabled', 'false');
                    }
                    if (content) {
                        content.style.display = 'block';
                        content.setAttribute('aria-hidden', 'false');
                    }
                    // 检查库存按钮
                    const locateBtn = panel.querySelector('.lv-product-locate-in-store__container');
                    if (locateBtn) {
                        const rect = locateBtn.getBoundingClientRect();
                        return {
                            ok: true,
                            locateBtnVisible: rect.width > 0 && rect.height > 0,
                            locateBtnW: Math.round(rect.width),
                            locateBtnH: Math.round(rect.height),
                        };
                    }
                    return { ok: true, locateBtnVisible: false };
                }
            }
            return { ok: false };
        }""")
        print(f"强制展开结果: {expand_result}")

        await page.wait_for_timeout(1000)

        # === 2. 点击库存按钮 ===
        print("\n=== 点击库存按钮 ===")
        # 先尝试 Playwright click
        try:
            locate_btn = page.locator('.lv-product-locate-in-store__container')
            if await locate_btn.count() > 0:
                await locate_btn.first.click(timeout=5000, force=True)
                print("Playwright click (force) 成功")
        except Exception as e:
            print(f"Playwright click 失败: {e}")
            # 回退 JS click
            clicked = await page.evaluate(r"""() => {
                const btn = document.querySelector('.lv-product-locate-in-store__container');
                if (btn) {
                    btn.click();
                    return true;
                }
                return false;
            }""")
            print(f"JS click 结果: {clicked}")

        # 等待弹窗加载
        await page.wait_for_timeout(5000)

        # 检查弹窗状态
        modal_check = await page.evaluate(r"""() => {
            const first = document.querySelector('.lv-locate-in-store__first-step-modal');
            const geoBtn = document.querySelector('.lv-store-geolocation__get-button');
            const searchBtn = document.querySelector('.lv-address-search-form__button');
            const input = document.querySelector('.lv-address-search-form__input');
            return {
                firstVisible: first ? first.getBoundingClientRect().width > 0 : false,
                geoBtnVisible: geoBtn ? geoBtn.getBoundingClientRect().width > 0 : false,
                geoBtnDisabled: geoBtn ? geoBtn.hasAttribute('disabled') : null,
                searchBtnVisible: searchBtn ? searchBtn.getBoundingClientRect().width > 0 : false,
                searchBtnDisabled: searchBtn ? searchBtn.hasAttribute('disabled') : null,
                inputVisible: input ? input.getBoundingClientRect().width > 0 : false,
            };
        }""")
        print(f"\n弹窗状态: {modal_check}")

        if not modal_check.get("firstVisible"):
            print("弹窗未打开，终止")
            await browser.close()
            return

        # === 3. 测试地理位置搜索 ===
        print("\n=== 测试地理位置搜索（东京）===")
        try:
            await context.grant_permissions(['geolocation'])
            await context.set_geolocation({"latitude": 35.6762, "longitude": 139.6503})
            print("已设置地理位置: 东京")
        except Exception as e:
            print(f"地理位置设置失败: {e}")

        await page.wait_for_timeout(1000)

        # 点击「現在地で検索」
        try:
            geo_btn = page.locator('.lv-store-geolocation__get-button')
            if await geo_btn.count() > 0:
                disabled = await geo_btn.first.get_attribute('disabled')
                print(f"「現在地で検索」按钮 disabled={disabled}")
                if disabled is None:
                    await geo_btn.first.click(timeout=5000)
                    print("已点击「現在地で検索」")
        except Exception as e:
            print(f"点击失败: {e}")

        # 渐进式检查
        for wait_s in [3, 5, 5, 5, 5, 5]:
            await page.wait_for_timeout(wait_s * 1000)
            state = await page.evaluate(r"""() => {
                const result = {};
                const sels = [
                    '.lv-locate-in-store__first-step-modal',
                    '.lv-locate-in-store__second-step-modal',
                    '.lv-store-card-detailed',
                    '.lv-store-card',
                    '[class*="store-card"]',
                    '[class*="no-result"]',
                    '[class*="empty"]',
                    '[class*="not-found"]',
                    '[class*="suggestion"]',
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
                            if (info.length >= 2) break;
                        }
                        result[sel] = { count: els.length, items: info };
                    }
                }
                const modal = document.querySelector('.lv-modal__content');
                if (modal) result.modalText = (modal.innerText || '').substring(0, 800);
                return result;
            }""")
            print(f"\n--- 等待 {wait_s}s 后 ---")
            for sel, info in state.items():
                if sel == 'modalText':
                    print(f"modalText:\n{info[:500]}")
                    continue
                print(f"{sel} (count={info['count']}):")
                for i, item in enumerate(info["items"]):
                    print(f"  [{i}] visible={item['visible']} w={item['w']} h={item['h']}")
                    if item.get('text'): print(f"      text: {item['text'][:100]}")

            if '.lv-store-card-detailed' in state or '.lv-store-card' in state:
                print("\n✅ 发现门店卡片！")
                break
            if state.get('.lv-locate-in-store__second-step-modal', {}).get('items', [{}])[0].get('visible'):
                print("\n✅ 第二步弹窗已可见！")
                break

        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
