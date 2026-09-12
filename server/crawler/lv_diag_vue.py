"""诊断 Vue 尺寸选择机制：检查 option._value、Vue 组件 data，尝试原生 JS 触发 change。

用法：env -u HTTP_PROXY -u HTTPS_PROXY -u http_proxy -u https_proxy -u ALL_PROXY -u all_proxy \
        venv/bin/python3.11 -m crawler.lv_diag_vue "https://jp.louisvuitton.com/jpn-jp/products/-/M29195"
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

        # 1) 检查 option._value 和 select 绑定
        info = await page.evaluate("""
            () => {
                const sel = document.querySelector('#displayedModelList');
                if (!sel) return {err: 'no select'};
                const opts = [];
                for (const o of sel.options) {
                    opts.push({
                        text: o.text, value: o.value,
                        has_value_prop: ('_value' in o),
                        stored: o._value !== undefined ? JSON.stringify(o._value).substring(0,80) : null,
                    });
                }
                // 找 select 的 Vue 组件
                let v = sel, vueNames = [];
                while (v && v !== document.body) {
                    if (v.__vue__) {
                        const vm = v.__vue__;
                        vueNames.push(vm.$options && vm.$options.name || vm.$el.className.split(' ')[0]);
                    }
                    v = v.parentElement;
                }
                return {selectedIndex: sel.selectedIndex, opts, vueChain: vueNames};
            }
        """)
        print("=== select 绑定信息 ===")
        print(f"selectedIndex={info.get('selectedIndex')}")
        print(f"Vue组件链: {info.get('vueChain')}")
        for o in info.get('opts', []):
            print(f"  option text={o['text']!r} value={o['value']!r} has_value={o['has_value_prop']} stored={o['stored']}")

        # 2) dump 弹窗组件 Vue data（找尺寸/selectedModel 字段）
        data = await page.evaluate("""
            () => {
                const m = document.querySelector('.-sidepanel.lv-locate-in-store');
                if (!m) return 'NO_MODAL';
                let v = m;
                const out = {};
                while (v && v !== document.body) {
                    if (v.__vue__) {
                        const vm = v.__vue__;
                        const name = (vm.$options && vm.$options.name) || (vm.$el && vm.$el.className && vm.$el.className.split(' ')[0]) || 'anon';
                        const keys = vm.$data ? Object.keys(vm.$data) : [];
                        // 只记录含 size/model/selected 的关键字段值
                        const interesting = {};
                        for (const k of keys) {
                            if (/size|model|selected|variant|displayed/i.test(k)) {
                                let val = vm.$data[k];
                                interesting[k] = (typeof val === 'object' ? JSON.stringify(val).substring(0,120) : String(val));
                            }
                        }
                        if (Object.keys(interesting).length) out[name] = interesting;
                    }
                    v = v.parentElement;
                }
                return out;
            }
        """)
        print("\n=== 弹窗组件 Vue data (size/model/selected) ===")
        print(data)

        # 3) 尝试原生 JS 触发 change，看按钮 + Vue 数据
        print("\n=== 原生 JS 触发尺寸选择 ===")
        r = await page.evaluate("""
            () => {
                const sel = document.querySelector('#displayedModelList');
                sel.selectedIndex = 1;
                sel.dispatchEvent(new Event('change', {bubbles: true}));
                sel.dispatchEvent(new Event('input', {bubbles: true}));
                return sel.selectedIndex;
            }
        """)
        await asyncio.sleep(2)
        disabled = await page.evaluate("""
            () => { const bs=document.querySelectorAll('.lv-loading-button');
                for(const b of bs) if((b.innerText||'').includes('在庫状況を見る')) return b.disabled; return 'NO_BTN'; }
        """)
        print(f"原生change后 selectedIndex={r}, 按钮disabled={disabled}")

        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())