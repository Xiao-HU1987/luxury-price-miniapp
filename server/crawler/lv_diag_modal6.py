"""诊断：不过滤域名监听所有 XHR/fetch，定位地址补全 API；用 DOM property 确认按钮状态。

用法：cd server && env -u HTTP_PROXY -u HTTPS_PROXY -u http_proxy -u https_proxy -u ALL_PROXY -u all_proxy \
        venv/bin/python3.11 -m crawler.lv_diag_modal6 "https://jp.louisvuitton.com/jpn-jp/products/-/M29195"
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
    async def on_resp(resp):
        rtype = resp.request.resource_type
        if rtype not in ("xhr", "fetch"):
            return
        try:
            ct = resp.headers.get("content-type", "")
        except Exception:
            ct = ""
        body = ""
        if "json" in ct or "javascript" in ct:
            try:
                body = (await resp.text())[:1500]
            except Exception:
                body = ""
        REQUESTS.append({"url": resp.url[:200], "status": resp.status, "ct": ct[:40], "body": body})
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


def btn_state(page):
    """用 DOM property 读取'在庫状況を見る'按钮真实状态。"""
    return page.evaluate("""
        () => {
            const btns = document.querySelectorAll('.lv-loading-button');
            let btn = null;
            for (const b of btns) {
                if ((b.innerText||'').includes('在庫状況を見る')) { btn = b; break; }
            }
            if (!btn) return 'NO_BTN';
            return 'disabled=' + btn.disabled + ' ariaDisabled=' + btn.getAttribute('aria-disabled');
        }
    """)


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
        print(f"打开弹窗后 按钮: {await btn_state(page)}")

        # 选尺寸
        size_sel = page.locator("#displayedModelList")
        if await size_sel.count() > 0:
            await size_sel.select_option(index=1)
            await asyncio.sleep(2)
            print(f"选尺寸后 按钮: {await btn_state(page)}")
            # 检查 select 的 value 和 Vue 状态
            info = await page.evaluate("""() => {
                const s = document.querySelector('#displayedModelList');
                const opt = s.options[s.selectedIndex];
                return {value: s.value, selText: opt?opt.text:'', selValue: opt?opt.value:''};
            }""")
            print(f"select选中: {info}")

        # 输入地址，监听所有请求
        REQUESTS.clear()
        print("\n=== 输入'東京' ===")
        inp = page.locator("#address-search-input")
        await inp.click(timeout=3000)
        await asyncio.sleep(0.5)
        await inp.type("東京", delay=200)
        await asyncio.sleep(5)
        print(f"输入后 按钮: {await btn_state(page)}")
        print(f"\n--- 输入'東京'后所有XHR/fetch ({len(REQUESTS)}) ---")
        for r in REQUESTS:
            print(f"  [{r['status']}] {r['ct']} {r['url']}")
            if r["body"]:
                print(f"      BODY: {r['body'][:300]}")

        # dump 补全建议
        sugg = await page.evaluate("""
            () => {
                const all = document.querySelectorAll('li, [role="option"], [class*="suggestion"], [class*="autocomplete"], [class*="predict"], [class*="result"], [class*="dropdown"]');
                const out=[];
                for (const el of all) {
                    const r=el.getBoundingClientRect();
                    if(r.width>0&&r.height>0){const t=(el.innerText||'').trim(); if(t) out.push(t.substring(0,60));}
                }
                return out.slice(0,15);
            }
        """)
        print(f"补全建议: {sugg}")
        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())