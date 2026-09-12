"""方案A v18：文本搜索流程测试（输入城市 → 地址补全 → 选择 → 提交）。

用法：venv/bin/python3.11 -m crawler.lv_diag_v18 <SKU> <城市名>
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
        if "address" in url or "search" in url or "store" in url or "inventory" in url or "geoloc" in url or "suggest" in url:
            REQUESTS.append({"url": url, "status": resp.status, "ct": ct, "body": body})
    page.on("response", on_resp)


async def main():
    sku = sys.argv[1] if len(sys.argv) > 1 else "M26763"
    city = sys.argv[2] if len(sys.argv) > 2 else "東京"
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

        # 展开面板 + 点库存按钮
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

        # 输入城市名（真实键盘输入触发 Vue 事件）
        print(f"\n=== 输入城市 '{city}' ===")
        inp = page.locator("#address-search-input")
        if await inp.count() > 0:
            await inp.click(timeout=5000)
            await asyncio.sleep(1)
            await inp.press_sequentially(city, delay=150)
            print("已输入")
        else:
            print("找不到 #address-search-input")
        await asyncio.sleep(6)

        # 检查补全建议
        sug = await page.evaluate(r"""
            () => {
                const modal = document.querySelector('.lv-modal__content, .-sidepanel.lv-locate-in-store');
                if (!modal) return [];
                const out = [];
                modal.querySelectorAll('[class*="suggestion"] li, [role="option"], [class*="address-search"] li, [class*="dropdown"] li').forEach(el => {
                    const r = el.getBoundingClientRect();
                    if (r.width>0 && r.height>0) out.push((el.innerText||'').trim().substring(0,80));
                });
                return out;
            }
        """)
        print(f"补全建议: {sug}")

        # 输入框当前值
        val = await page.evaluate("document.querySelector('#address-search-input')?.value")
        print(f"输入框值: '{val}'")

        # 底部按钮状态
        fb = await page.evaluate(r"""
            () => {
                const b = document.querySelector('.lv-modal__footer button');
                return b ? {disabled: b.disabled, text:(b.innerText||'').trim()} : null;
            }
        """)
        print(f"底部按钮: {fb}")

        # 尝试点击第一个补全建议
        clicked = await page.evaluate(r"""
            () => {
                const modal = document.querySelector('.lv-modal__content, .-sidepanel.lv-locate-in-store');
                if (!modal) return false;
                const opts = modal.querySelectorAll('[class*="suggestion"] li, [role="option"]');
                for (const el of opts) {
                    const r = el.getBoundingClientRect();
                    if (r.width>0 && r.height>0) { el.click(); return true; }
                }
                return false;
            }
        """)
        print(f"点击补全建议: {clicked}")
        await asyncio.sleep(4)

        # 底部按钮状态
        fb2 = await page.evaluate(r"""
            () => {
                const b = document.querySelector('.lv-modal__footer button');
                return b ? {disabled: b.disabled, text:(b.innerText||'').trim()} : null;
            }
        """)
        print(f"选择后底部按钮: {fb2}")

        # 点击底部按钮
        if fb2 and fb2['disabled'] is None:
            print("\n=== 点击'在庫状況を見る' ===")
            await page.locator(".lv-modal__footer button").first.click(timeout=5000)
        await asyncio.sleep(8)

        # 提取门店
        stores = await page.evaluate(r"""
            () => {
                const second = document.querySelector('.lv-locate-in-store__second-step-modal');
                if (!second) return {modal:false, noresult:false, cards:[]};
                const cards = second.querySelectorAll('.lv-store-card-detailed');
                const out = [];
                for (const c of cards) {
                    out.push({
                        name: (c.querySelector('.lv-store-card-detailed__name')?.innerText||'').trim(),
                        info: (c.querySelector('.lv-store-card-detailed__info')?.innerText||'').trim().substring(0,120),
                        stock: (c.querySelector('.lv-store-card-detailed__stock')?.innerText||'').trim().substring(0,40)
                    });
                }
                const nores = second.innerText.includes('見つかりません') || second.querySelector('[class*="no-result"]');
                return {modal:true, noresult:!!nores, cards:out};
            }
        """)
        print(f"\n门店提取: {stores.get('modal')} 无结果={stores.get('noresult')} 数量={len(stores.get('cards',[]))}")
        for s in stores.get('cards', [])[:20]:
            print(f"  - {s['name']} | {s['info']} | [{s['stock']}]")

        # 弹窗文本
        txt = await page.evaluate(r"""
            () => {
                const m = document.querySelector('.-sidepanel.lv-locate-in-store');
                return m ? (m.innerText||'').substring(0,800) : 'NO_MODAL';
            }
        """)
        print(f"\n弹窗文本:\n{txt}")

        print(f"\n=== 相关网络请求 ({len(REQUESTS)} 条) ===")
        for r_ in REQUESTS:
            print(f"  [RESP {r_['status']} {r_['ct']}] {r_['url']}")
            if r_['body']:
                print(f"      BODY: {r_['body'][:350]}")

        html = await page.evaluate("document.documentElement.outerHTML")
        OUT_DIR.joinpath(f"v18_{sku}_{city}.html").write_text(html, encoding="utf-8")

        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())