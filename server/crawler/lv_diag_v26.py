"""方案A v26：抓取LV所有JS bundle，搜索库存API端点。

用法：venv/bin/python3.11 -m crawler.lv_diag_v26 <SKU>
"""
import asyncio
import os
import re
import sys
from pathlib import Path

for v in ("http_proxy", "https_proxy", "HTTP_PROXY", "HTTPS_PROXY",
          "all_proxy", "ALL_PROXY"):
    os.environ.pop(v, None)

from playwright.async_api import async_playwright

PANEL_TEXT = "ストアの在庫状況を確認する"
OUT_DIR = Path("/tmp/lv_diag_out")
OUT_DIR.mkdir(parents=True, exist_ok=True)

KEYWORDS = ["availability", "inventory", "findStore", "getStore", "storeStock",
            "inStock", "point-of-sale", "pointOfSale", "locate", "geoloc",
            "/store", "stores/", "availability/", "inventory/", "stock/",
            "GetAvail", "productAvailability"]


def scan_js(content, name):
    hits = []
    for kw in KEYWORDS:
        for m in re.finditer(re.escape(kw), content, re.IGNORECASE):
            s = max(0, m.start() - 120)
            e = min(len(content), m.end() + 120)
            hits.append(f"[{name}] ...{content[s:e]}...")
    return hits


async def main():
    sku = sys.argv[1] if len(sys.argv) > 1 else "M26763"
    url = f"https://jp.louisvuitton.com/jpn-jp/products/-/{sku}"
    async with async_playwright() as pw:
        browser = await pw.chromium.connect_over_cdp("http://127.0.0.1:9333")
        ctx = browser.contexts[0] if browser.contexts else await browser.new_context(
            locale="ja-JP", timezone_id="Asia/Tokyo")
        page = await ctx.new_page()
        await page.set_viewport_size({"width": 1440, "height": 900})

        print(f"=== 导航 {sku} ===")
        try:
            resp = await page.goto(url, wait_until="domcontentloaded", timeout=45000)
            print(f"HTTP: {resp.status if resp else 'None'}")
        except Exception as e:
            print(f"导航异常: {str(e).split(chr(10))[0]}")
        await asyncio.sleep(8)

        # 打开库存弹窗（确保组件chunk加载）
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

        # 收集所有 script src 和 modulepreload
        scripts = await page.evaluate(r"""
            () => {
                const urls = new Set();
                document.querySelectorAll('script[src]').forEach(s => urls.add(s.src));
                document.querySelectorAll('link[rel="modulepreload"], link[rel="preload"][as="script"]').forEach(l => urls.add(l.href));
                return Array.from(urls);
            }
        """)
        print(f"\nJS文件数: {len(scripts)}")

        # 抓取每个JS并扫描
        all_hits = []
        for i, src in enumerate(scripts):
            try:
                content = await page.evaluate(
                    "async (src) => { const r = await fetch(src); return await r.text(); }",
                    src
                )
                hits = scan_js(content, Path(src).name)
                all_hits.extend(hits)
                if hits:
                    print(f"\n### {src} ({len(hits)} hits)")
            except Exception as e:
                print(f"  fetch失败 {src}: {str(e)[:60]}")

        # 去重打印
        print(f"\n\n=== 全部命中 ({len(all_hits)}) ===")
        seen = set()
        for h in all_hits:
            if h not in seen:
                seen.add(h)
                print(h[:300])
                print("---")

        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())