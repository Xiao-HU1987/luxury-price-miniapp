"""方案A v22：专注地理位置搜索，捕获所有请求+console错误。

用法：venv/bin/python3.11 -m crawler.lv_diag_v22 <SKU>
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
OUT_DIR.mkdir(parents=True, exist_ok=True)

REQUESTS = []
CONSOLE_MSGS = []


async def setup(page):
    async def on_resp(resp):
        try:
            ct = resp.headers.get("content-type", "")
        except Exception:
            ct = ""
        interesting = any(k in resp.url.lower() for k in
                          ["store", "inventory", "availability", "stock", "geoloc",
                           "address", "suggest", "point-of-sale", "pos/", "api/",
                           "graphql", "geo", "maps", "locat", "find", "search"])
        if interesting:
            body = ""
            if "json" in ct:
                try:
                    body = (await resp.text())[:1500]
                except Exception:
                    body = ""
            REQUESTS.append({"url": resp.url, "status": resp.status, "ct": ct, "body": body})
    page.on("response", on_resp)

    async def on_console(msg):
        CONSOLE_MSGS.append({"type": msg.type, "text": msg.text[:200]})
    page.on("console", on_console)


async def main():
    sku = sys.argv[1] if len(sys.argv) > 1 else "M26763"
    url = f"https://jp.louisvuitton.com/jpn-jp/products/-/{sku}"
    async with async_playwright() as pw:
        browser = await pw.chromium.connect_over_cdp("http://127.0.0.1:9333")
        ctx = browser.contexts[0] if browser.contexts else await browser.new_context(
            locale="ja-JP", timezone_id="Asia/Tokyo")
        page = await ctx.new_page()
        await page.set_viewport_size({"width": 1440, "height": 900})
        await setup(page)

        print(f"=== 导航 {sku} ===")
        try:
            resp = await page.goto(url, wait_until="domcontentloaded", timeout=45000)
            print(f"HTTP: {resp.status if resp else 'None'}")
        except Exception as e:
            print(f"导航异常: {str(e).split(chr(10))[0]}")
        await asyncio.sleep(8)

        # 检查 geolocation 可用性
        geo_ok = await page.evaluate(r"""
            () => {
                return {hasGeolocation: 'geolocation' in navigator, hasAPI: typeof navigator.geolocation !== 'undefined'};
            }
        """)
        print(f"geolocation: {geo_ok}")

        # 授权地理位置（用 grant_permissions）
        try:
            await ctx.grant_permissions(['geolocation'], origin="https://jp.louisvuitton.com")
            await ctx.set_geolocation({"latitude": 35.6762, "longitude": 139.6503})
            print("已设置地理位置+授权東京")
        except Exception as e:
            print(f"geo授权异常: {e}")

        await page.evaluate(r"""
            (panelText) => {
                const panels = document.querySelectorAll('.lv-expandable-panel');
                for (const p of panels) {
                    if ((p.innerText||'').includes(panelText)) {
                        p.scrollIntoView({behavior:'instant', block:'center'});
                        break;
                    }
                }
            }
        """, PANEL_TEXT)
        await asyncio.sleep(1)

        size_sel = page.locator("#displayedModelList")
        if await size_sel.count() > 0:
            opts = await size_sel.locator("option").all_inner_texts()
            real = [o.strip() for o in opts if "選ん" not in o]
            if real:
                await size_sel.select_option(label=real[0])
                await asyncio.sleep(3)

        await page.evaluate(r"""
            (panelText) => {
                const panels = document.querySelectorAll('.lv-expandable-panel');
                for (const p of panels) {
                    if ((p.innerText||'').includes(panelText)) {
                        const eb = p.querySelector('button[aria-expanded]');
                        if (eb && eb.getAttribute('aria-expanded')!=='true') eb.click();
                        p.querySelectorAll('.lv-expandable-panel__content').forEach(c=>{c.style.display='block';c.setAttribute('aria-hidden','false');});
                        break;
                    }
                }
                const sb = document.querySelector('.lv-product-locate-in-store__container');
                if (sb) sb.click();
            }
        """, PANEL_TEXT)
        await asyncio.sleep(6)

        REQUESTS.clear()
        CONSOLE_MSGS.clear()

        # 点击地理位置按钮
        print("\n=== 点击'現在地で検索' ===")
        geo = page.locator(".lv-store-geolocation__get-button")
        if await geo.count() > 0:
            await geo.first.click(timeout=5000)
            print("已点击")
        await asyncio.sleep(8)

        # 状态
        st = await page.evaluate(r"""
            () => {
                const m = document.querySelector('.-sidepanel.lv-locate-in-store');
                const inp = document.querySelector('#address-search-input');
                const err = document.querySelector('.lv-field-error');
                const second = document.querySelector('.lv-locate-in-store__second-step-modal');
                return {
                    second: !!second,
                    input_val: inp?inp.value:null,
                    err: err?(err.innerText||'').trim():'',
                    text: (m?m.innerText:'').substring(0,400)
                };
            }
        """)
        print(f"弹窗状态: {st}")

        # 尝试直接调用浏览器 geolocation，看返回
        geo_result = await page.evaluate(r"""
            () => new Promise((resolve) => {
                if (!navigator.geolocation) { resolve({err:'no api'}); return; }
                navigator.geolocation.getCurrentPosition(
                    (pos) => resolve({ok:true, lat:pos.coords.latitude, lng:pos.coords.longitude}),
                    (err) => resolve({ok:false, code:err.code, msg:err.message}),
                    {timeout:8000}
                );
            })
        """)
        print(f"geolocation.getCurrentPosition 结果: {geo_result}")

        print(f"\n=== 网络请求 ({len(REQUESTS)} 条) ===")
        for r_ in REQUESTS:
            print(f"  [RESP {r_['status']} {r_['ct']}] {r_['url']}")
            if r_['body']:
                print(f"      BODY: {r_['body'][:300]}")

        print(f"\n=== Console消息 ({len(CONSOLE_MSGS)} 条) ===")
        for c in CONSOLE_MSGS[-20:]:
            print(f"  [{c['type']}] {c['text']}")

        html = await page.evaluate("document.documentElement.outerHTML")
        OUT_DIR.joinpath(f"v22_{sku}.html").write_text(html, encoding="utf-8")

        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())