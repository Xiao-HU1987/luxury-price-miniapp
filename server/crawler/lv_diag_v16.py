"""方案A v16：聚焦弹窗真实DOM + 网络请求（页面正常加载时）。

用法：venv/bin/python3.11 -m crawler.lv_diag_v16 <SKU>
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
OUT_DIR.mkdir(parents=True, exist_ok=True)

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
        if "json" in ct or "javascript" in ct or "graphql" in url:
            try:
                body = (await resp.text())[:1500]
            except Exception:
                body = ""
        REQUESTS.append({"url": url, "status": resp.status, "ct": ct, "body": body})
    page.on("response", on_resp)


async def js_expand_panel(page):
    """用 JS 展开面板 + 点击库存按钮（绕过 viewport）。"""
    return await page.evaluate(r"""
        (panelText) => {
            const out = {panel: false, btn: false, storeBtn: false};
            const panels = document.querySelectorAll('.lv-expandable-panel');
            let target = null;
            for (const p of panels) {
                if ((p.innerText||'').includes(panelText)) { target = p; break; }
            }
            if (target) {
                out.panel = true;
                const eb = target.querySelector('button[aria-expanded]');
                if (eb && eb.getAttribute('aria-expanded') !== 'true') eb.click();
                // 强制显示内容
                target.querySelectorAll('.lv-expandable-panel__content').forEach(c => {
                    c.style.display = 'block';
                    c.setAttribute('aria-hidden', 'false');
                });
            }
            // 点击库存按钮
            const sb = document.querySelector('.lv-product-locate-in-store__container');
            if (sb) { sb.click(); out.storeBtn = true; }
            return out;
        }
    """, PANEL_TEXT)


async def dump_modal(page, name):
    info = await page.evaluate(r"""
        () => {
            const sels = [
                '.lv-locate-in-store', '.-sidepanel.lv-locate-in-store',
                '.lv-modal__container', '.lv-modal__content',
                '[class*="locate-in-store"]', '[class*="store-list"]',
                '[class*="store-card"]', '[class*="store-item"]'
            ];
            const found = [];
            for (const s of sels) {
                const els = document.querySelectorAll(s);
                for (const el of els) {
                    const r = el.getBoundingClientRect();
                    if (r.width>0 && r.height>0) {
                        found.push({
                            sel: s,
                            cls: (typeof el.className === 'string' ? el.className : el.getAttribute('class')||'').substring(0,80),
                            text: (el.innerText||'').substring(0,200)
                        });
                    }
                }
            }
            return found.slice(0,30);
        }
    """)
    print(f"\n[{name}] 弹窗可见元素 ({len(info)}):")
    seen = set()
    for it in info:
        key = it['sel'] + '|' + it['text'][:40]
        if key in seen:
            continue
        seen.add(key)
        print(f"  [{it['sel']}] <{it['cls']}>")
        print(f"      {it['text']}")

    html = await page.evaluate("document.documentElement.outerHTML")
    OUT_DIR.joinpath(f"{name}.html").write_text(html, encoding="utf-8")
    print(f"  (HTML已存 {name}.html)")


async def main():
    sku = sys.argv[1] if len(sys.argv) > 1 else "M26763"
    url = f"https://jp.louisvuitton.com/jpn-jp/products/-/{sku}"
    async with async_playwright() as pw:
        browser = await pw.chromium.connect_over_cdp("http://127.0.0.1:9333")
        ctx = browser.contexts[0] if browser.contexts else await browser.new_context(
            locale="ja-JP", timezone_id="Asia/Tokyo")
        page = await ctx.new_page()
        await page.set_viewport_size({"width": 1440, "height": 900})
        await setup_network(page)

        print(f"=== 导航 {sku} ===")
        try:
            resp = await page.goto(url, wait_until="domcontentloaded", timeout=45000)
            print(f"HTTP: {resp.status if resp else 'None'} -> {page.url}")
        except Exception as e:
            print(f"导航异常: {str(e).split(chr(10))[0]}")
        await asyncio.sleep(8)

        # 滚动到库存面板
        try:
            await page.evaluate(r"""
                (panelText) => {
                    const panels = document.querySelectorAll('.lv-expandable-panel');
                    for (const p of panels) {
                        if ((p.innerText||'').includes(panelText)) {
                            p.scrollIntoView({behavior:'instant', block:'center'});
                            break;
                        }
                    }
                }
            """, PANEL_TEXT)
            await asyncio.sleep(1)
        except Exception:
            pass

        # 选择尺寸（若有）
        size_sel = page.locator("#displayedModelList")
        if await size_sel.count() > 0:
            opts = await size_sel.locator("option").all_inner_texts()
            real = [o.strip() for o in opts if "選ん" not in o]
            print(f"\n尺寸选项: {real}")
            if real:
                await size_sel.select_option(label=real[0])
                await asyncio.sleep(3)

        # JS 展开面板 + 点击库存按钮
        print("\n=== JS 展开面板 + 点击库存按钮 ===")
        r = await js_expand_panel(page)
        print(f"结果: {r}")
        await asyncio.sleep(6)

        await dump_modal(page, f"v16_{sku}_after_open")

        # 授权地理位置
        try:
            await ctx.grant_permissions(['geolocation'])
            await ctx.set_geolocation({"latitude": 35.6762, "longitude": 139.6503})
            print("\n已设置地理位置=東京")
        except Exception as e:
            print(f"设置地理位置异常: {e}")
        await asyncio.sleep(2)

        REQUESTS.clear()

        # 点击"現在地で検索"
        print("\n=== 点击'現在地で検索' ===")
        geo = page.locator(".lv-store-geolocation__get-button")
        if await geo.count() > 0:
            dis = await geo.first.get_attribute("disabled")
            print(f"geo disabled={dis}")
            try:
                await geo.first.click(timeout=5000)
                print("已点击")
            except Exception as e:
                print(f"点击失败({str(e).split(chr(10))[0]})，尝试JS点击")
                await geo.first.evaluate("el => el.click()")
                print("已用JS点击")
        else:
            print(".lv-store-geolocation__get-button 不存在")
            # 列出弹窗内所有按钮
            btns = await page.evaluate(r"""
                () => {
                    const modal = document.querySelector('.lv-modal__content, .-sidepanel.lv-locate-in-store, .lv-locate-in-store');
                    if (!modal) return [];
                    const out = [];
                    modal.querySelectorAll('button, [role=button], input, select, a').forEach(el => {
                        const r = el.getBoundingClientRect();
                        if (r.width>0 && r.height>0) {
                            out.push({
                                tag: el.tagName,
                                type: el.getAttribute('type')||'',
                                text: (el.innerText||el.value||el.getAttribute('placeholder')||'').trim().substring(0,60),
                                cls: (typeof el.className==='string'?el.className:'').substring(0,60)
                            });
                        }
                    });
                    return out;
                }
            """)
            print(f"弹窗内可见控件 ({len(btns)}):")
            for b in btns:
                print(f"  <{b['tag']} type={b['type']} class={b['cls']}> {b['text']}")

        await asyncio.sleep(8)
        await dump_modal(page, f"v16_{sku}_after_geo")

        print(f"\n=== 网络请求 ({len(REQUESTS)} 条) ===")
        for r_ in REQUESTS:
            print(f"  [RESP {r_['status']} {r_['ct']}] {r_['url']}")
            if r_['body']:
                print(f"      BODY: {r_['body'][:400]}")

        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())