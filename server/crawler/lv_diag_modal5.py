"""完整模拟人工操作 + 完整网络监听，定位库存/地址补全 API。

流程：选尺寸 → 输入地址触发补全 → 点击补全项 → 点击"在庫状況を見る" → dump 门店。
用法：cd server && env -u HTTP_PROXY -u HTTPS_PROXY -u http_proxy -u https_proxy -u ALL_PROXY -u all_proxy \
        venv/bin/python3.11 -m crawler.lv_diag_modal5 "https://jp.louisvuitton.com/jpn-jp/products/-/M29195"
"""
import asyncio
import os
import sys

for v in ("http_proxy", "https_proxy", "HTTP_PROXY", "HTTPS_PROXY",
          "all_proxy", "ALL_PROXY"):
    os.environ.pop(v, None)

from playwright.async_api import async_playwright

PANEL_TEXT = "ストアの在庫状況を確認する"
REQUESTS = []


async def setup_network(page):
    async def on_req(req):
        url = req.url
        if "louisvuitton.com" not in url and "louisvuitton" not in url:
            return
        # 只关注 XHR/fetch
        rtype = req.resource_type
        if rtype not in ("xhr", "fetch", "document"):
            return
        REQUESTS.append({"type": "REQ", "url": url[:200], "method": req.method})

    async def on_resp(resp):
        url = resp.url
        if "louisvuitton.com" not in url and "louisvuitton" not in url:
            return
        rtype = resp.request.resource_type
        if rtype not in ("xhr", "fetch", "document"):
            return
        try:
            ct = resp.headers.get("content-type", "")
        except Exception:
            ct = ""
        body = ""
        if "json" in ct:
            try:
                body = (await resp.text())[:2000]
            except Exception:
                body = ""
        REQUESTS.append({"type": "RESP", "url": url[:200], "status": resp.status,
                         "ct": ct[:40], "body": body})

    page.on("request", on_req)
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


def print_requests(tag):
    print(f"\n--- [{tag}] 网络请求 ({len(REQUESTS)}) ---")
    for r in REQUESTS:
        print(f"  {r['type']} {r.get('status','')} {r['url']}")
        if r.get("body"):
            print(f"      BODY: {r['body'][:400]}")


async def main():
    url = sys.argv[1] if len(sys.argv) > 1 else "https://jp.louisvuitton.com/jpn-jp/products/-/M29195"
    REQUESTS.clear()
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
            print(f"导航异常: {str(e).splitlines()[0]}")
        await asyncio.sleep(8)
        REQUESTS.clear()
        await open_modal(page)
        print_requests("打开弹窗后")

        # 1) 选尺寸
        size_sel = page.locator("#displayedModelList")
        if await size_sel.count() > 0:
            await size_sel.select_option(index=1)
            await asyncio.sleep(3)
            btn_dis = await page.locator(".lv-loading-button:has-text('在庫状況を見る')").get_attribute("disabled")
            print(f"\n选尺寸后 在庫状況を見る disabled={btn_dis}")
        await asyncio.sleep(1)

        # 2) 输入地址
        print("\n=== 输入'東京'触发补全 ===")
        inp = page.locator("#address-search-input")
        await inp.click(timeout=3000)
        await asyncio.sleep(0.5)
        await inp.type("東京", delay=150)
        await asyncio.sleep(4)
        print_requests("输入'東京'后")

        # dump 补全建议
        sugg = await page.evaluate("""
            () => {
                const sels = ['[class*="suggestion"]', '[class*="autocomplete"]', '[class*="predict"]',
                              '[role="listbox"]', '[role="option"]', '[class*="result"]', '[class*="dropdown"]'];
                const out = [];
                for (const sel of sels) {
                    const els = document.querySelectorAll(sel);
                    for (const el of els) {
                        const r = el.getBoundingClientRect();
                        if (r.width>0 && r.height>0) {
                            out.push({sel, text:(el.innerText||'').substring(0,80), cls:(typeof el.className==='string'?el.className:'').substring(0,50)});
                        }
                    }
                }
                return out.slice(0,15);
            }
        """)
        print(f"补全建议元素: {len(sugg)}")
        for s in sugg[:12]:
            print(f"  [{s['sel']}] {s['text']} | {s['cls']}")

        # 3) 点击'在庫状況を見る'
        print("\n=== 点击'在庫状況を見る' ===")
        see = page.locator(".lv-loading-button:has-text('在庫状況を見る')")
        if await see.count() > 0:
            dis = await see.first.get_attribute("disabled")
            print(f"应用前 disabled={dis}")
            if dis is None:
                await see.first.click(timeout=5000)
                await asyncio.sleep(8)
                print_requests("点击'在庫状況を見る'后")
            else:
                print("按钮禁用，尝试点击补全建议后重试")
        else:
            print("未找到按钮")

        # 4) dump 门店
        stores = await page.evaluate("""
            () => {
                const m = document.querySelector('.-sidepanel.lv-locate-in-store');
                const root = m || document;
                const cards = root.querySelectorAll('[class*="store-card"], [class*="store-item"], [class*="pos"], [class*="store-list"]');
                const out = [];
                for (const el of cards) {
                    const r = el.getBoundingClientRect();
                    if (r.width>0 && r.height>0) out.push((el.innerText||'').substring(0,150));
                }
                const steps = {};
                for (const s of ['first-step','second-step']) {
                    const el = root.querySelector('.lv-locate-in-store__'+s+'-modal');
                    steps[s] = el ? (el.innerText||'').substring(0,200) : 'NONE';
                }
                return {cards: out, steps};
            }
        """)
        print(f"\n门店卡片: {len(stores['cards'])}")
        for s in stores['cards'][:10]:
            print(f"  - {s}")
        print(f"steps: first={stores['steps']['first-step'][:80]!r} second={stores['steps']['second-step'][:80]!r}")

        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())