"""方案A v11：完整 hook，过滤门店/库存/位置相关 API，并在输入后点击补全建议。

用法：venv/bin/python3.11 -m crawler.lv_diag_store_v11 <URL> <城市>
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

# 过滤关键词：门店/库存/位置
KEYWORDS = ["store", "point-of-sale", "availability", "inventory", "stock",
            "sku", "locat", "geo", "address", "deal", "near", "poslist",
            "shipment", "quantity", "stockstatus"]


async def hook_network(page):
    await page.add_init_script(r"""
        (() => {
            if (window.__hooked) return;
            window.__hooked = true;
            window.__reqs = [];
            const record = (url, method, status, body) => {
                window.__reqs.push({url: String(url), method, status, body: body||''});
            };
            const of = window.fetch;
            window.fetch = function(...args) {
                const u = args[0] && (args[0].url || args[0]) || '';
                return of.apply(this, args).then(res => {
                    const ct = res.headers && res.headers.get('content-type') || '';
                    if (ct.includes('json')) {
                        return res.clone().text().then(body => {
                            record(u, 'FETCH', res.status, body.substring(0,3000));
                            return res;
                        });
                    }
                    record(u, 'FETCH', res.status, '');
                    return res;
                }).catch(e => { record(u,'FETCH','ERR',String(e)); throw e; });
            };
            const ox = XMLHttpRequest.prototype.open;
            XMLHttpRequest.prototype.open = function(method, url, ...rest) {
                this.__url = url; this.__method = method;
                this.addEventListener('load', function() {
                    record(this.__url, this.__method, this.status,
                           (this.responseText||'').substring(0,3000));
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
        await page.keyboard.type(city, delay=150)
        await asyncio.sleep(6)

        # 尝试点击任何补全建议
        clicked = await page.evaluate("""
            () => {
                const sels = ['[role=option]', '[class*=suggest] li', '[class*=dropdown] li',
                              '[class*=listbox] li', '[class*=result] li', '[class*=autocomplete] li'];
                for (const sel of sels) {
                    const els = document.querySelectorAll(sel);
                    for (const el of els) {
                        const r = el.getBoundingClientRect();
                        if (r.width>0 && r.height>0) {
                            el.click();
                            return 'clicked: ' + sel + ' -> ' + (el.innerText||'').substring(0,40);
                        }
                    }
                }
                return 'no suggestion';
            }
        """)
        print(f"补全点击: {clicked}")
        await asyncio.sleep(5)

        reqs = await page.evaluate("window.__reqs || []")
        print(f"\n=== 过滤门店/库存相关请求 ({len(reqs)} 总) ===")
        matched = 0
        for r in reqs:
            low = r["url"].lower()
            if any(k in low for k in KEYWORDS):
                matched += 1
                print(f"\n  [{r['method']} {r['status']}] {r['url'][:200]}")
                if r["body"]:
                    print(f"      BODY: {r['body'][:800]}")
        print(f"\n匹配 {matched} 条")

        # 提交按钮
        submit = page.locator(".lv-modal__footer button")
        if await submit.count() > 0:
            print(f"提交按钮 disabled={await submit.first.get_attribute('disabled')}")

        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())