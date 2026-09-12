"""方案A v23：授权地理位置 → 点击"現在地で検索" → 点击底部"在庫状況を見る"。

用法：venv/bin/python3.11 -m crawler.lv_diag_v23 <SKU>
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


async def setup_network(page):
    async def on_resp(resp):
        interesting = any(k in resp.url.lower() for k in
                          ["store", "inventory", "availability", "stock", "geoloc",
                           "address", "suggest", "point-of-sale", "api/", "graphql",
                           "geo", "locat", "search", "map"])
        if interesting:
            try:
                ct = resp.headers.get("content-type", "")
            except Exception:
                ct = ""
            body = ""
            if "json" in ct:
                try:
                    body = (await resp.text())[:1500]
                except Exception:
                    body = ""
            REQUESTS.append({"url": resp.url, "status": resp.status, "ct": ct, "body": body})
    page.on("response", on_resp)


async def main():
    sku = sys.argv[1] if len(sys.argv) > 1 else "M26763"
    url = f"https://jp.louisvuitton.com/jpn-jp/products/-/{sku}"
    async with async_playwright() as pw:
        browser = await pw.chromium.connect_over_cdp("http://127.0.0.1:9333")
        ctx = browser.contexts[0] if browser.contexts else await browser.new_context(
            locale="ja-JP", timezone_id="Asia/Tokyo")
        page = await ctx.new_page()
        await page.set_viewport_size({"width": 1440, "height": 900})
        await setup_network(page)

        print(f"=== 导航 {sku} ===")
        try:
            resp = await page.goto(url, wait_until="domcontentloaded", timeout=45000)
            print(f"HTTP: {resp.status if resp else 'None'}")
        except Exception as e:
            print(f"导航异常: {str(e).split(chr(10))[0]}")
        await asyncio.sleep(8)

        # 授权地理位置
        try:
            await ctx.grant_permissions(['geolocation'], origin="https://jp.louisvuitton.com")
            await ctx.set_geolocation({"latitude": 35.6762, "longitude": 139.6503})
            print("已授权+设置地理位置=東京")
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

        # 点击"現在地で検索"
        print("\n=== 点击'現在地で検索' ===")
        geo = page.locator(".lv-store-geolocation__get-button")
        if await geo.count() > 0:
            await geo.first.click(timeout=5000)
            print("已点击")
            await asyncio.sleep(5)
            inp = await page.evaluate("document.querySelector('#address-search-input')?.value")
            print(f"点击后 input_val='{inp}'")
        else:
            print("geo按钮不存在")

        # 点击底部"在庫状況を見る"
        print("\n=== 点击底部'在庫状況を見る' ===")
        fb = await page.evaluate("()=>{const b=document.querySelector('.lv-modal__footer button');return b?{d:b.disabled,t:(b.innerText||'').trim()}:null}")
        print(f"底部: {fb}")
        if fb and not fb['d']:
            try:
                await page.locator(".lv-modal__footer button").first.click(timeout=5000)
                print("已点击底部")
            except Exception as e:
                await page.evaluate("()=>{const b=document.querySelector('.lv-modal__footer button'); if(b) b.click();}")
                print("已JS点击底部")
        await asyncio.sleep(8)

        # 检查
        st = await page.evaluate(r"""
            () => {
                const m = document.querySelector('.-sidepanel.lv-locate-in-store');
                const second = document.querySelector('.lv-locate-in-store__second-step-modal');
                const inp = document.querySelector('#address-search-input');
                return {second:!!second, input_val:(inp?inp.value:null), text:(m?m.innerText:'').substring(0,500)};
            }
        """)
        print(f"\n弹窗: {st}")

        print(f"\n=== 网络请求 ({len(REQUESTS)} 条) ===")
        for r_ in REQUESTS:
            print(f"  [RESP {r_['status']} {r_['ct']}] {r_['url']}")
            if r_['body']:
                print(f"      BODY: {r_['body'][:300]}")

        html = await page.evaluate("document.documentElement.outerHTML")
        OUT_DIR.joinpath(f"v23_{sku}.html").write_text(html, encoding="utf-8")

        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())