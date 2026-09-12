"""聚焦 Nuxt JS：搜索库存/地址补全 API 调用逻辑。

用法：env -u HTTP_PROXY -u HTTPS_PROXY -u http_proxy -u https_proxy -u ALL_PROXY -u all_proxy \
        venv/bin/python3.11 -m crawler.lv_diag_nuxt "https://jp.louisvuitton.com/jpn-jp/products/-/M29195"
"""
import asyncio
import os
import re
import sys

for v in ("http_proxy", "https_proxy", "HTTP_PROXY", "HTTPS_PROXY",
          "all_proxy", "ALL_PROXY"):
    os.environ.pop(v, None)

from playwright.async_api import async_playwright

KEYWORDS = ["availab", "inventor", "locat", "store", "geoloc", "address"]


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
        await asyncio.sleep(6)

        scripts = await page.evaluate("""
            () => [...document.querySelectorAll('script[src]')].map(s=>s.src)
                .filter(u => u.includes('/_nuxt/') && u.endsWith('.js'))
        """)
        print(f"Nuxt JS 文件数: {len(scripts)}")

        # 抓取所有 Nuxt JS，拼在一起搜索
        all_hits = {}
        for s in scripts:
            try:
                resp = await page.request.get(s, timeout=25000)
                txt = await resp.text()
            except Exception:
                continue
            for kw in KEYWORDS:
                # 找 kw 出现的位置，取上下文
                for m in re.finditer(kw, txt, re.IGNORECASE):
                    start = max(0, m.start()-120)
                    end = min(len(txt), m.end()+120)
                    snippet = txt[start:end]
                    # 只保留含 http/api 的片段（更可能是 API 调用）
                    if "http" in snippet or "/api" in snippet or "fetch" in snippet or "axios" in snippet or "post(" in snippet:
                        all_hits.setdefault(kw, []).append((s.split('/')[-1], snippet.replace('\n',' ')))
                        break  # 每个文件每个关键字只取一条

        for kw in KEYWORDS:
            hits = all_hits.get(kw, [])
            if not hits:
                continue
            print(f"\n===== [{kw}] {len(hits)} 个文件命中 =====")
            for fname, snippet in hits[:6]:
                print(f"\n--- {fname} ---")
                print(f"  {snippet[:260]}")

        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())