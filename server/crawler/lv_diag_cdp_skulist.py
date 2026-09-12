"""诊断：批量测试待采集SKU的 /-/ 访问，识别哪些能正常重定向、哪些无限循环。

用法：
  cd server
  venv/bin/python3.11 -m crawler.lv_diag_cdp_skulist
"""
import asyncio
import json
import os

for v in ("http_proxy", "https_proxy", "HTTP_PROXY", "HTTPS_PROXY",
          "all_proxy", "ALL_PROXY"):
    os.environ.pop(v, None)

from playwright.async_api import async_playwright

# 待采集 SKU 列表
PENDING = ["M28029", "M29195", "M46955", "M28023", "M14920", "N00205",
           "M26763", "M25783", "M27640", "M58489", "M24786", "M14723",
           "M26805", "M14743", "M25989", "M27061", "M14458", "M12940",
           "M28112", "M28618", "M26075", "M27022"]


async def main():
    async with async_playwright() as pw:
        browser = await pw.chromium.connect_over_cdp("http://127.0.0.1:9333")
        ctx = browser.contexts[0] if browser.contexts else await browser.new_context()
        page = await ctx.new_page()

        results = {}
        for sku in PENDING:
            url = f"https://jp.louisvuitton.com/jpn-jp/products/-/{sku}"
            try:
                resp = await page.goto(url, wait_until="domcontentloaded", timeout=20000)
                final = page.url
                results[sku] = {"status": resp.status if resp else "None", "final": final}
                print(f"{sku}: HTTP {results[sku]['status']} -> {final}")
                await asyncio.sleep(2)
            except Exception as e:
                err = str(e).split("\n")[0]
                met = "REDIRECT" if "REDIRECTS" in err else "OTHER"
                results[sku] = {"status": met, "final": page.url}
                print(f"{sku}: {met} {err}")
                # 出错后回到首页，重置重定向状态
                try:
                    await page.goto("https://jp.louisvuitton.com/jpn-jp/homepage",
                                    wait_until="domcontentloaded", timeout=20000)
                    await asyncio.sleep(2)
                except Exception:
                    pass

        print("\n=== 汇总 ===")
        ok = [k for k, v in results.items() if isinstance(v["status"], int) and v["status"] == 200]
        redirect = [k for k, v in results.items() if v["status"] == "REDIRECT"]
        other = [k for k, v in results.items() if v["status"] not in ("REDIRECT",) and not (isinstance(v["status"], int) and v["status"] == 200)]
        print(f"正常访问({len(ok)}): {ok}")
        print(f"重定向循环({len(redirect)}): {redirect}")
        print(f"其他({len(other)}): {other}")

        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())