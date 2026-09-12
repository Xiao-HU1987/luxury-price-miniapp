"""方案A v29：捕获所有网络请求，定位地址补全API和门店库存API。

流程：开弹窗 → 输入 #address-search-input → 捕获全部lvv/api请求 → 点搜索按钮 → 提取门店。
用法：venv/bin/python3.11 -m crawler.lv_diag_v29 <SKU|URL> [城市]
"""
import asyncio
import os
import sys

for v in ("http_proxy", "https_proxy", "HTTP_PROXY", "HTTPS_PROXY",
          "all_proxy", "ALL_PROXY"):
    os.environ.pop(v, None)

from playwright.async_api import async_playwright

REQUESTS = []
CONSOLE = []


async def setup(page):
    async def on_resp(resp):
        url = resp.url
        if ("louisvuitton.com" in url or "api." in url) and not any(
                x in url for x in (".js", ".css", ".png", ".jpg", ".webp", ".gif",
                                   ".svg", ".woff", ".woff2", "doubleclick", "googletagmanager",
                                   "teads", "contentsquare", "yahoo", "mpulse", "akstat")):
            body = ""
            try:
                ct = resp.headers.get("content-type", "")
                if "json" in ct:
                    body = (await resp.text())[:2000]
            except Exception:
                pass
            REQUESTS.append({"url": url[:220], "status": resp.status, "ct": ct, "body": body})
    page.on("response", on_resp)

    def on_console(msg):
        if msg.type in ("error", "warning"):
            CONSOLE.append(f"[{msg.type}] {msg.text[:200]}")
    page.on("console", on_console)


async def open_modal(page):
    await page.evaluate("""(txt) => {
        const ps = document.querySelectorAll('.lv-expandable-panel');
        for (const p of ps) {
            if ((p.innerText||'').includes(txt)) {
                const b = p.querySelector('button[aria-expanded]');
                if (b && b.getAttribute('aria-expanded') !== 'true') b.click();
                break;
            }
        }
    }""", "ストアの在庫状況を確認する")
    await asyncio.sleep(2)
    await page.evaluate("""() => {
        const b = document.querySelector('.lv-product-locate-in-store__container');
        if (b) b.click();
    }""")
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
        await setup(page)

        print(f"=== 导航: {url} ===")
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=45000)
        except Exception as e:
            print(f"导航异常: {str(e).split(chr(10))[0]}")
        await asyncio.sleep(8)
        await open_modal(page)

        # 检查初始状态
        ini = await page.evaluate("""() => {
            const btn = document.querySelector('.lv-address-search-form__button');
            return {disabled: btn? btn.disabled : 'N/A', loading: btn? (btn.innerHTML||'').includes('lv-loader') : 'N/A'};
        }""")
        print(f"初始搜索按钮: {ini}")

        # 输入城市
        REQUESTS.clear()
        print(f"\n=== 输入: {city} ===")
        inp = page.locator("#address-search-input")
        await inp.first.click()
        await inp.first.fill("")
        for ch in city:
            await inp.first.type(ch, delay=150)
            await asyncio.sleep(0.3)
        await asyncio.sleep(4)

        btn_state = await page.evaluate("""() => {
            const btn = document.querySelector('.lv-address-search-form__button');
            return {disabled: btn? btn.disabled : 'N/A', loading: (btn&&(btn.innerHTML||'').includes('lv-loader'))};
        }""")
        print(f"输入后按钮: {btn_state}")

        print(f"\n=== 输入期间请求 ({len(REQUESTS)} 条) ===")
        for r in REQUESTS:
            print(f"  [RESP {r['status']}] {r['url']}")
            if r["body"]:
                print(f"      BODY: {r['body'][:400]}")

        # 自动补全建议
        sugg = await page.evaluate("""() => {
            const out = [];
            const sels = document.querySelectorAll('[role="option"], ul[class*=suggest] li, [class*=suggestion] li, [class*=autocomplete] li, .lv-address-search-form__suggestion [class*=item]');
            for (const el of sels) {
                const r = el.getBoundingClientRect();
                if (r.width>0 && r.height>0) out.push((el.innerText||'').trim().substring(0,80));
            }
            return out.slice(0,15);
        }""")
        print(f"\n自动补全 ({len(sugg)}):")
        for s in sugg:
            print(f"  - {s}")

        # 点击搜索按钮（仅图标按钮）
        await page.evaluate("""() => {
            const btn = document.querySelector('.lv-address-search-form__button');
            if (btn && !btn.disabled) btn.click();
        }""")
        await asyncio.sleep(6)

        print(f"\n=== 点击搜索后请求 ({len(REQUESTS)} 条) ===")
        for r in REQUESTS:
            print(f"  [RESP {r['status']}] {r['url']}")
            if r["body"]:
                print(f"      BODY: {r['body'][:400]}")

        # 提取门店
        mtxt = await page.evaluate("""() => {
            const m = document.querySelector('.lv-store-geolocation');
            return m ? (m.innerText||'').substring(0,1500) : 'NO_MODAL';
        }""")
        print(f"\n=== 门店区域文本 ===\n{mtxt}")

        print(f"\n=== 控制台 ===  {len(CONSOLE)} 条")
        for c in CONSOLE[:20]:
            print(f"  {c}")

        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())