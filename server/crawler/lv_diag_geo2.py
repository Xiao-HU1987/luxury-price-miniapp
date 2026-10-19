"""测试地理位置方案：CDP setGeolocationOverride + 点击"現在地で検索"，hook fetch/XHR。

用法：env -u HTTP_PROXY -u HTTPS_PROXY -u http_proxy -u https_proxy -u ALL_PROXY -u all_proxy \
        venv/bin/python3.11 -m crawler.lv_diag_geo2 "https://jp.louisvuitton.com/jpn-jp/products/-/M29195" 35.6762 139.6503
"""
import asyncio
import os
import sys

for v in ("http_proxy", "https_proxy", "HTTP_PROXY", "HTTPS_PROXY",
          "all_proxy", "ALL_PROXY"):
    os.environ.pop(v, None)

from playwright.async_api import async_playwright

PANEL_TEXT = "ストアの在庫状況を確認する"


async def install_hooks(page):
    await page.evaluate("""
        () => {
            window.__LV_HOOKS__ = [];
            const record = (kind, method, url, body) => {
                window.__LV_HOOKS__.push({kind, method, url: String(url).substring(0,250), body: body?String(body).substring(0,500):''});
            };
            const of = window.fetch;
            if (of) window.fetch = async function(...a){
                const url = typeof a[0]==='string'?a[0]:(a[0]&&a[0].url)||'';
                const o = a[1]||{}; record('fetch', o.method||'GET', url, o.body);
                try{return await of.apply(this,a);}catch(e){throw e;}
            };
            const oo = XMLHttpRequest.prototype.open, os_ = XMLHttpRequest.prototype.send;
            XMLHttpRequest.prototype.open = function(m,u,...rest){this.__u=u;this.__m=m;return oo.apply(this,[m,u,...rest]);};
            XMLHttpRequest.prototype.send = function(b){record('xhr',this.__m,this.__u,b);return os_.apply(this,arguments);};
        }
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


async def main():
    url = sys.argv[1] if len(sys.argv) > 1 else "https://jp.louisvuitton.com/jpn-jp/products/-/M29195"
    lat = float(sys.argv[2]) if len(sys.argv) > 2 else 35.6762
    lon = float(sys.argv[3]) if len(sys.argv) > 3 else 139.6503
    async with async_playwright() as pw:
        browser = await pw.chromium.connect_over_cdp("http://127.0.0.1:9333")
        ctx = browser.contexts[0] if browser.contexts else await browser.new_context()
        page = await ctx.new_page()
        await page.set_viewport_size({"width": 1440, "height": 900})
        await install_hooks(page)

        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=45000)
        except Exception as e:
            print(f"导航异常: {str(e).splitlines()[0]}")
        await asyncio.sleep(8)
        await open_modal(page)

        # 设置地理位置（CDP override + 权限）
        print(f"\n=== 设置地理位置 ({lat},{lon}) ===")
        try:
            await ctx.grant_permissions(["geolocation"])
            print("grant_permissions OK")
        except Exception as e:
            print(f"grant_permissions 失败: {str(e).splitlines()[0]}")
        try:
            await ctx.set_geolocation({"latitude": lat, "longitude": lon})
            print("set_geolocation OK")
        except Exception as e:
            print(f"set_geolocation 失败: {str(e).splitlines()[0]}")
        await asyncio.sleep(2)

        # 验证 navigator.geolocation 是否可用
        geo_test = await page.evaluate("""
            () => new Promise((resolve) => {
                if (!navigator.geolocation) return resolve('NO_GEOLOCATION_API');
                navigator.geolocation.getCurrentPosition(
                    (p) => resolve('OK ' + p.coords.latitude + ',' + p.coords.longitude),
                    (e) => resolve('ERR ' + e.code + ' ' + e.message),
                    {timeout: 5000}
                );
            })
        """)
        print(f"geolocation 测试: {geo_test}")

        # 获取地理位置按钮
        geo_btn = page.locator(".lv-store-geolocation__get-button")
        if await geo_btn.count() == 0:
            print("未找到'現在地で検索'按钮")
            await browser.close()
            return
        dis = await geo_btn.first.get_attribute("disabled")
        print(f"現在地で検索 disabled={dis}")

        # 点击'現在地で検索'
        await page.evaluate("window.__LV_HOOKS__=[]")
        print("\n=== 点击'現在地で検索' ===")
        await geo_btn.first.click(timeout=5000)
        await asyncio.sleep(10)

        hooked = await page.evaluate("window.__LV_HOOKS__ || []")
        print(f"--- hook 捕获 {len(hooked)} 个请求 ---")
        for h in hooked:
            print(f"  [{h['kind']}] {h['method']} {h['url']}")
            if h['body']:
                print(f"      BODY: {h['body'][:300]}")

        # dump 弹窗状态
        state = await page.evaluate("""
            () => {
                const m = document.querySelector('.-sidepanel.lv-locate-in-store');
                if(!m) return 'NO_MODAL';
                const steps={};
                for(const s of ['first-step','second-step']){const el=m.querySelector('.lv-locate-in-store__'+s+'-modal'); steps[s]=el?(el.innerText||'').substring(0,300):'NONE';}
                const err=m.querySelector('.lv-field-error');
                const cards=m.querySelectorAll('[class*="store-card"],[class*="pos"],[class*="store-item"]');
                const vis=[]; for(const c of cards){const r=c.getBoundingClientRect(); if(r.width>0&&r.height>0) vis.push((c.innerText||'').substring(0,120));}
                return {steps, err:err?(err.innerText||''):'', cards:vis};
            }
        """)
        print(f"\nerror: {state.get('err')!r}")
        print(f"first-step: {state.get('steps',{}).get('first-step','')[:120]!r}")
        print(f"second-step: {state.get('steps',{}).get('second-step','')[:200]!r}")
        print(f"门店卡片: {len(state.get('cards',[]))}")
        for c in state['cards'][:8]: print(f"  - {c}")
        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())