"""方案A v28：使用 #address-search-input 输入城市 → 选自动补全 → 点主按钮 → 监听库存API → 提取门店。

用法：venv/bin/python3.11 -m crawler.lv_diag_v28 <SKU或URL> [城市]
"""
import asyncio
import os
import sys

for v in ("http_proxy", "https_proxy", "HTTP_PROXY", "HTTPS_PROXY",
          "all_proxy", "ALL_PROXY"):
    os.environ.pop(v, None)

from playwright.async_api import async_playwright

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
        if "json" in ct or "search" in url or "store" in url or "availability" in url:
            body = ""
            try:
                body = (await resp.text())[:1500]
            except Exception:
                body = ""
            REQUESTS.append({"url": url[:200], "status": resp.status, "body": body})
    page.on("response", on_resp)


async def open_modal(page):
    expanded = await page.evaluate("""(txt) => {
        const panels = document.querySelectorAll('.lv-expandable-panel');
        for (const p of panels) {
            if ((p.innerText||'').includes(txt)) {
                const btn = p.querySelector('button[aria-expanded]');
                if (btn && btn.getAttribute('aria-expanded') !== 'true') btn.click();
                return 'expanded';
            }
        }
        return 'panel_not_found';
    }""", "ストアの在庫状況を確認する")
    print(f"展开面板: {expanded}")
    await asyncio.sleep(2)
    opened = await page.evaluate("""() => {
        const btn = document.querySelector('.lv-product-locate-in-store__container');
        if (btn) { btn.click(); return 'clicked'; }
        return 'not_found';
    }""")
    print(f"打开弹窗: {opened}")
    await asyncio.sleep(5)


async def main():
    args = sys.argv[1:]
    url = args[0] if args else "https://jp.louisvuitton.com/jpn-jp/products/-/M26763"
    city = args[1] if len(args) > 1 else "東京"
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

        # 输入城市
        inp = page.locator("#address-search-input")
        print(f"\n=== 输入城市: {city} ===")
        if await inp.count() == 0:
            print("未找到 #address-search-input")
        else:
            await inp.first.click()
            await inp.first.fill("")
            await inp.first.type(city, delay=120)
            await asyncio.sleep(3)

            # 转储自动补全建议
            sugg = await page.evaluate("""() => {
                const out = [];
                const sels = document.querySelectorAll('[role="option"], .lv-address-search-form__suggestion li, .lv-address-search-form__suggestion [class*=item], ul[class*=suggest] li');
                for (const el of sels) {
                    const r = el.getBoundingClientRect();
                    if (r.width>0 && r.height>0) {
                        out.push((el.innerText||'').trim().substring(0,80));
                    }
                }
                return out.slice(0,15);
            }""")
            print(f"自动补全建议 ({len(sugg)}):")
            for s in sugg:
                print(f"  - {s}")

            # 点击主按钮（在庫状況を見る）
            print("\n=== 点击主按钮(.lv-button -primary) ===")
            primary = page.locator(".lv-button.-primary, .lv-button.-primary-fullwidth, .lv-button[class*='primary']")
            print(f"主按钮数量: {await primary.count()}")
            if await primary.count() > 0:
                try:
                    await primary.last.click(timeout=5000)
                    print("已点击主按钮")
                except Exception as e:
                    print(f"点击失败: {str(e).split(chr(10))[0]}")
            await asyncio.sleep(8)

        print(f"\n=== 库存相关网络请求 ({len(REQUESTS)} 条) ===")
        for r in REQUESTS:
            print(f"  [RESP {r['status']}] {r['url']}")
            if r["body"]:
                print(f"      BODY: {r['body'][:500]}")
                print()

        # 提取门店卡片
        stores = await page.evaluate("""() => {
            const out = [];
            const sels = document.querySelectorAll('[class*="store-card"], [class*="store-item"], [class*="pos-item"], [class*="store-list"] [class*=item], [class*="locate-in-store"] [class*=result] > *, ul[class*=store] li');
            for (const el of sels) {
                const r = el.getBoundingClientRect();
                if (r.width>0 && r.height>0) {
                    out.push({text:(el.innerText||'').substring(0,120), cls:(el.className||'').substring(0,50)});
                }
            }
            return out.slice(0,15);
        }""")
        print(f"\nDOM 门店元素: {len(stores)}")
        for s in stores:
            print(f"  - [{s['cls']}] {s['text']}")

        # 转储弹窗文本
        mtxt = await page.evaluate("""() => {
            const m = document.querySelector('.-sidepanel.lv-locate-in-store, .lv-locate-in-store');
            return m ? (m.innerText||'').substring(0,1500) : 'NO_MODAL';
        }""")
        print(f"\n=== 弹窗文本 ===\n{mtxt}")

        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())