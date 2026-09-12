"""方案A v17：完整地理位置搜索流程测试。

流程：打开弹窗 → 点击"現在地で検索" → 检查底部按钮enable → 点击"在庫状況を見る" → 提取门店。

用法：venv/bin/python3.11 -m crawler.lv_diag_v17 <SKU>
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
        if "louisvuitton.com" not in url:
            return
        try:
            ct = resp.headers.get("content-type", "")
        except Exception:
            ct = ""
        body = ""
        if "json" in ct and "louisvuitton.com" in url:
            try:
                body = (await resp.text())[:2000]
            except Exception:
                body = ""
        REQUESTS.append({"url": url, "status": resp.status, "ct": ct, "body": body})
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

        # 滚动到面板
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

        # 选尺寸
        size_sel = page.locator("#displayedModelList")
        if await size_sel.count() > 0:
            opts = await size_sel.locator("option").all_inner_texts()
            real = [o.strip() for o in opts if "選ん" not in o]
            print(f"\n尺寸: {real}")
            if real:
                await size_sel.select_option(label=real[0])
                await asyncio.sleep(3)

        # JS 展开面板 + 点击库存按钮
        r = await page.evaluate(r"""
            (panelText) => {
                const out = {panel:false, storeBtn:false};
                const panels = document.querySelectorAll('.lv-expandable-panel');
                for (const p of panels) {
                    if ((p.innerText||'').includes(panelText)) {
                        out.panel = true;
                        const eb = p.querySelector('button[aria-expanded]');
                        if (eb && eb.getAttribute('aria-expanded')!=='true') eb.click();
                        p.querySelectorAll('.lv-expandable-panel__content').forEach(c=>{c.style.display='block';c.setAttribute('aria-hidden','false');});
                        break;
                    }
                }
                const sb = document.querySelector('.lv-product-locate-in-store__container');
                if (sb) { sb.click(); out.storeBtn = true; }
                return out;
            }
        """, PANEL_TEXT)
        print(f"\n展开结果: {r}")
        await asyncio.sleep(6)

        # 授权地理位置
        try:
            await ctx.grant_permissions(['geolocation'])
            await ctx.set_geolocation({"latitude": 35.6762, "longitude": 139.6503})
            print("已设置地理位置=東京")
        except Exception as e:
            print(f"设置地理位置异常: {e}")
        await asyncio.sleep(2)

        REQUESTS.clear()

        # 点击"現在地で検索"
        print("\n=== 点击'現在地で検索' ===")
        geo = page.locator(".lv-store-geolocation__get-button")
        if await geo.count() > 0:
            dis = await geo.first.get_attribute("disabled")
            print(f"geo disabled={dis}")
            await geo.first.click(timeout=5000)
            print("已点击")
        else:
            print("geo按钮不存在")
        await asyncio.sleep(5)

        # 检查搜索后状态：输入框值、底部按钮disabled
        state = await page.evaluate(r"""
            () => {
                const input = document.querySelector('#address-search-input, .lv-address-search-form__input');
                const footer = document.querySelector('.lv-modal__footer button, .lv-modal__content .lv-modal__footer button');
                const geo = document.querySelector('.lv-store-geolocation__get-button');
                const err = document.querySelector('.lv-field-error');
                return {
                    input_value: input ? input.value : null,
                    footer_disabled: footer ? footer.disabled : null,
                    footer_text: footer ? (footer.innerText||'').trim() : null,
                    geo_disabled: geo ? geo.disabled : null,
                    error: err ? (err.innerText||'').trim() : ''
                };
            }
        """)
        print(f"搜索后状态: {state}")

        # 点击底部"在庫状況を見る"
        print("\n=== 点击底部'在庫状況を見る' ===")
        footer_btn = page.locator(".lv-modal__footer button")
        if await footer_btn.count() > 0:
            fb_dis = await footer_btn.first.get_attribute("disabled")
            print(f"底部按钮 disabled={fb_dis}")
            if fb_dis is None:
                await footer_btn.first.click(timeout=5000)
                print("已点击底部按钮")
        else:
            print("底部按钮不存在")
        await asyncio.sleep(8)

        # 提取门店
        stores = await page.evaluate(r"""
            () => {
                const second = document.querySelector('.lv-locate-in-store__second-step-modal');
                if (!second) return {modal:false, cards:[]};
                const cards = second.querySelectorAll('.lv-store-card-detailed');
                const out = [];
                for (const c of cards) {
                    out.push({
                        name: (c.querySelector('.lv-store-card-detailed__name')?.innerText||'').trim(),
                        info: (c.querySelector('.lv-store-card-detailed__info')?.innerText||'').trim().substring(0,120),
                        stock: (c.querySelector('.lv-store-card-detailed__stock')?.innerText||'').trim().substring(0,40)
                    });
                }
                return {modal:true, cards:out};
            }
        """)
        print(f"\n门店提取: modal={stores.get('modal')} 数量={len(stores.get('cards',[]))}")
        for s in stores.get('cards', [])[:15]:
            print(f"  - {s['name']} | {s['info']} | [{s['stock']}]")

        # 弹窗文本
        txt = await page.evaluate(r"""
            () => {
                const m = document.querySelector('.-sidepanel.lv-locate-in-store');
                return m ? (m.innerText||'').substring(0,700) : 'NO_MODAL';
            }
        """)
        print(f"\n弹窗文本:\n{txt}")

        print(f"\n=== 网络请求 ({len(REQUESTS)} 条) ===")
        for r_ in REQUESTS:
            print(f"  [RESP {r_['status']} {r_['ct']}] {r_['url']}")
            if r_['body']:
                print(f"      BODY: {r_['body'][:350]}")

        # 保存HTML
        html = await page.evaluate("document.documentElement.outerHTML")
        OUT_DIR.joinpath(f"v17_{sku}.html").write_text(html, encoding="utf-8")

        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())