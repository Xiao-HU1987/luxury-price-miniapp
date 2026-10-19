"""方案A v9：真实键盘输入 + 彻底转储补全下拉。

核心：用 page.keyboard.type 物理输入（最接近真人），debounce 更久等待，
转储地址输入框周边所有可见元素（含可能的下拉列表结构）。

用法：venv/bin/python3.11 -m crawler.lv_diag_store_v9 <URL> <城市>
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
REQUESTS = []


async def setup_network(page):
    async def on_resp(resp):
        url = resp.url
        if not any(k in url for k in ("louisvuitton.com", "api.louisvuitton.com")):
            return
        body = ""
        try:
            ct = resp.headers.get("content-type", "")
        except Exception:
            ct = ""
        if "json" in ct.lower():
            try:
                body = (await resp.text())[:3000]
            except Exception:
                body = ""
        REQUESTS.append({"url": url[:200], "status": resp.status, "ct": ct[:40], "body": body})
    page.on("response", on_resp)


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


async def dump_full(page, label):
    """转储地址输入框及其父级、兄弟元素的完整 outerHTML。"""
    info = await page.evaluate("""
        () => {
            const inp = document.getElementById('address-search-input');
            if (!inp) return 'NO_INPUT';
            const out = { input_html: inp.outerHTML.substring(0,800) };
            // 输入框父级向上3层
            let p = inp;
            const chain = [];
            for (let i=0;i<4 && p;i++){
                chain.push({level:i, cls:(p.className||p.tagName||'').toString().substring(0,80)});
                p = p.parentElement;
            }
            out.chain = chain;
            // 弹窗内所有可见元素（li/button/div with text）
            const modal = document.querySelector('.lv-locate-in-store');
            const vis = [];
            if (modal) {
                const els = modal.querySelectorAll('li, [role=option], button, a, [class*=listbox], [class*=dropdown], [class*=suggest], [class*=result]');
                for (const el of els) {
                    const r = el.getBoundingClientRect();
                    const t = (el.innerText||'').trim();
                    if (r.width>0 && r.height>0 && t && t.length<80) {
                        vis.push({tag:el.tagName, cls:(el.className||'').toString().substring(0,50), text:t.substring(0,60)});
                    }
                }
            }
            out.visible = vis.slice(0,30);
            return out;
        }
    """)
    print(f"\n[{label}] 输入框结构:")
    print("  HTML:", info.get("input_html"))
    print("  层级:", [f"{c['level']}:{c['cls']}" for c in info.get("chain",[])])
    print(f"  弹窗可见元素({len(info.get('visible',[]))}):")
    for v in info.get("visible",[])[:20]:
        print(f"    <{v['tag']} class={v['cls']}> {v['text']}")


async def main():
    url = sys.argv[1] if len(sys.argv) > 1 else "https://jp.louisvuitton.com/jpn-jp/products/-/M29195"
    city = sys.argv[2] if len(sys.argv) > 2 else "東京都"
    async with async_playwright() as pw:
        browser = await pw.chromium.connect_over_cdp("http://127.0.0.1:9333")
        ctx = browser.contexts[0] if browser.contexts else await browser.new_context()
        page = await ctx.new_page()
        await page.set_viewport_size({"width": 1440, "height": 900})
        await setup_network(page)

        print(f"=== 导航: {url} ===")
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=45000)
        except Exception as e:
            print(f"导航异常: {str(e).split(chr(10))[0]}")
        await asyncio.sleep(8)
        await open_modal(page)
        await select_size(page)
        await dump_full(page, "打开弹窗后")

        inp = page.locator("#address-search-input")
        if await inp.count() == 0:
            print("未找到地址输入框"); await browser.close(); return
        await inp.click(timeout=5000)

        print(f"\n=== 真实键盘输入: {city} ===")
        REQUESTS.clear()
        await page.keyboard.type(city, delay=180)
        # debounce 等待，分多次检查
        for i in range(6):
            await asyncio.sleep(2)
            print(f"-- 等待 {2*(i+1)}s --")
            await dump_full(page, f"输入后{2*(i+1)}s")
            if len(REQUESTS) > 0:
                break
        print(f"\n网络请求: {len(REQUESTS)}")
        for r in REQUESTS:
            print(f"  [RESP {r['status']}] {r['ct']} {r['url']}")
            if r["body"]:
                print(f"      BODY: {r['body'][:400]}")

        # 转储完整DOM
        html = await page.evaluate("document.documentElement.outerHTML")
        OUT_DIR.joinpath("v9_keyboard.html").write_text(html, encoding="utf-8")
        print("\n已转储 v9_keyboard.html")

        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())