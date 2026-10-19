"""方案A v20：点击底部按钮后转储弹窗完整状态 + 检查补全建议和错误。

用法：venv/bin/python3.11 -m crawler.lv_diag_v20 <SKU> <城市>
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

        print(f"=== 导航 {sku} ===")
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
            print(f"\n尺寸: {real}")
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

        # 输入城市
        print(f"\n=== 输入 '{city}' ===")
        inp = page.locator("#address-search-input")
        if await inp.count() > 0:
            await inp.click(timeout=5000)
            await asyncio.sleep(1)
            await inp.press_sequentially(city, delay=150)
        await asyncio.sleep(5)

        # 检查补全建议（输入后）
        sug = await page.evaluate(r"""
            () => {
                const modal = document.querySelector('.lv-modal__content, .-sidepanel.lv-locate-in-store');
                if (!modal) return {count:0, items:[]};
                const out = [];
                modal.querySelectorAll('[class*="suggestion"] li, [role="option"], [class*="option"] li').forEach(el => {
                    const r = el.getBoundingClientRect();
                    if (r.width>0 && r.height>0) out.push((el.innerText||'').trim().substring(0,100));
                });
                return {count:out.length, items:out};
            }
        """)
        print(f"输入后补全建议: {sug}")

        # 底部按钮
        fb = await page.evaluate(r"""
            () => {
                const b = document.querySelector('.lv-modal__footer button');
                return b ? {disabled: b.disabled, text:(b.innerText||'').trim()} : null;
            }
        """)
        print(f"底部按钮: {fb}")

        # 点击底部按钮
        if fb and not fb['disabled']:
            print("\n=== 点击底部按钮 ===")
            await page.locator(".lv-modal__footer button").first.click(timeout=5000)
            await asyncio.sleep(6)

        # 转储弹窗完整状态
        state = await page.evaluate(r"""
            () => {
                const m = document.querySelector('.-sidepanel.lv-locate-in-store');
                if (!m) return {modal:false};
                const out = {modal:true, text: (m.innerText||'').substring(0,1500)};
                // 所有可见按钮
                out.buttons = [];
                m.querySelectorAll('button, [role=button], input, a').forEach(el => {
                    const r = el.getBoundingClientRect();
                    if (r.width>0 && r.height>0) {
                        out.buttons.push({
                            tag: el.tagName,
                            type: el.getAttribute('type')||'',
                            text: (el.innerText||el.value||el.getAttribute('placeholder')||'').trim().substring(0,50),
                            cls: (typeof el.className==='string'?el.className:'').substring(0,50),
                            disabled: el.disabled
                        });
                    }
                });
                // 错误
                out.errors = [];
                m.querySelectorAll('[role=alert], .lv-field-error, [class*="error"]').forEach(el => {
                    const t = (el.innerText||'').trim();
                    if (t) out.errors.push(t.substring(0,100));
                });
                return out;
            }
        """)
        print(f"\n=== 点击后弹窗状态 ===")
        print(f"modal={state.get('modal')}")
        print(f"文本: {state.get('text')}")
        print(f"\n可见控件 ({len(state.get('buttons',[]))}):")
        for b in state.get('buttons', []):
            print(f"  <{b['tag']} type={b['type']} disabled={b['disabled']} class={b['cls']}> {b['text']}")
        print(f"\n错误: {state.get('errors')}")

        html = await page.evaluate("document.documentElement.outerHTML")
        OUT_DIR.joinpath(f"v20_{sku}_{city}.html").write_text(html, encoding="utf-8")

        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())