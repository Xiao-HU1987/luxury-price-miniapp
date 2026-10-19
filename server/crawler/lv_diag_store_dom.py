"""诊断：转储库存弹窗完整DOM，理解可用的搜索交互方式。

用法：
  cd server
  venv/bin/python3.11 -m crawler.lv_diag_store_dom <SKU或URL>
"""
import asyncio
import os
import sys

for v in ("http_proxy", "https_proxy", "HTTP_PROXY", "HTTPS_PROXY",
          "all_proxy", "ALL_PROXY"):
    os.environ.pop(v, None)

from playwright.async_api import async_playwright


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
        await page.evaluate(r"""() => {
            const panels = document.querySelectorAll('.lv-expandable-panel');
            for (const p of panels) {
                if ((p.innerText||'').includes('ストアの在庫状況を確認する')) {
                    const btn = p.querySelector('button[aria-expanded]');
                    if (btn) { btn.setAttribute('aria-expanded','true'); btn.setAttribute('aria-disabled','false'); btn.click(); }
                    const content = p.querySelector('.lv-expandable-panel__content');
                    if (content) { content.style.display='block'; content.setAttribute('aria-hidden','false'); }
                }
            }
        }""")
        await asyncio.sleep(3)
        await page.evaluate(r"""() => {
            const btn = document.querySelector('.lv-product-locate-in-store__container');
            if (btn) btn.click();
        }""")
        await asyncio.sleep(5)

        # 转储弹窗完整 HTML
        html = await page.evaluate(r"""() => {
            const modal = document.querySelector('.lv-locate-in-store, .lv-modal__container, .lv-modal__content');
            if (!modal) return 'NO_MODAL';
            return modal.outerHTML;
        }""")
        print("\n=== 弹窗完整 HTML ===\n")
        print(html[:8000])

        # 转储所有可见元素（按钮、输入框、链接）
        print("\n=== 弹窗内所有可见按钮/输入/链接 ===")
        els = await page.evaluate(r"""() => {
            const modal = document.querySelector('.lv-locate-in-store, .lv-modal__container, .lv-modal__content');
            if (!modal) return [];
            const out = [];
            const tags = 'button,input,select,a,textarea,[role="option"],[role="button"]'.split(',');
            for (const tag of tags) {
                const els = modal.querySelectorAll(tag);
                for (const el of els) {
                    const rect = el.getBoundingClientRect();
                    if (rect.width>0 && rect.height>0) {
                        out.push({
                            tag: el.tagName,
                            type: el.getAttribute('type')||'',
                            text: (el.innerText||el.value||el.getAttribute('placeholder')||'').trim().substring(0,60),
                            cls: (el.className||'').substring(0,60),
                        });
                    }
                }
            }
            return out;
        }""")
        for e in els:
            print(f"  <{e['tag']} type={e['type']} class={e['cls']}> {e['text']}")

        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())