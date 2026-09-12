"""方案A v19：点击底部按钮后轮询检测门店列表 + 捕获所有网络请求。

用法：venv/bin/python3.11 -m crawler.lv_diag_v19 <SKU> <城市>
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
        if "json" in ct or "javascript" in ct:
            body = ""
            try:
                body = (await resp.text())[:2000]
            except Exception:
                body = ""
            REQUESTS.append({"t": "RESP", "url": url, "status": resp.status, "ct": ct, "body": body})
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

        # 底部按钮状态
        fb = await page.evaluate(r"""
            () => {
                const b = document.querySelector('.lv-modal__footer button');
                return b ? {disabled: b.disabled, text:(b.innerText||'').trim()} : null;
            }
        """)
        print(f"底部按钮: {fb}")

        REQUESTS.clear()

        if fb and not fb['disabled']:
            print("\n=== 点击'在庫状況を見る' ===")
            try:
                await page.locator(".lv-modal__footer button").first.click(timeout=5000)
                print("已点击")
            except Exception as e:
                print(f"点击异常: {str(e).split(chr(10))[0]}")
                await page.evaluate("() => { const b=document.querySelector('.lv-modal__footer button'); if(b) b.click(); }")
                print("已用JS点击")

            # 轮询检测 second-step 弹窗
            for round_ in range(8):
                await asyncio.sleep(3)
                st = await page.evaluate(r"""
                    () => {
                        const second = document.querySelector('.lv-locate-in-store__second-step-modal');
                        if (!second) {
                            // 检查整个弹窗文本
                            const m = document.querySelector('.-sidepanel.lv-locate-in-store');
                            return {second:false, modaltext:(m?m.innerText:'').substring(0,200)};
                        }
                        const cards = second.querySelectorAll('.lv-store-card-detailed');
                        const out = [];
                        for (const c of cards) {
                            out.push({
                                n: (c.querySelector('.lv-store-card-detailed__name')?.innerText||'').trim(),
                                i: (c.querySelector('.lv-store-card-detailed__info')?.innerText||'').trim().substring(0,80),
                                s: (c.querySelector('.lv-store-card-detailed__stock')?.innerText||'').trim().substring(0,30)
                            });
                        }
                        return {second:true, cards:out, text: second.innerText.substring(0,150)};
                    }
                """)
                print(f"[轮询{round_+1}] second={st.get('second')} 卡片={len(st.get('cards',[]))}")
                if st.get('second') and st.get('cards'):
                    print(f"  文本: {st.get('text')}")
                    for s_ in st.get('cards')[:10]:
                        print(f"    - {s_['n']} | {s_['i']} | [{s_['s']}]")
                    break
                elif st.get('second'):
                    print(f"  (无卡片) 文本: {st.get('text')}")
            else:
                print("  8轮后仍无second-step")
        else:
            print("底部按钮不可用，跳过")

        print(f"\n=== 网络请求 ({len(REQUESTS)} 条) ===")
        for r_ in REQUESTS:
            print(f"  [RESP {r_['status']} {r_['ct']}] {r_['url']}")
            if r_['body']:
                print(f"      BODY: {r_['body'][:400]}")

        html = await page.evaluate("document.documentElement.outerHTML")
        OUT_DIR.joinpath(f"v19_{sku}_{city}.html").write_text(html, encoding="utf-8")

        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())