"""Dump 页面所有 JS 资源 URL，供分析地址补全/库存 API 使用。

用法：env -u HTTP_PROXY -u HTTPS_PROXY -u http_proxy -u https_proxy -u ALL_PROXY -u all_proxy \
        venv/bin/python3.11 -m crawler.lv_diag_scripts "https://jp.louisvuitton.com/jpn-jp/products/-/M29195"
"""
import asyncio
import os
import sys

for v in ("http_proxy", "https_proxy", "HTTP_PROXY", "HTTPS_PROXY",
          "all_proxy", "ALL_PROXY"):
    os.environ.pop(v, None)

from playwright.async_api import async_playwright


async def main():
    url = sys.argv[1] if len(sys.argv) > 1 else "https://jp.louisvuitton.com/jpn-jp/products/-/M29195"
    async with async_playwright() as pw:
        browser = await pw.chromium.connect_over_cdp("http://127.0.0.1:9333")
        ctx = browser.contexts[0] if browser.contexts else await browser.new_context()
        page = await ctx.new_page()
        try:
            await page.goto(url, wait_until="networkidle", timeout=60000)
        except Exception as e:
            print(f"导航异常: {str(e).splitlines()[0]}")
        await asyncio.sleep(5)

        scripts = await page.evaluate("""
            () => {
                const out = new Set();
                for (const s of document.querySelectorAll('script[src]')) out.add(s.src);
                for (const l of document.querySelectorAll('link[href]')) {
                    const href = l.href;
                    if (href.includes('.js') || href.includes('modulepreload')) out.add(href);
                }
                return [...out];
            }
        """)
        print(f"=== 页面脚本/预加载资源 ({len(scripts)}) ===")
        for s in sorted(scripts):
            print(s)

        # 抓取所有 JS 内容，搜索库存/地址关键字
        import re
        keywords = ["availab", "inventory", "\bstock\b", "store", "locat", "geoloc",
                    "address.search", "autocomplete", "typeahead", "suggest", "/api/"]
        hits = {}
        for s in scripts:
            if ".js" not in s:
                continue
            try:
                resp = await page.request.get(s, timeout=20000)
                txt = await resp.text()
            except Exception:
                continue
            for kw in keywords:
                if kw in txt:
                    hits.setdefault(kw, []).append((s, txt.count(kw)))
        print("\n=== JS 内关键字命中 ===")
        for kw, v in hits.items():
            print(f"\n[{kw}]")
            for s, cnt in v[:15]:
                print(f"  {cnt:4d}  {s}")

        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())