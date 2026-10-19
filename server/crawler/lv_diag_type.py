"""诊断v7：用type方法模拟键盘输入，检查补全建议和网络请求。

用法：
  cd server
  venv/bin/python3.11 -m crawler.lv_diag_type
"""
import asyncio
import os

for v in ("http_proxy", "https_proxy", "HTTP_PROXY", "HTTPS_PROXY",
          "all_proxy", "ALL_PROXY"):
    os.environ.pop(v, None)

from playwright.async_api import async_playwright, Request, Response


async def main():
    async with async_playwright() as pw:
        browser = await pw.chromium.connect_over_cdp("http://127.0.0.1:9333")
        context = browser.contexts[0] if browser.contexts else await browser.new_context()
        page = context.pages[0] if context.pages else await context.new_page()

        # 收集 LV 相关请求
        lv_requests = []
        async def on_response(resp: Response):
            url = resp.url
            if "louisvuitton" in url.lower() and not any(url.lower().endswith(ext) for ext in ('.css', '.js', '.woff', '.woff2', '.ttf', '.svg', '.ico', '.png', '.jpg', '.jpeg', '.webp', '.gif')):
                ct = (resp.headers.get("content-type") or "").lower()
                if "json" in ct or "text" in ct:
                    try:
                        body = await resp.text()
                        lv_requests.append({
                            "status": resp.status,
                            "url": url[:250],
                            "ct": ct[:30],
                            "len": len(body),
                            "body": body[:500],
                        })
                    except Exception:
                        pass

        page.on("response", on_response)

        # === 0. 导航并等待 ===
        url = "https://jp.louisvuitton.com/jpn-jp/products/-/M46955"
        print(f"=== 导航到 {url} ===")
        try:
            await page.goto(url, timeout=30_000, wait_until="commit")
        except Exception:
            await page.goto(url, timeout=60_000, wait_until="domcontentloaded")

        try:
            await page.wait_for_function(
                """() => { const e = document.querySelector('.lv-price'); return e && /[0-9]/.test(e.innerText || ''); }""",
                timeout=30_000,
            )
        except Exception:
            pass

        await page.wait_for_timeout(5000)

        # === 1. 强制展开面板 + 点击库存按钮 ===
        await page.evaluate(r"""() => {
            const panels = document.querySelectorAll('.lv-expandable-panel');
            for (const panel of panels) {
                if ((panel.innerText||'').includes('ストアの在庫状況を確認する')) {
                    const btn = panel.querySelector('button[aria-expanded]');
                    const content = panel.querySelector('.lv-expandable-panel__content');
                    if (btn) { btn.setAttribute('aria-expanded', 'true'); btn.setAttribute('aria-disabled', 'false'); }
                    if (content) { content.style.display = 'block'; content.setAttribute('aria-hidden', 'false'); }
                    return;
                }
            }
        }""")
        await page.wait_for_timeout(1000)

        try:
            locate_btn = page.locator('.lv-product-locate-in-store__container')
            if await locate_btn.count() > 0:
                await locate_btn.first.click(timeout=5000, force=True)
                print("库存按钮点击成功")
        except Exception:
            await page.evaluate(r"""() => { const b = document.querySelector('.lv-product-locate-in-store__container'); if (b) b.click(); }""")

        await page.wait_for_timeout(5000)

        # 清空请求记录
        lv_requests.clear()

        # === 2. 用 type 方法模拟键盘输入 ===
        print("\n=== 用 type 方法输入「東京」 ===")
        search_input = page.locator('.lv-address-search-form__input')
        if await search_input.count() > 0:
            await search_input.first.click(timeout=3000, force=True)
            await page.wait_for_timeout(500)

            # 用 type 方法模拟键盘输入（每个字符间隔100ms）
            await search_input.first.type("東京", delay=100)
            print("已用 type 输入「東京」")

            # 等待补全建议
            for wait_ms in [1000, 2000, 3000, 5000]:
                await page.wait_for_timeout(wait_ms)
                suggestions = await page.evaluate(r"""() => {
                    const modal = document.querySelector('.lv-locate-in-store__first-step-modal');
                    if (!modal) return { count: 0, html: '' };
                    // 查找所有可能的补全项
                    const all = modal.querySelectorAll('li, [role="option"], [class*="suggestion"], [class*="result"], [class*="dropdown"] > *');
                    const items = [];
                    for (const el of all) {
                        const rect = el.getBoundingClientRect();
                        if (rect.width > 0 && rect.height > 0) {
                            const text = (el.innerText || '').trim();
                            if (text && text.length < 100 && text !== '東京') {
                                items.push({
                                    tag: el.tagName,
                                    classes: (el.className || '').substring(0, 60),
                                    text: text.substring(0, 80),
                                });
                            }
                        }
                    }
                    return {
                        count: items.length,
                        items: items.slice(0, 10),
                        html: modal.innerHTML.substring(0, 1000),
                    };
                }""")
                print(f"  等待 {wait_ms}ms 后: 补全项={suggestions.get('count',0)}")
                for s in suggestions.get("items", [])[:5]:
                    print(f"    - tag={s['tag']} class={s['classes']} text={s['text']}")

                if suggestions.get("count", 0) > 0:
                    print("  发现补全建议！")
                    break

            print(f"\n输入期间 LV 请求数: {len(lv_requests)}")
            for i, req in enumerate(lv_requests):
                print(f"  [{i}] status={req['status']} ct={req['ct']} len={req['len']}")
                print(f"      url: {req['url']}")
                if req['body']:
                    print(f"      body: {req['body'][:200]}")

        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
