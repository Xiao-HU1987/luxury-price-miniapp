"""方案A v5：聚焦地理位置搜索 + 网络监听。

路径：选尺寸 → 点击"現在地で検索"(.lv-store-geolocation__get-button) → 监听库存API → 检查DOM门店。

用法：venv/bin/python3.11 -m crawler.lv_diag_store_real <SKU或URL>
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
        body = ""
        if "json" in ct or "javascript" in ct:
            try:
                body = (await resp.text())[:1000]
            except Exception:
                body = ""
        REQUESTS.append({"url": url[:170], "status": resp.status, "body": body})
    page.on("response", on_resp)


async def dump_modal(page, name):
    txt = await page.evaluate("""
        () => {
            const m = document.querySelector('.-sidepanel.lv-locate-in-store');
            return m ? (m.innerText||'').substring(0, 600) : 'NO_MODAL';
        }
    """)
    print(f"\n[{name}] 弹窗文本:\n{txt}")
    html = await page.evaluate("document.documentElement.outerHTML")
    OUT_DIR.joinpath(f"{name}.html").write_text(html, encoding="utf-8")


async def open_modal(page):
    # 用 JS 展开「ストアの在庫状況を確認する」面板（无视视口）
    expanded = await page.evaluate("""(txt) => {
        const panels = document.querySelectorAll('.lv-expandable-panel');
        for (const p of panels) {
            if ((p.innerText||'').includes(txt)) {
                const btn = p.querySelector('button[aria-expanded]');
                if (btn && btn.getAttribute('aria-expanded') !== 'true') {
                    btn.click();
                    return 'expanded_click';
                }
                if (btn) return 'already_expanded';
            }
        }
        return 'panel_not_found';
    }""", PANEL_TEXT)
    print(f"展开面板: {expanded}")
    await asyncio.sleep(2)

    # 用 JS 点击「ストアの在庫状況」按钮打开弹窗
    opened = await page.evaluate("""() => {
        const btn = document.querySelector('.lv-product-locate-in-store__container');
        if (btn) { btn.click(); return 'clicked'; }
        return 'not_found';
    }""")
    print(f"打开弹窗按钮: {opened}")
    await asyncio.sleep(5)


async def main():
    url = sys.argv[1] if len(sys.argv) > 1 else "https://jp.louisvuitton.com/jpn-jp/products/-/M29195"
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

        # 选择尺寸
        print("\n=== 选择尺寸 ===")
        size_sel = page.locator("#displayedModelList")
        if await size_sel.count() > 0:
            opts = await size_sel.locator("option").all_inner_texts()
            real = [o.strip() for o in opts if "選ん" not in o]
            print(f"尺寸: {real}")
            if real:
                await size_sel.select_option(label=real[0])
                await asyncio.sleep(3)
                # 确认选择后值
                sel_val = await size_sel.input_value()
                print(f"尺寸选择后 value='{sel_val}'")

        # 授予地理位置
        try:
            await ctx.grant_permissions(['geolocation'])
            await ctx.set_geolocation({"latitude": 35.6762, "longitude": 139.6503})
            print("已设置地理位置=東京(35.6762,139.6503)")
        except Exception as e:
            print(f"设置地理位置异常: {e}")
        await asyncio.sleep(2)

        REQUESTS.clear()

        # 点击"現在地で検索"
        print("\n=== 点击'現在地で検索' ===")
        geo = page.locator(".lv-store-geolocation__get-button")
        if await geo.count() > 0:
            dis = await geo.first.get_attribute("disabled")
            print(f"disabled={dis}")
            if dis is None:
                try:
                    await geo.first.click(timeout=5000)
                    print("已点击現在地で検索")
                except Exception as e:
                    print(f"点击失败: {e}")
        await asyncio.sleep(8)
        await dump_modal(page, "after_geo")

        print(f"\n=== 点击后网络 ({len(REQUESTS)} 条) ===")
        for r in REQUESTS:
            print(f"  [RESP {r['status']}] {r['url']}")
            if r["body"]:
                print(f"      BODY: {r['body'][:400]}")

        # 检查门店元素
        stores = await page.evaluate("""
            () => {
                const cards = document.querySelectorAll('[class*="store-card"], [class*="store-item"], [class*="pos"], [class*="store-list"]');
                const out = [];
                for (const el of cards) {
                    const r = el.getBoundingClientRect();
                    if (r.width>0 && r.height>0) {
                        out.push({text: (el.innerText||'').substring(0,100), cls: (el.className||'').substring(0,60)});
                    }
                }
                return out.slice(0,10);
            }
        """)
        print(f"\nDOM 门店元素: {len(stores)}")
        for s in stores:
            print(f"  - {s['text']} | {s['cls']}")

        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())