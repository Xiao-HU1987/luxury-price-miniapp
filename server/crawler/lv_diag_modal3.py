"""诊断库存弹窗真实交互结构：dump 弹窗内所有 input/button/select，尝试城市文本搜索触发库存API。

用法：cd server && env -u HTTP_PROXY -u HTTPS_PROXY -u http_proxy -u https_proxy -u ALL_PROXY -u all_proxy \
        venv/bin/python3.11 -m crawler.lv_diag_modal3 "https://jp.louisvuitton.com/jpn-jp/products/-/M29195"
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
        url = resp.url
        if "louisvuitton.com" not in url and "akamai" not in url:
            return
        try:
            ct = resp.headers.get("content-type", "")
        except Exception:
            ct = ""
        body = ""
        if "json" in ct or "javascript" in ct:
            try:
                body = (await resp.text())[:800]
            except Exception:
                body = ""
        REQUESTS.append({"url": url[:180], "status": resp.status, "body": body})
    page.on("response", on_resp)


async def dump_modal_elements(page, label):
    print(f"\n===== {label}: 弹窗内所有可见表单元素 =====")
    els = await page.evaluate(r"""() => {
        const modal = document.querySelector('.lv-locate-in-store, .lv-modal__content, .-sidepanel.lv-locate-in-store');
        const root = modal || document;
        const out = [];
        const tags = 'button,input,select,a,[role="button"],[role="combobox"],[role="option"],[class*="option"]'.split(',');
        for (const tg of tags) {
            for (const el of root.querySelectorAll(tg)) {
                const rect = el.getBoundingClientRect();
                if (rect.width <= 0 || rect.height <= 0) continue;
                out.push({
                    tag: el.tagName,
                    type: el.getAttribute('type') || '',
                    ph: el.getAttribute('placeholder') || '',
                    text: (el.innerText || el.value || '').trim().replace(/\s+/g,' ').substring(0, 50),
                    cls: (el.className && typeof el.className === 'string' ? el.className : el.getAttribute('class') || '').substring(0, 70),
                    disabled: el.disabled ? true : false,
                });
            }
        }
        return out;
    }""")
    if not els:
        print("  (未找到可见表单元素)")
    for e in els:
        print(f"  <{e['tag']} type={e['type']} ph='{e['ph']}' disabled={e['disabled']} class={e['cls']}> {e['text']}")
    return els


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
            print(f"导航异常: {str(e).splitlines()[0]}")
        await asyncio.sleep(8)
        await open_modal(page)
        await asyncio.sleep(2)

        # 选择尺寸
        size_sel = page.locator("#displayedModelList")
        if await size_sel.count() > 0:
            opts = await size_sel.locator("option").all_inner_texts()
            real = [o.strip() for o in opts if "選ん" not in o]
            print(f"\n尺寸选项: {real}")
            if real:
                await size_sel.select_option(index=1)  # 用 index 而非 label
                await asyncio.sleep(3)
                sel_text = await size_sel.locator("option:checked").inner_text()
                print(f"尺寸选择后 checked option: '{sel_text}'")
        await asyncio.sleep(2)

        await dump_modal_elements(page, "打开弹窗后")

        REQUESTS.clear()

        # 尝试文本搜索：找到地址输入框
        print("\n=== 尝试输入城市'東京' ===")
        inputs = page.locator(".lv-locate-in-store input, input[placeholder*='都道府県'], input[placeholder*='住所'], input[placeholder*='検索'], .lv-address-search-form__input")
        input_count = await inputs.count()
        print(f"候选输入框数: {input_count}")
        typed = False
        for i in range(input_count):
            inp = inputs.nth(i)
            try:
                await inp.first.click(timeout=3000)
                await inp.first.fill("東京")
                typed = True
                print(f"  已在输入框[{i}]输入'東京'")
                break
            except Exception as e:
                print(f"  输入框[{i}]失败: {str(e).splitlines()[0]}")
        if not typed:
            print("  未找到可输入框")
        await asyncio.sleep(4)

        # dump 输入后网络（看补全请求）
        print(f"\n=== 输入'東京'后网络 ({len(REQUESTS)} 条) ===")
        for r in REQUESTS:
            print(f"  [RESP {r['status']}] {r['url']}")
            if r["body"] and ("東京" in r["body"] or "store" in r["url"]):
                print(f"      BODY: {r['body'][:400]}")

        # 点击"在庫状況を見る"
        print("\n=== 点击'在庫状況を見る' ===")
        see_btn = page.locator("button:has-text('在庫状況を見る')")
        if await see_btn.count() > 0:
            dis = await see_btn.first.get_attribute("disabled")
            print(f"disabled={dis}")
            if dis is None:
                try:
                    await see_btn.first.click(timeout=5000)
                    print("已点击")
                except Exception as e:
                    print(f"点击失败: {e}")
        await asyncio.sleep(8)

        print(f"\n=== 点击'在庫状況を見る'后网络 ({len(REQUESTS)} 条) ===")
        for r in REQUESTS:
            print(f"  [RESP {r['status']}] {r['url']}")
            if r["body"]:
                print(f"      BODY: {r['body'][:250]}")

        await dump_modal_elements(page, "点击'在庫状況を見る'后")

        # 检查门店卡片
        stores = await page.evaluate("""
            () => {
                const cards = document.querySelectorAll('[class*="store-card"], [class*="store-item"], [class*="pos"]');
                const out = [];
                for (const el of cards) {
                    const r = el.getBoundingClientRect();
                    if (r.width>0 && r.height>0) out.push((el.innerText||'').substring(0,120));
                }
                return out.slice(0,10);
            }
        """)
        print(f"\nDOM 门店元素: {len(stores)}")
        for s in stores:
            print(f"  - {s}")

        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())