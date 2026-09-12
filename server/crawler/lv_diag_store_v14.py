"""方案A v14：提交后转储整个弹窗 DOM + console 错误 + click事件追踪。

用法：venv/bin/python3.11 -m crawler.lv_diag_store_v14 <URL> <城市>
"""
import asyncio
import os
import sys
from pathlib import Path

for v in ("http_proxy", "https_proxy", "HTTP_PROXY", "HTTPS_PROXY",
          "all_proxy", "ALL_PROXY"):
    os.environ.pop(v, None)

from playwright.async_api import async_playwright

OUT_DIR = Path("/tmp/lv_diag_out")
OUT_DIR.mkdir(exist_ok=True)
CONSOLE = []


async def open_modal(page):
    await page.evaluate(r"""
        () => {
            const panels = document.querySelectorAll('.lv-expandable-panel');
            for (const p of panels) {
                if ((p.innerText||'').includes('ストアの在庫状況を確認する')) {
                    const btn = p.querySelector('button[aria-expanded]');
                    if (btn && btn.getAttribute('aria-expanded') !== 'true') btn.click();
                    break;
                }
            }
        }
    """)
    await asyncio.sleep(2)
    await page.evaluate(r"""
        () => {
            const btn = document.querySelector('.lv-product-locate-in-store__container');
            if (btn) btn.click();
        }
    """)
    await asyncio.sleep(5)


async def select_size(page):
    size_sel = page.locator("#displayedModelList")
    if await size_sel.count() > 0:
        opts = await size_sel.locator("option").all_inner_texts()
        real = [o.strip() for o in opts if "サイズを選んで" not in o]
        if real:
            await size_sel.select_option(label=real[0])
            await asyncio.sleep(2)


async def main():
    url = sys.argv[1] if len(sys.argv) > 1 else "https://jp.louisvuitton.com/jpn-jp/products/-/M29195"
    city = sys.argv[2] if len(sys.argv) > 2 else "東京"
    async with async_playwright() as pw:
        browser = await pw.chromium.connect_over_cdp("http://127.0.0.1:9333")
        ctx = browser.contexts[0] if browser.contexts else await browser.new_context()
        page = await ctx.new_page()
        await page.set_viewport_size({"width": 1440, "height": 900})

        page.on("console", lambda m: CONSOLE.append(f"[{m.type}] {m.text[:200]}"))
        page.on("pageerror", lambda e: CONSOLE.append(f"[PAGEERROR] {str(e)[:300]}"))

        print(f"=== 导航: {url} ===")
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=45000)
        except Exception as e:
            print(f"导航异常: {str(e).split(chr(10))[0]}")
        await asyncio.sleep(8)
        await open_modal(page)
        await select_size(page)

        inp = page.locator("#address-search-input")
        if await inp.count() == 0:
            print("未找到地址输入框"); await browser.close(); return
        try:
            await inp.click(timeout=3000)
        except Exception:
            await inp.click(force=True, timeout=3000)
        await page.keyboard.type(city, delay=120)
        await asyncio.sleep(4)

        submit = page.locator(".lv-modal__footer button")
        dis = await submit.first.get_attribute("disabled") if await submit.count() > 0 else "NONE"
        print(f"提交按钮 disabled={dis}")
        if await submit.count() > 0:
            try:
                await submit.first.click(timeout=5000)
                print("已点击提交")
            except Exception as e:
                print(f"点击提交异常: {str(e).split(chr(10))[0]}")
        await asyncio.sleep(6)

        # 转储整个弹窗区域 outerHTML
        modal = await page.evaluate("""
            () => {
                const m = document.querySelector('.lv-locate-in-store');
                if (!m) return 'NO_MODAL';
                // 只取弹窗内容（去掉script/style）
                const clone = m.cloneNode(true);
                clone.querySelectorAll('script,style').forEach(e=>e.remove());
                return clone.outerHTML;
            }
        """)
        OUT_DIR.joinpath("v14_modal.html").write_text(modal, encoding="utf-8")
        print(f"弹窗 HTML 已转储 (len={len(modal)})")

        # 弹窗当前可见文本
        txt = await page.evaluate("""
            () => {
                const m = document.querySelector('.lv-locate-in-store');
                return m ? (m.innerText||'').trim().replace(/\\n+/g,' | ').substring(0,500) : 'NO_MODAL';
            }
        """)
        print(f"\n弹窗文本: {txt}")

        # 检查是否有 error/empty 元素
        err = await page.evaluate("""
            () => {
                const m = document.querySelector('.lv-locate-in-store');
                if (!m) return [];
                const out = [];
                const els = m.querySelectorAll('[class*=error], [class*=empty], [class*=no-result], [class*=not-found], [role=alert]');
                for (const el of els) {
                    const r = el.getBoundingClientRect();
                    if (r.width>0) out.push((el.innerText||el.className||'').substring(0,100));
                }
                return out;
            }
        """)
        print(f"错误/空态元素: {err}")

        # console
        print(f"\n=== console ({len(CONSOLE)}) ===")
        for c in CONSOLE[-25:]:
            print(f"  {c}")

        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())