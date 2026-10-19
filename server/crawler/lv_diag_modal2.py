"""诊断v4：检查弹窗完整HTML和empty元素内容。

用法：
  cd server
  venv/bin/python3.11 -m crawler.lv_diag_modal2
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

        # 检查弹窗当前状态
        modal_state = await page.evaluate(r"""() => {
            const result = {};

            // 1. 弹窗完整 HTML
            const modal = document.querySelector('.lv-modal__content, .lv-locate-in-store');
            if (modal) {
                result.modalHTML = modal.innerHTML.substring(0, 5000);
                result.modalText = (modal.innerText || '').substring(0, 1000);
            }

            // 2. empty 元素详情
            const empties = document.querySelectorAll('[class*="empty"]');
            result.empties = [];
            for (const el of empties) {
                const rect = el.getBoundingClientRect();
                result.empties.push({
                    visible: rect.width > 0 && rect.height > 0,
                    w: Math.round(rect.width), h: Math.round(rect.height),
                    classes: el.className,
                    text: (el.innerText || '').substring(0, 200),
                    html: el.innerHTML.substring(0, 500),
                    tag: el.tagName,
                });
            }

            // 3. first-step-modal 完整结构
            const first = document.querySelector('.lv-locate-in-store__first-step-modal');
            if (first) {
                result.firstHTML = first.innerHTML.substring(0, 3000);
            }

            // 4. 检查地理位置权限状态
            result.geoPermission = navigator.permissions ? 'supported' : 'not_supported';

            return result;
        }""")

        print("\n=== 弹窗文本 ===")
        print(modal_state.get("modalText", ""))

        print("\n=== empty 元素 ===")
        for i, e in enumerate(modal_state.get("empties", [])):
            print(f"\n[{i}] tag={e['tag']} visible={e['visible']} classes={e['classes']}")
            print(f"    text: {e['text']}")
            print(f"    html: {e['html'][:300]}")

        print("\n=== first-step-modal HTML ===")
        print(modal_state.get("firstHTML", "")[:2000])

        print("\n=== 弹窗完整 HTML ===")
        print(modal_state.get("modalHTML", "")[:3000])

        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
