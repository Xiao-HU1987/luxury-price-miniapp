"""方案A v12：输入城市→提交→转储 second-step 弹窗完整 innerHTML。

验证提交后门店列表组件是否真正渲染，提取门店名称/地址/库存状态。

用法：venv/bin/python3.11 -m crawler.lv_diag_store_v12 <URL> <城市>
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

        inp = page.locator("#address-search-input")
        if await inp.count() == 0:
            print("未找到地址输入框"); await browser.close(); return
        await inp.click(timeout=5000)
        await page.keyboard.type(city, delay=150)
        await asyncio.sleep(4)

        submit = page.locator(".lv-modal__footer button")
        dis = await submit.first.get_attribute("disabled") if await submit.count() > 0 else "NONE"
        print(f"提交按钮 disabled={dis}")
        if dis != "NONE" and dis is not None:
            print("提交按钮禁用，尝试点击补全建议")
            await page.evaluate("""
                () => {
                    const sels = ['[role=option]','[class*=suggest] li','[class*=dropdown] li',
                                  '[class*=listbox] li','[class*=result] li'];
                    for (const sel of sels) {
                        for (const el of document.querySelectorAll(sel)) {
                            if (el.getBoundingClientRect().width>0) { el.click(); return; }
                        }
                    }
                }
            """)
            await asyncio.sleep(3)
            dis = await submit.first.get_attribute("disabled") if await submit.count() > 0 else "NONE"
            print(f"点击建议后提交按钮 disabled={dis}")

        if dis is None:
            try:
                await submit.first.click(timeout=8000)
                print("已点击提交")
            except Exception as e:
                print(f"点击提交失败: {e}")
        else:
            print("无法提交")
            await browser.close(); return

        # 等待 second-step 渲染，逐步检查
        for i in range(8):
            await asyncio.sleep(3)
            state = await page.evaluate("""
                () => {
                    const second = document.querySelector('.lv-locate-in-store__second-step-modal');
                    if (!second) return {found:false};
                    const cards = second.querySelectorAll('.lv-store-card-detailed');
                    const vis = [];
                    for (const c of cards) {
                        const r = c.getBoundingClientRect();
                        if (r.width>0 && r.height>0) vis.push(c);
                    }
                    const text = (second.innerText||'').trim().substring(0,300);
                    return {found:true, cards:cards.length, vis:vis.length, text:text};
                }
            """)
            print(f"-- 等待{3*(i+1)}s: {state}")
            if state.get("found") and (state.get("cards")>0 or "見つかりません" in state.get("text","") or "在庫" in state.get("text","")):
                break

        # 转储 second-step 完整 HTML
        html = await page.evaluate("""
            () => {
                const second = document.querySelector('.lv-locate-in-store__second-step-modal');
                return second ? second.outerHTML : 'NO_SECOND';
            }
        """)
        OUT_DIR.joinpath(f"v12_second_{city}.html").write_text(html, encoding="utf-8")
        print(f"\n已转储 v12_second_{city}.html (len={len(html)})")

        # 提取门店数据
        stores = await page.evaluate("""
            () => {
                const second = document.querySelector('.lv-locate-in-store__second-step-modal');
                if (!second) return [];
                const cards = second.querySelectorAll('.lv-store-card-detailed');
                const out = [];
                for (const card of cards) {
                    const r = card.getBoundingClientRect();
                    if (r.width<=0) continue;
                    const name = card.querySelector('.lv-store-card-detailed__name');
                    const info = card.querySelector('.lv-store-card-detailed__info');
                    const stock = card.querySelector('.lv-store-card-detailed__stock');
                    out.push({
                        name: name ? name.innerText.trim() : '',
                        info: info ? info.innerText.trim().replace(/\\n/g,' ') : '',
                        stock: stock ? stock.innerText.trim() : ''
                    });
                }
                return out.slice(0,10);
            }
        """)
        print(f"\n门店({len(stores)}):")
        for s in stores:
            print(f"  - {s['name']} | 地址:{s['info'][:50]} | 库存:{s['stock']}")

        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())