"""方案A v10：在页面内 hook fetch/XHR，并搜索地址补全机制。

在当前页面注入 fetch/XHR hook，输入城市，捕获所有网络请求（含补全API）。
同时检查 window 上与 store 搜索相关的函数/数据。

用法：venv/bin/python3.11 -m crawler.lv_diag_store_v10 <URL> <城市>
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
HOOKED = []


async def hook_network(page):
    """注入 fetch/XHR hook，捕获所有请求。"""
    await page.add_init_script(r"""
        (() => {
            if (window.__hooked) return;
            window.__hooked = true;
            window.__reqs = [];
            const record = (url, method, status, body) => {
                window.__reqs.push({url, method, status, body: body||''});
            };
            const of = window.fetch;
            window.fetch = function(...args) {
                const url = args[0] && (args[0].url || args[0]) || '';
                return of.apply(this, args).then(res => {
                    const ct = res.headers && res.headers.get('content-type') || '';
                    if (ct.includes('json')) {
                        return res.clone().text().then(body => {
                            record(String(url), 'FETCH', res.status, body.substring(0,2000));
                            return res;
                        });
                    }
                    record(String(url), 'FETCH', res.status, '');
                    return res;
                }).catch(e => { record(String(url),'FETCH','ERR',String(e)); throw e; });
            };
            const ox = XMLHttpRequest.prototype.open;
            XMLHttpRequest.prototype.open = function(method, url, ...rest) {
                this.__url = url; this.__method = method;
                this.addEventListener('load', function() {
                    record(String(this.__url), this.__method, this.status,
                           (this.responseText||'').substring(0,2000));
                });
                return ox.apply(this, arguments);
            };
        })();
    """)


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


async def main():
    url = sys.argv[1] if len(sys.argv) > 1 else "https://jp.louisvuitton.com/jpn-jp/products/-/M29195"
    city = sys.argv[2] if len(sys.argv) > 2 else "東京都"
    async with async_playwright() as pw:
        browser = await pw.chromium.connect_over_cdp("http://127.0.0.1:9333")
        ctx = browser.contexts[0] if browser.contexts else await browser.new_context()
        page = await ctx.new_page()
        await page.set_viewport_size({"width": 1440, "height": 900})
        await hook_network(page)

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

        print(f"\n=== 输入: {city} ===")
        await page.keyboard.type(city, delay=150)
        await asyncio.sleep(6)

        # 也点击搜索按钮（address-search-form 内的按钮）
        search_btn = page.locator(".lv-address-search-form__button")
        if await search_btn.count() > 0:
            dis = await search_btn.first.get_attribute("disabled")
            print(f"搜索按钮 disabled={dis}")

        reqs = await page.evaluate("window.__reqs || []")
        print(f"\n=== 捕获到 {len(reqs)} 个请求 ===")
        for r in reqs:
            print(f"  [{r['method']} {r['status']}] {r['url'][:190]}")
            if r["body"]:
                print(f"      BODY: {r['body'][:400]}")

        # 检查页面是否有 store 相关全局数据
        glob = await page.evaluate("""
            () => {
                const out = [];
                for (const k of Object.keys(window)) {
                    if (k.toLowerCase().includes('store') || k.toLowerCase().includes('geo') ||
                        k.toLowerCase().includes('address') || k.toLowerCase().includes('locat')) {
                        out.push(k);
                    }
                }
                return out;
            }
        """)
        print(f"\nwindow store 相关全局: {glob}")

        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())