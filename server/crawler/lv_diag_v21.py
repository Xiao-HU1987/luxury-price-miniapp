"""方案A v21：系统测试多种交互组合，监听所有网络请求找出库存API。

用法：venv/bin/python3.11 -m crawler.lv_diag_v21 <SKU> <城市>
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
        url = resp.url
        # 捕获所有请求（含第三方），重点关注API
        try:
            ct = resp.headers.get("content-type", "")
        except Exception:
            ct = ""
        body = ""
        url_l = url.lower()
        interesting = any(k in url_l for k in ["store", "inventory", "availability",
                                               "stock", "geoloc", "address", "suggest",
                                               "point-of-sale", "pos/", "api/", "graphql",
                                               "find", "locator", "geo"])
        if interesting:
            if "json" in ct:
                try:
                    body = (await resp.text())[:2000]
                except Exception:
                    body = ""
            REQUESTS.append({"url": url, "status": resp.status, "ct": ct, "body": body})
    page.on("response", on_resp)


async def open_product_modal(page, sku):
    url = f"https://jp.louisvuitton.com/jpn-jp/products/-/{sku}"
    try:
        resp = await page.goto(url, wait_until="domcontentloaded", timeout=45000)
        print(f"HTTP: {resp.status if resp else 'None'}")
    except Exception as e:
        print(f"导航异常: {str(e).split(chr(10))[0]}")
    await asyncio.sleep(8)

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


async def main():
    sku = sys.argv[1] if len(sys.argv) > 1 else "M26763"
    city = sys.argv[2] if len(sys.argv) > 2 else "東京"
    async with async_playwright() as pw:
        browser = await pw.chromium.connect_over_cdp("http://127.0.0.1:9333")
        ctx = browser.contexts[0] if browser.contexts else await browser.new_context(
            locale="ja-JP", timezone_id="Asia/Tokyo")
        page = await ctx.new_page()
        await page.set_viewport_size({"width": 1440, "height": 900})
        await setup_network(page)

        print(f"=== 导航 {sku} ===")
        await open_product_modal(page, sku)

        # 输入城市
        print(f"\n=== 输入 '{city}' ===")
        inp = page.locator("#address-search-input")
        if await inp.count() > 0:
            await inp.click(timeout=5000)
            await asyncio.sleep(1)
            await inp.press_sequentially(city, delay=150)
        await asyncio.sleep(5)

        REQUESTS.clear()

        # 尝试1：点击放大镜搜索按钮
        print("\n=== 尝试1: 点击放大镜按钮 ===")
        mag = page.locator(".lv-address-search-form__button")
        if await mag.count() > 0:
            try:
                await mag.first.click(timeout=4000)
                print("已点击放大镜")
            except Exception as e:
                print(f"点击失败: {str(e).split(chr(10))[0]}")
        await asyncio.sleep(6)
        print(f"请求数: {len(REQUESTS)}")
        st = await page.evaluate(r"""
            () => {
                const m = document.querySelector('.-sidepanel.lv-locate-in-store');
                const second = document.querySelector('.lv-locate-in-store__second-step-modal');
                return {second: !!second, text:(m?m.innerText:'').substring(0,300)};
            }
        """)
        print(f"弹窗: {st}")

        # 尝试2：输入城市后按 Enter
        print("\n=== 尝试2: 按 Enter ===")
        if await inp.count() > 0:
            await inp.press("Enter")
        await asyncio.sleep(6)
        print(f"请求数: {len(REQUESTS)}")
        st = await page.evaluate(r"""
            () => {
                const m = document.querySelector('.-sidepanel.lv-locate-in-store');
                const second = document.querySelector('.lv-locate-in-store__second-step-modal');
                return {second: !!second, text:(m?m.innerText:'').substring(0,300)};
            }
        """)
        print(f"弹窗: {st}")

        # 尝试3：点击底部按钮
        print("\n=== 尝试3: 点击底部'在庫状況を見る' ===")
        fb = await page.evaluate("()=>{const b=document.querySelector('.lv-modal__footer button');return b?{d:b.disabled,t:(b.innerText||'').trim()}:null}")
        print(f"底部: {fb}")
        if fb and not fb['d']:
            await page.locator(".lv-modal__footer button").first.click(timeout=5000)
        await asyncio.sleep(6)
        print(f"请求数: {len(REQUESTS)}")
        st = await page.evaluate(r"""
            () => {
                const m = document.querySelector('.-sidepanel.lv-locate-in-store');
                const second = document.querySelector('.lv-locate-in-store__second-step-modal');
                return {second: !!second, text:(m?m.innerText:'').substring(0,300)};
            }
        """)
        print(f"弹窗: {st}")

        # 尝试4：点击地理位置按钮
        print("\n=== 尝试4: 点击'現在地で検索' ===")
        try:
            await ctx.grant_permissions(['geolocation'])
            await ctx.set_geolocation({"latitude": 35.6762, "longitude": 139.6503})
        except Exception as e:
            print(f"geo授权异常: {e}")
        geo = page.locator(".lv-store-geolocation__get-button")
        if await geo.count() > 0:
            await geo.first.click(timeout=5000)
        await asyncio.sleep(6)
        print(f"请求数: {len(REQUESTS)}")
        st = await page.evaluate(r"""
            () => {
                const m = document.querySelector('.-sidepanel.lv-locate-in-store');
                const second = document.querySelector('.lv-locate-in-store__second-step-modal');
                const inp = document.querySelector('#address-search-input');
                return {second: !!second, input_val: (inp?inp.value:null), text:(m?m.innerText:'').substring(0,300)};
            }
        """)
        print(f"弹窗: {st}")

        print(f"\n=== 全部相关网络请求 ({len(REQUESTS)} 条) ===")
        for r_ in REQUESTS:
            print(f"  [RESP {r_['status']} {r_['ct']}] {r_['url']}")
            if r_['body']:
                print(f"      BODY: {r_['body'][:400]}")

        html = await page.evaluate("document.documentElement.outerHTML")
        OUT_DIR.joinpath(f"v21_{sku}_{city}.html").write_text(html, encoding="utf-8")

        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())