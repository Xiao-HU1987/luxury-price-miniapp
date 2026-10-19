"""聚焦：dump 库存弹窗完整DOM，确认尺寸选择器与地址输入框的真实结构。

用法：cd server && env -u HTTP_PROXY -u HTTPS_PROXY -u http_proxy -u https_proxy -u ALL_PROXY -u all_proxy \
        venv/bin/python3.11 -m crawler.lv_diag_modal4 "https://jp.louisvuitton.com/jpn-jp/products/-/M29195"
"""
import asyncio
import os
import sys
from pathlib import Path

for v in ("http_proxy", "https_proxy", "HTTP_PROXY", "HTTPS_PROXY",
          "all_proxy", "ALL_PROXY"):
    os.environ.pop(v, None)

from playwright.async_api import async_playwright

PANEL_TEXT = "ストアの在庫状況を確認する"
OUT_DIR = Path("/tmp/lv_diag_out")
OUT_DIR.mkdir(exist_ok=True)


async def open_modal(page):
    panel = page.locator(f".lv-expandable-panel:has-text('{PANEL_TEXT}')")
    if await panel.count() > 0:
        try:
            await panel.first.scroll_into_view_if_needed(timeout=8000)
            await asyncio.sleep(1)
        except Exception:
            pass
        eb = panel.first.locator("button[aria-expanded]")
        if await eb.count() > 0 and await eb.first.get_attribute("aria-expanded") != "true":
            await eb.first.click(timeout=5000)
        await asyncio.sleep(2)
    lb = page.locator(".lv-product-locate-in-store__container")
    if await lb.count() > 0:
        try:
            await lb.first.scroll_into_view_if_needed(timeout=8000)
            await asyncio.sleep(0.8)
            await lb.first.click(timeout=5000)
        except Exception as e:
            print(f"打开弹窗失败: {e}")
    await asyncio.sleep(5)


async def main():
    url = sys.argv[1] if len(sys.argv) > 1 else "https://jp.louisvuitton.com/jpn-jp/products/-/M29195"
    async with async_playwright() as pw:
        browser = await pw.chromium.connect_over_cdp("http://127.0.0.1:9333")
        ctx = browser.contexts[0] if browser.contexts else await browser.new_context()
        page = await ctx.new_page()
        await page.set_viewport_size({"width": 1440, "height": 900})

        print(f"=== 导航: {url} ===")
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=45000)
        except Exception as e:
            print(f"导航异常: {str(e).splitlines()[0]}")
        await asyncio.sleep(8)
        await open_modal(page)
        await asyncio.sleep(2)

        # 1) 完整转储弹窗DOM（用 -sidepanel.lv-locate-in-store 做 root）
        html = await page.evaluate("""
            () => {
                const m = document.querySelector('.-sidepanel.lv-locate-in-store');
                return m ? m.outerHTML : 'NO_MODAL';
            }
        """)
        OUT_DIR.joinpath("modal4_sidepanel.html").write_text(html, encoding="utf-8")
        print(f"\n=== 弹窗 outerHTML 长度: {len(html)} ===")
        print("已保存到 /tmp/lv_diag_out/modal4_sidepanel.html")

        # 2) dump 弹窗(用正确root)内所有可见表单元素
        print("\n=== 弹窗内所有可见表单元素 ===")
        els = await page.evaluate(r"""() => {
            const m = document.querySelector('.-sidepanel.lv-locate-in-store');
            const root = m || document;
            const out = [];
            const tags = 'button,input,select,a,[role="button"],[role="combobox"],[role="listbox"],[role="option"]'.split(',');
            for (const tg of tags) {
                for (const el of root.querySelectorAll(tg)) {
                    const rect = el.getBoundingClientRect();
                    if (rect.width <= 0 || rect.height <= 0) continue;
                    out.push({
                        tag: el.tagName, id: el.id||'', type: el.getAttribute('type')||'',
                        ph: el.getAttribute('placeholder')||'',
                        text: (el.innerText || el.value || '').trim().replace(/\s+/g,' ').substring(0, 60),
                        cls: (typeof el.className==='string'?el.className:el.getAttribute('class')||'').substring(0, 80),
                        disabled: el.disabled ? true : false, aria: el.getAttribute('aria-expanded')||'',
                    });
                }
            }
            return out;
        }""")
        for e in els:
            print(f"  <{e['tag']} id={e['id']} type={e['type']} ph='{e['ph']}' dis={e['disabled']} aria={e['aria']} class={e['cls']}> {e['text']}")

        # 3) 检查尺寸区域：dump 所有含"サイズ"的可见容器 HTML
        print("\n=== 尺寸区域容器 ===")
        size_area = await page.evaluate("""
            () => {
                const m = document.querySelector('.-sidepanel.lv-locate-in-store');
                const root = m || document;
                const out = [];
                const els = root.querySelectorAll('[class*="size"], [class*="model"], [class*="displayed"], select, #displayedModelList');
                for (const el of els) {
                    const rect = el.getBoundingClientRect();
                    if (rect.width<=0||rect.height<=0) continue;
                    out.push({
                        tag: el.tagName, id: el.id||'',
                        cls: (typeof el.className==='string'?el.className:el.getAttribute('class')||'').substring(0,80),
                        html: el.outerHTML.substring(0, 400),
                    });
                }
                return out;
            }
        """)
        for s in size_area:
            print(f"  <{s['tag']} id={s['id']} class={s['cls']}>\n      {s['html']}")

        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())