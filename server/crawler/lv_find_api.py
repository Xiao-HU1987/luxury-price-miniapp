"""从 Nuxt JS bundle 中搜索库存/地址补全 API 端点和调用逻辑。

用法：env -u HTTP_PROXY -u HTTPS_PROXY -u http_proxy -u https_proxy -u ALL_PROXY -u all_proxy \
        venv/bin/python3.11 -m crawler.lv_find_api "https://jp.louisvuitton.com/jpn-jp/products/-/M29195"
"""
import asyncio
import os
import re
import sys

for v in ("http_proxy", "https_proxy", "HTTP_PROXY", "HTTPS_PROXY",
          "all_proxy", "ALL_PROXY"):
    os.environ.pop(v, None)

from playwright.async_api import async_playwright

PATTERNS = [
    r'availab[^"\'`]{0,80}',
    r'inventor[^"\'`]{0,80}',
    r'stock[^"\'`]{0,60}',
    r'locat(e|ion)[^"\'`]{0,80}',
    r'/api/[^"\'`]{0,80}',
    r'point-of-sale[^"\'`]{0,60}',
    r'store[^"\'`]{0,60}',
]


async def main():
    url = sys.argv[1] if len(sys.argv) > 1 else "https://jp.louisvuitton.com/jpn-jp/products/-/M29195"
    async with async_playwright() as pw:
        browser = await pw.chromium.connect_over_cdp("http://127.0.0.1:9333")
        ctx = browser.contexts[0] if browser.contexts else await browser.new_context()
        page = await ctx.new_page()
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=45000)
        except Exception:
            pass
        await asyncio.sleep(8)

        # 用 performance API 拿所有已加载 JS
        js_urls = await page.evaluate("""
            () => {
                const out = new Set();
                for (const r of performance.getEntriesByType('resource')) {
                    if (r.name.includes('.js')) out.add(r.name);
                }
                for (const s of document.querySelectorAll('script[src]')) out.add(s.src);
                return [...out].filter(u => u.includes('louisvuitton.com') || u.includes('/_nuxt/'));
            }
        """)
        print(f"JS 文件数: {len(js_urls)}")

        # 下载并搜索
        found = {}
        for js in js_urls:
            try:
                resp = await page.request.get(js, timeout=25000)
                txt = await resp.text()
            except Exception:
                continue
            fname = js.split('/')[-1]
            for pat in PATTERNS:
                for m in re.finditer(pat, txt):
                    start = max(0, m.start()-60)
                    end = min(len(txt), m.end()+60)
                    snippet = txt[start:end]
                    # 过滤明显不是库存的（普通文本）
                    if 'data-' in snippet:
                        continue
                    found.setdefault(pat, []).append((fname, snippet.replace('\n', ' ')))

        for pat, hits in found.items():
            print(f"\n===== [{pat}] {len(hits)} 命中 =====")
            seen = set()
            for fname, snippet in hits:
                key = snippet[:50]
                if key in seen:
                    continue
                seen.add(key)
                print(f"  {fname}: ...{snippet[:220]}...")
                if len(seen) >= 8:
                    break
        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())