"""方案A v13：诊断地址补全服务 + 提交后弹窗状态。

检查：
1. 地址搜索框的 autocomplete 是否依赖外部地理编码服务（Google/Maplox）
2. 提交按钮点击后弹窗切换到什么状态
3. 尝试输入完整地址格式

用法：venv/bin/python3.11 -m crawler.lv_diag_store_v13 <URL> <城市>
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
OUT_DIR.mkdir(exist_ok=True)


async def open_modal(page):
    # 用 JS 展开面板并点击库存按钮（比 Playwright click 更稳定）
    await page.evaluate(r"""
        () => {
            const panels = document.querySelectorAll('.lv-expandable-panel');
            for (const p of panels) {
                if ((p.innerText||'').includes('ストアの在庫状況を確認する')) {
                    const btn = p.querySelector('button[aria-expanded]');
                    if (btn && btn.getAttribute('aria-expanded') !== 'true') btn.click();
                    break;
                }
            }
        }
    """)
    await asyncio.sleep(2)
    await page.evaluate(r"""
        () => {
            const btn = document.querySelector('.lv-product-locate-in-store__container');
            if (btn) btn.click();
        }
    """)
    await asyncio.sleep(5)


async def select_size(page):
    size_sel = page.locator("#displayedModelList")
    if await size_sel.count() > 0:
        opts = await size_sel.locator("option").all_inner_texts()
        real = [o.strip() for o in opts if "サイズを選んで" not in o]
        if real:
            await size_sel.select_option(label=real[0])
            await asyncio.sleep(2)


async def main():
    url = sys.argv[1] if len(sys.argv) > 1 else "https://jp.louisvuitton.com/jpn-jp/products/-/M29195"
    city = sys.argv[2] if len(sys.argv) > 2 else "東京都"
    async with async_playwright() as pw:
        browser = await pw.chromium.connect_over_cdp("http://127.0.0.1:9333")
        ctx = browser.contexts[0] if browser.contexts else await browser.new_context()
        page = await ctx.new_page()
        await page.set_viewport_size({"width": 1440, "height": 900})

        print(f"=== 导航: {url} ===")
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=45000)
        except Exception as e:
            print(f"导航异常: {str(e).split(chr(10))[0]}")
        await asyncio.sleep(8)
        await open_modal(page)
        await select_size(page)

        # 检查地址补全相关外部服务是否加载
        deps = await page.evaluate("""
            () => {
                const out = {};
                // 检查是否加载了地图/地理编码库
                out.googleMaps = typeof window.google !== 'undefined' && window.google.maps ? true : false;
                out.maplibre = !!document.querySelector('[class*=maplibre], [class*=mapbox]');
                out.leaflet = typeof window.L !== 'undefined';
                out.here = !!document.querySelector('script[src*=mapsjs], script[src*=here]');
                // 检查页面 script 里是否有地理编码 api key 相关
                return out;
            }
        """)
        print(f"地图/地理编码依赖: {deps}")

        # 搜索 input 的 aria/autocomplete 相关属性
        at = await page.evaluate("""
            () => {
                const inp = document.getElementById('address-search-input');
                if (!inp) return {};
                const out = {};
                for (const a of inp.attributes) out[a.name] = a.value;
                // 检查 input 的父级是否包裹了 combobox
                let p = inp;
                const chain = [];
                for (let i=0;i<5 && p;i++){ chain.push((p.tagName+'.'+(p.className||'')).substring(0,60)); p=p.parentElement; }
                out.chain = chain;
                return out;
            }
        """)
        print(f"输入框属性: {at}")

        # 输入并等待，检查 Vue 是否在 input 上绑定了 combobox
        inp = page.locator("#address-search-input")
        try:
            await inp.click(timeout=5000)
        except Exception:
            await inp.click(force=True, timeout=5000)
        await page.keyboard.type(city, delay=150)
        await asyncio.sleep(5)

        # 检查输入后 DOM 是否有 aria-expanded combobox 或新容器
        comb = await page.evaluate("""
            () => {
                const out = [];
                const els = document.querySelectorAll('[role=combobox], [aria-expanded], [aria-haspopup=listbox], [aria-controls]');
                for (const el of els) {
                    const r = el.getBoundingClientRect();
                    out.push({tag: el.tagName, id: el.id||'', role: el.getAttribute('role')||'',
                              expanded: el.getAttribute('aria-expanded')||'',
                              cls: (el.className||'').toString().substring(0,50),
                              vis: r.width>0&&r.height>0});
                }
                return out.slice(0,20);
            }
        """)
        print(f"combobox/aria 元素({len(comb)}):")
        for c in comb:
            print(f"   <{c['tag']}#{c['id']} role={c['role']} exp={c['expanded']} vis={c['vis']} class={c['cls']}>")

        # 提交按钮状态
        submit = page.locator(".lv-modal__footer button")
        if await submit.count() > 0:
            print(f"提交按钮 disabled={await submit.first.get_attribute('disabled')}")

        # 地址搜索按钮（form内）
        btn = page.locator(".lv-address-search-form__button")
        if await btn.count() > 0:
            print(f"地址搜索钮 disabled={await btn.first.get_attribute('disabled')}")

        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())