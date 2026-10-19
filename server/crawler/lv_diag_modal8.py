"""Hook fetch/XHR 精确捕获库存请求 + 测试尺寸选择。

用法：env -u HTTP_PROXY -u HTTPS_PROXY -u http_proxy -u https_proxy -u ALL_PROXY -u all_proxy \
        venv/bin/python3.11 -m crawler.lv_diag_modal8 "https://jp.louisvuitton.com/jpn-jp/products/-/M29195"
"""
import asyncio
import os
import sys

for v in ("http_proxy", "https_proxy", "HTTP_PROXY", "HTTPS_PROXY",
          "all_proxy", "ALL_PROXY"):
    os.environ.pop(v, None)

from playwright.async_api import async_playwright

PANEL_TEXT = "ストアの在庫状況を確認する"
HOOKED = []


async def install_hooks(page):
    """在页面内 hook fetch 和 XHR，记录所有调用（含被 abort 的）。"""
    await page.evaluate("""
        () => {
            window.__LV_HOOKS__ = [];
            const record = (kind, method, url, body) => {
                window.__LV_HOOKS__.push({kind, method, url: String(url).substring(0,250), body: body?String(body).substring(0,500):''});
            };
            // hook fetch
            const origFetch = window.fetch;
            if (origFetch) {
                window.fetch = async function(...args) {
                    const url = typeof args[0]==='string' ? args[0] : (args[0]&&args[0].url)||'';
                    const opts = args[1]||{};
                    record('fetch', (opts.method||'GET'), url, opts.body);
                    try { return await origFetch.apply(this, args); }
                    catch(e){ console.log('fetch-err', url); throw e; }
                };
            }
            // hook XHR
            const origOpen = XMLHttpRequest.prototype.open;
            const origSend = XMLHttpRequest.prototype.send;
            XMLHttpRequest.prototype.open = function(method, url, ...rest) {
                this.__url = url; this.__method = method;
                return origOpen.apply(this, [method, url, ...rest]);
            };
            XMLHttpRequest.prototype.send = function(body) {
                record('xhr', this.__method, this.__url, body);
                return origSend.apply(this, arguments);
            };
        }
    """)

def get_hooked(page):
    return page.evaluate("window.__LV_HOOKS__ || []")


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


def btn_disabled(page):
    return page.evaluate("""
        () => { const bs=document.querySelectorAll('.lv-loading-button');
            for(const b of bs) if((b.innerText||'').includes('在庫状況を見る')) return b.disabled; return 'NO_BTN'; }
    """)


def dump_state(page):
    return page.evaluate("""
        () => {
            const m = document.querySelector('.-sidepanel.lv-locate-in-store');
            if(!m) return 'NO_MODAL';
            const steps = {};
            for (const s of ['first-step','second-step']) {
                const el = m.querySelector('.lv-locate-in-store__'+s+'-modal');
                steps[s] = el ? (el.innerText||'').substring(0,300) : 'NONE';
            }
            const err = m.querySelector('.lv-field-error');
            const cards = m.querySelectorAll('[class*="store-card"], [class*="pos"], [class*="store-item"]');
            const vis=[]
            for(const c of cards){const r=c.getBoundingClientRect(); if(r.width>0&&r.height>0) vis.push((c.innerText||'').substring(0,120));}
            return {steps, err: err?(err.innerText||''):'', cards: vis};
        }
    """)


async def main():
    url = sys.argv[1] if len(sys.argv) > 1 else "https://jp.louisvuitton.com/jpn-jp/products/-/M29195"
    city = sys.argv[2] if len(sys.argv) > 2 else "東京"
    async with async_playwright() as pw:
        browser = await pw.chromium.connect_over_cdp("http://127.0.0.1:9333")
        ctx = browser.contexts[0] if browser.contexts else await browser.new_context()
        page = await ctx.new_page()
        await page.set_viewport_size({"width": 1440, "height": 900})
        await install_hooks(page)

        print(f"=== 导航: {url} ===")
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=45000)
        except Exception as e:
            print(f"导航异常: {str(e).splitlines()[0]}")
        await asyncio.sleep(8)
        await open_modal(page)

        # 选尺寸
        size_sel = page.locator("#displayedModelList")
        if await size_sel.count() > 0:
            await size_sel.select_option(index=1)
            await asyncio.sleep(2)
            print(f"选尺寸后 按钮disabled={await btn_disabled(page)}")

        # 输入城市
        inp = page.locator("#address-search-input")
        await inp.click(timeout=3000)
        await asyncio.sleep(0.3)
        await inp.type(city, delay=200)
        await asyncio.sleep(2)
        print(f"输入'{city}'后 按钮disabled={await btn_disabled(page)}")

        # 点击'在庫状況を見る'
        await page.evaluate("window.__LV_HOOKS__=[]")
        print("\n=== 点击'在庫状況を見る' ===")
        see = page.locator(".lv-loading-button:has-text('在庫状況を見る')")
        await see.first.click(timeout=5000)
        await asyncio.sleep(8)

        hooked = await get_hooked(page)
        print(f"--- hook 捕获 {len(hooked)} 个请求 ---")
        for h in hooked:
            print(f"  [{h['kind']}] {h['method']} {h['url']}")
            if h['body']:
                print(f"      BODY: {h['body'][:300]}")

        state = await dump_state(page)
        print(f"\n=== 弹窗状态 ===")
        print(f"error: {state['err']!r}")
        print(f"first-step: {state['steps']['first-step'][:150]!r}")
        print(f"second-step: {state['steps']['second-step'][:200]!r}")
        print(f"门店卡片: {len(state['cards'])}")
        for c in state['cards'][:8]:
            print(f"  - {c}")
        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())