"""诊断：检查库存弹窗中门店搜索结果 DOM，确认为何提取到0家门店。

用法：
  cd server
  venv/bin/python3.11 -m crawler.lv_diag_check_storecloud
"""
import asyncio
import os

for v in ("http_proxy", "https_proxy", "HTTP_PROXY", "HTTPS_PROXY",
          "all_proxy", "ALL_PROXY"):
    os.environ.pop(v, None)

from playwright.async_api import async_playwright


async def dump_state(page, label):
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
            '.lv-address-search-form__input',
            '.lv-address-search-form__button',
            '.lv-store-geolocation__get-button',
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
                    });
                }
                result[sel] = { count: els.length, items: info.slice(0, 3) };
            }
        }
        const modal = document.querySelector('.lv-locate-in-store__first-step-modal, .lv-locate-in-store__second-step-modal');
        if (modal) result.modalText = (modal.innerText || '').substring(0, 600);
        return result;
    }""")
    print(f"\n===== {label} =====")
    for sel, info in state.items():
        if sel == 'modalText':
            print(f"modalText:\n{info[:500]}")
            continue
        print(f"{sel} (count={info['count']}):")
        for i, item in enumerate(info["items"]):
            print(f"  [{i}] visible={item['visible']} w={item['w']} h={item['h']} class={item.get('classes','')}")
            if item.get('text'): print(f"      text: {item['text'][:120]}")


async def main():
    async with async_playwright() as pw:
        browser = await pw.chromium.connect_over_cdp("http://127.0.0.1:9333")
        ctx = browser.contexts[0] if browser.contexts else await browser.new_context()
        page = ctx.pages[0] if ctx.pages else await ctx.new_page()
        print(f"当前URL: {page.url}")

        await dump_state(page, "当前状态")

        # 尝试点击地理按钮或检查弹窗
        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())