"""方案A v8：用原生 setter + dispatch input 事件触发 Vue 地址补全。

Vue 的 v-model 监听 input/change 事件，Playwright 的 .type() 有时不触发
合成事件。本脚本用原生方式设置 input value 并派发事件，测试地址补全。

用法：venv/bin/python3.11 -m crawler.lv_diag_store_v8 <URL> <城市>
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
REQUESTS = []


async def setup_network(page):
    async def on_resp(resp):
        url = resp.url
        if not any(k in url for k in ("louisvuitton.com", "api.louisvuitton.com")):
            return
        body = ""
        try:
            ct = resp.headers.get("content-type", "")
        except Exception:
            ct = ""
        if "json" in ct.lower():
            try:
                body = (await resp.text())[:2000]
            except Exception:
                body = ""
        REQUESTS.append({"url": url[:200], "status": resp.status, "ct": ct[:40], "body": body})
    page.on("response", on_resp)


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


async def select_size(page):
    size_sel = page.locator("#displayedModelList")
    if await size_sel.count() > 0:
        opts = await size_sel.locator("option").all_inner_texts()
        real = [o.strip() for o in opts if "サイズを選んで" not in o]
        if real:
            await size_sel.select_option(label=real[0])
            await asyncio.sleep(2)


async def set_input_native(page, value):
    """原生 setter + dispatch input/change 事件，触发 Vue v-model。"""
    await page.evaluate("""(val) => {
        const inp = document.getElementById('address-search-input');
        if (!inp) return false;
        const setter = Object.getOwnPropertyDescriptor(
            HTMLInputElement.prototype, 'value').set;
        setter.call(inp, val);
        inp.dispatchEvent(new Event('input', { bubbles: true }));
        inp.dispatchEvent(new Event('change', { bubbles: true }));
        inp.dispatchEvent(new Event('keyup', { bubbles: true }));
        return true;
    }""", value)


async def dump_suggestions(page, label):
    sugg = await page.evaluate("""
        () => {
            const out = [];
            const all = document.querySelectorAll('li, [role=option], [role=listbox] *, [class*=suggest], [class*=autocompl], [class*=dropdown], [class*=result], [class*=listbox], [class*=address]');
            for (const el of all) {
                const r = el.getBoundingClientRect();
                const t = (el.innerText||el.textContent||'').trim();
                if (r.width>0 && r.height>0 && t && t.length<120 && !t.includes('ストア検索')) {
                    out.push(t.substring(0,100));
                }
            }
            return [...new Set(out)].slice(0,25);
        }
    """)
    print(f"[{label}] 可见补全元素({len(sugg)}):")
    for s in sugg[:15]:
        print(f"   - {s}")
    return sugg


async def main():
    url = sys.argv[1] if len(sys.argv) > 1 else "https://jp.louisvuitton.com/jpn-jp/products/-/M29195"
    city = sys.argv[2] if len(sys.argv) > 2 else "東京都"
    async with async_playwright() as pw:
        browser = await pw.chromium.connect_over_cdp("http://127.0.0.1:9333")
        ctx = browser.contexts[0] if browser.contexts else await browser.new_context()
        page = await ctx.new_page()
        await page.set_viewport_size({"width": 1440, "height": 900})
        await setup_network(page)

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
        await inp.click(timeout=5000)

        print(f"\n=== 原生 setter 输入: {city} ===")
        REQUESTS.clear()
        await set_input_native(page, city)
        await asyncio.sleep(5)
        print(f"网络请求: {len(REQUESTS)}")
        for r in REQUESTS:
            print(f"  [RESP {r['status']}] {r['ct']} {r['url']}")
            if r["body"]:
                print(f"      BODY: {r['body'][:400]}")
        await dump_suggestions(page, "原生输入后")

        # 输入框实际值
        val = await inp.input_value()
        print(f"输入框当前值: '{val}'")

        # 提交按钮状态
        submit = page.locator(".lv-modal__footer button")
        if await submit.count() > 0:
            print(f"提交按钮 disabled={await submit.first.get_attribute('disabled')}")

        # 转储 DOM
        html = await page.evaluate("document.documentElement.outerHTML")
        OUT_DIR.joinpath("v8_native.html").write_text(html, encoding="utf-8")
        print("\n已转储 v8_native.html")

        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())