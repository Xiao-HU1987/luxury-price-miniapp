"""方案A v25：注入 geolocation 监控，追踪点击"現在地で検索"后 Vue 的调用行为。

用法：venv/bin/python3.11 -m crawler.lv_diag_v25 <SKU>
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

MONITOR_SCRIPT = r"""
window.__GEO_LOG = [];
(function() {
    if (!navigator.geolocation) { window.__GEO_LOG.push('no geolocation api'); return; }
    const origGC = navigator.geolocation.getCurrentPosition.bind(navigator.geolocation);
    const origWP = navigator.geolocation.watchPosition.bind(navigator.geolocation);
    navigator.geolocation.getCurrentPosition = function(success, error, opts) {
        window.__GEO_LOG.push('getCurrentPosition called');
        try {
            return origGC(function(pos){
                window.__GEO_LOG.push('getCurrentPosition SUCCESS '+pos.coords.latitude+','+pos.coords.longitude);
                if (success) success(pos);
            }, function(err){
                window.__GEO_LOG.push('getCurrentPosition ERROR code='+err.code+' '+err.message);
                if (error) error(err);
            }, opts);
        } catch(e) { window.__GEO_LOG.push('getCurrentPosition EXC '+e); }
    };
    navigator.geolocation.watchPosition = function(success, error, opts) {
        window.__GEO_LOG.push('watchPosition called');
        return origWP(success, error, opts);
    };
    window.__GEO_LOG.push('monkeypatch installed');
})();
"""


async def main():
    sku = sys.argv[1] if len(sys.argv) > 1 else "M26763"
    url = f"https://jp.louisvuitton.com/jpn-jp/products/-/{sku}"
    async with async_playwright() as pw:
        browser = await pw.chromium.connect_over_cdp("http://127.0.0.1:9333")
        ctx = browser.contexts[0] if browser.contexts else await browser.new_context(
            locale="ja-JP", timezone_id="Asia/Tokyo")
        await ctx.add_init_script(MONITOR_SCRIPT)
        page = await ctx.new_page()
        await page.set_viewport_size({"width": 1440, "height": 900})

        print(f"=== 导航 {sku} ===")
        try:
            resp = await page.goto(url, wait_until="domcontentloaded", timeout=45000)
            print(f"HTTP: {resp.status if resp else 'None'}")
        except Exception as e:
            print(f"导航异常: {str(e).split(chr(10))[0]}")
        await asyncio.sleep(8)

        try:
            await ctx.grant_permissions(['geolocation'], origin="https://jp.louisvuitton.com")
            await ctx.set_geolocation({"latitude": 35.6762, "longitude": 139.6503})
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

        # 清空geo log
        await page.evaluate("window.__GEO_LOG = []")

        print("\n=== 点击'現在地で検索' ===")
        geo = page.locator(".lv-store-geolocation__get-button")
        if await geo.count() > 0:
            await geo.first.click(timeout=5000)
            print("已点击")
        await asyncio.sleep(8)

        log = await page.evaluate("window.__GEO_LOG || []")
        print(f"\ngeolocation 调用日志 ({len(log)}):")
        for l in log:
            print(f"  - {l}")

        inp = await page.evaluate("document.querySelector('#address-search-input')?.value")
        print(f"input_val='{inp}'")

        # 手动调用一次确认monkeypatch生效
        manual = await page.evaluate(r"""
            () => new Promise(res => {
                window.navigator.geolocation.getCurrentPosition(
                    p => res('ok '+p.coords.latitude+','+p.coords.longitude),
                    e => res('err '+e.code)
                );
            })
        """)
        print(f"手动调用: {manual}")

        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())