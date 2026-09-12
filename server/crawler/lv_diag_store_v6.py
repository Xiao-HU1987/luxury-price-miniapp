"""方案A v6：走完整地址搜索流程（输入城市→自动补全→提交→门店列表）。

核心：监听所有网络请求，找出触发门店库存数据的 API；
并验证「在庫状況を見る」提交按钮在选中位置后是否可用、点击后 DOM 是否出现门店卡片。

用法：venv/bin/python3.11 -m crawler.lv_diag_store_v6 <SKU或URL>
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
        # 收集所有请求，重点找搜索/库存 API
        body = ""
        try:
            ct = resp.headers.get("content-type", "")
        except Exception:
            ct = ""
        if "json" in ct.lower() or "javascript" in ct.lower():
            try:
                body = (await resp.text())[:1500]
            except Exception:
                body = ""
        REQUESTS.append({"url": url[:200], "status": resp.status,
                         "ct": ct[:40], "body": body})
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
        print(f"尺寸选项: {real}")
        if real:
            await size_sel.select_option(label=real[0])
            await asyncio.sleep(2)
            print(f"已选择尺寸: {real[0]}")


async def search_city(page, city):
    """输入城市名 → 等待自动补全 → 选择第一个建议。返回是否成功。"""
    inp = page.locator("#address-search-input")
    if await inp.count() == 0:
        print("未找到地址搜索输入框")
        return False
    await inp.click(timeout=5000)
    await inp.fill("")
    await asyncio.sleep(0.5)
    before = len(REQUESTS)
    await inp.type(city, delay=120)
    print(f"已输入城市: {city}")
    await asyncio.sleep(4)

    # 检查自动补全下拉
    sugg = await page.evaluate("""
        () => {
            // 常见补全容器
            const sels = ['[role="listbox"]', '[role="option"]',
                          '[class*="suggestion"]', '[class*="autocomplete"]',
                          '[class*="lv-suggest"]', '[class*="lv-address"]'];
            const out = [];
            for (const sel of sels) {
                const els = document.querySelectorAll(sel);
                for (const el of els) {
                    const r = el.getBoundingClientRect();
                    if (r.width>0 && r.height>0) {
                        out.push({sel: sel, text: (el.innerText||'').trim().substring(0,80)});
                    }
                }
            }
            return out.slice(0, 20);
        }
    """)
    print(f"自动补全元素: {len(sugg)}")
    for s in sugg:
        print(f"  [{s['sel']}] {s['text']}")

    # 报告此期间的新网络请求
    new_reqs = REQUESTS[before:]
    print(f"输入期间新增请求: {len(new_reqs)}")
    for r in new_reqs:
        print(f"  [RESP {r['status']}] {r['ct']} {r['url']}")
        if r["body"]:
            print(f"      BODY: {r['body'][:500]}")

    return True


async def main():
    url = sys.argv[1] if len(sys.argv) > 1 else "https://jp.louisvuitton.com/jpn-jp/products/-/M29195"
    city = sys.argv[2] if len(sys.argv) > 2 else "東京"
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
        await search_city(page, city)

        # 检查提交按钮是否可用
        submit = page.locator(".lv-modal__footer button")
        if await submit.count() > 0:
            dis = await submit.first.get_attribute("disabled")
            print(f"\n提交按钮 disabled={dis}")
            if dis is None:
                before2 = len(REQUESTS)
                try:
                    await submit.first.click(timeout=8000)
                    print("已点击「在庫状況を見る」")
                except Exception as e:
                    print(f"点击提交失败: {e}")
                await asyncio.sleep(8)
                new2 = REQUESTS[before2:]
                print(f"\n提交后新增请求: {len(new2)}")
                for r in new2:
                    print(f"  [RESP {r['status']}] {r['ct']} {r['url']}")
                    if r["body"]:
                        print(f"      BODY: {r['body'][:600]}")
                # 转储弹窗
                html = await page.evaluate("document.documentElement.outerHTML")
                OUT_DIR.joinpath("v6_after_submit.html").write_text(html, encoding="utf-8")
                print("\n已转储 v6_after_submit.html")
                # 门店卡片
                stores = await page.evaluate("""
                    () => {
                        const cards = document.querySelectorAll('.lv-store-card-detailed');
                        const out = [];
                        for (const el of cards) {
                            const r = el.getBoundingClientRect();
                            if (r.width>0 && r.height>0) {
                                out.push((el.innerText||'').substring(0,120).replace(/\\n/g,' | '));
                            }
                        }
                        return out.slice(0,10);
                    }
                """)
                print(f"\n门店卡片: {len(stores)}")
                for s in stores:
                    print(f"  - {s}")
            else:
                print("提交按钮仍禁用，无法提交")

        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())