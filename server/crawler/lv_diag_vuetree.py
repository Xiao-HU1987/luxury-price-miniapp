"""从 Vue 根实例遍历组件树，定位尺寸选择组件并 dump 其 data / methods。

用法：env -u HTTP_PROXY -u HTTPS_PROXY -u http_proxy -u https_proxy -u ALL_PROXY -u all_proxy \
        venv/bin/python3.11 -m crawler.lv_diag_vuetree "https://jp.louisvuitton.com/jpn-jp/products/-/M29195"
"""
import asyncio
import os
import sys

for v in ("http_proxy", "https_proxy", "HTTP_PROXY", "HTTPS_PROXY",
          "all_proxy", "ALL_PROXY"):
    os.environ.pop(v, None)

from playwright.async_api import async_playwright

PANEL_TEXT = "ストアの在庫状況を確認する"


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
    async with async_playwright() as pw:
        browser = await pw.chromium.connect_over_cdp("http://127.0.0.1:9333")
        ctx = browser.contexts[0] if browser.contexts else await browser.new_context()
        page = await ctx.new_page()
        await page.set_viewport_size({"width": 1440, "height": 900})
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=45000)
        except Exception as e:
            print(f"导航异常: {str(e).splitlines()[0]}")
        await asyncio.sleep(8)
        await open_modal(page)

        # 1) 找根 Vue 实例
        root_info = await page.evaluate("""
            () => {
                const roots = ['#__nuxt', '#__layout', '#app', '#__app'];
                const out = {};
                for (const sel of roots) {
                    const el = document.querySelector(sel);
                    if (el && el.__vue__) {
                        out[sel] = { has_vue: true, name: (el.__vue__.$options && el.__vue__.$options.name) || 'root' };
                    } else if (el) {
                        out[sel] = { has_vue: false };
                    } else {
                        out[sel] = { has_vue: 'no_el' };
                    }
                }
                return out;
            }
        """)
        print("=== 根 Vue 实例 ===")
        for k, v in root_info.items():
            print(f"  {k}: {v}")

        # 2) 遍历组件树，找含 size/model/selected 的组件
        tree = await page.evaluate("""
            () => {
                const results = [];
                const seen = new Set();
                const walk = (vm, depth) => {
                    if (!vm || depth > 40 || seen.has(vm)) return;
                    seen.add(vm);
                    let name = (vm.$options && vm.$options.name) || 'anon';
                    let data = vm.$data || {};
                    const keys = Object.keys(data);
                    // 找含 size/model/selected/variant 的 data 字段
                    const inter = {};
                    for (const k of keys) {
                        if (/size|model|selected|variant|displayed|available/i.test(k)) {
                            let v = data[k];
                            if (v && typeof v === 'object') v = JSON.stringify(v).substring(0,150);
                            inter[k] = String(v);
                        }
                    }
                    // dump 有 select 子元素的组件
                    const hasSelect = vm.$el && vm.$el.querySelector && vm.$el.querySelector('select#displayedModelList');
                    if (Object.keys(inter).length || hasSelect) {
                        results.push({depth, name, hasSelect: !!hasSelect, data: inter});
                    }
                    const children = vm.$children || [];
                    for (const c of children) walk(c, depth+1);
                };
                const roots = ['#__nuxt','#__layout','#app','#__app'];
                for (const sel of roots) {
                    const el = document.querySelector(sel);
                    if (el && el.__vue__) walk(el.__vue__, 0);
                }
                return results;
            }
        """)
        print(f"\n=== 匹配组件 ({len(tree)}) ===")
        for c in tree:
            print(f"  depth={c['depth']} name={c['name']} hasSelect={c['hasSelect']} data={c['data']}")
        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())