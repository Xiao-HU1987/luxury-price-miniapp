"""方案A v6：完整 dump 库存弹窗第一屏结构 + 测试文本搜索路径。

关键：确认弹窗第一屏的真实 DOM（输入框/按钮/placeholder），并测试输入城市名后
是否触发补全API与"在庫状況を見る"按钮，最终 dump 第二屏门店列表。

用法：venv/bin/python3.11 -m crawler.lv_diag_store_full <SKU或URL>
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
        # 捕获所有 LV 域名的非静态资源请求，重点找库存/门店 API
        if "louisvuitton" not in url:
            return
        if any(k in url for k in ["_nuxt", ".js", ".css", ".png", ".jpg",
                                  "bat.bing", "doubleclick", "teads", "facebook",
                                  "linkedin", "contentsquare", "inside-graph",
                                  "criteo", "adobedtm", "omtrdc"]):
            return
        try:
            ct = resp.headers.get("content-type", "")
        except Exception:
            ct = ""
        body = ""
        if "json" in ct or "graphql" in ct or "javascript" in ct:
            try:
                body = (await resp.text())[:800]
            except Exception:
                body = ""
        REQUESTS.append({"url": url[:200], "status": resp.status, "body": body})
    page.on("response", on_resp)


async def dump_modal_elems(page, name):
    """dump 弹窗内所有可见可交互元素。"""
    els = await page.evaluate("""
        () => {
            const m = document.querySelector('.-sidepanel.lv-locate-in-store')
                          || document.querySelector('.lv-locate-in-store');
            if (!m) return {ok:false, txt:'NO_MODAL'};
            const out = {ok:true, txt:(m.innerText||'').substring(0,800), elems:[]};
            const tags = 'input,button,select,a,textarea'.split(',');
            for (const tag of tags) {
                const nodes = m.querySelectorAll(tag);
                for (const el of nodes) {
                    const r = el.getBoundingClientRect();
                    if (r.width>0 && r.height>0) {
                        out.elems.push({
                            tag: el.tagName,
                            type: el.getAttribute('type')||'',
                            placeholder: el.getAttribute('placeholder')||'',
                            text: (el.innerText||el.value||'').trim().substring(0,50),
                            disabled: el.disabled || el.getAttribute('aria-disabled'),
                            cls: (el.className||'').substring(0,50),
                        });
                    }
                }
            }
            return out;
        }
    """)
    print(f"\n[{name}] 弹窗文本:\n{els.get('txt','')}")
    print(f"[{name}] 可交互元素:")
    for e in els.get("elems", []):
        print(f"    <{e['tag']} type={e['type']} ph={e['placeholder']} dis={e['disabled']} cls={e['cls']}> {e['text']}")
    html = await page.evaluate("document.documentElement.outerHTML")
    OUT_DIR.joinpath(f"{name}.html").write_text(html, encoding="utf-8")
    return els


async def open_modal(page):
    expanded = await page.evaluate("""(txt) => {
        const panels = document.querySelectorAll('.lv-expandable-panel');
        for (const p of panels) {
            if ((p.innerText||'').includes(txt)) {
                const btn = p.querySelector('button[aria-expanded]');
                if (btn && btn.getAttribute('aria-expanded') !== 'true') {
                    btn.click(); return 'expanded_click';
                }
                if (btn) return 'already_expanded';
            }
        }
        return 'panel_not_found';
    }""", PANEL_TEXT)
    print(f"展开面板: {expanded}")
    await asyncio.sleep(2)
    opened = await page.evaluate("""() => {
        const btn = document.querySelector('.lv-product-locate-in-store__container');
        if (btn) { btn.click(); return 'clicked'; }
        return 'not_found';
    }""")
    print(f"打开弹窗按钮: {opened}")
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
            print(f"导航异常: {str(e).split(chr(10))[0]}")
        await asyncio.sleep(8)
        await open_modal(page)

        # 选尺寸
        size_sel = page.locator("#displayedModelList")
        if await size_sel.count() > 0:
            opts = await size_sel.locator("option").all_inner_texts()
            real = [o.strip() for o in opts if "選ん" not in o]
            print(f"\n尺寸: {real}")
            if real:
                await size_sel.select_option(label=real[0])
                await asyncio.sleep(3)

        # dump 第一屏结构
        REQUESTS.clear()
        await dump_modal_elems(page, "step1_initial")

        # 测试：输入城市名（東京）——真实键盘输入触发自动补全
        print("\n=== 测试地址搜索: 输入'東京' ===")
        inp = page.locator(".-sidepanel.lv-locate-in-store .lv-address-search-form__input")
        print(f"输入框数量: {await inp.count()}")
        if await inp.count() > 0:
            try:
                await inp.first.click(timeout=3000)
            except Exception:
                pass
            await inp.first.fill("")
            await asyncio.sleep(0.3)
            await inp.first.type("東", delay=120)
            await asyncio.sleep(2)
            await inp.first.type("京", delay=120)
            await asyncio.sleep(2)
            print(f"输入后值: '{await inp.first.input_value()}'")
            # dump 自动补全下拉
            sugg = await page.evaluate("""
                () => {
                    const m = document.querySelector('.-sidepanel.lv-locate-in-store')
                              || document.querySelector('.lv-locate-in-store');
                    if (!m) return [];
                    const out = [];
                    const sels = '[role="option"], [role="listbox"] li, .lv-address-search-form__suggestion, ul li, .lv-autocomplete li';
                    const nodes = m.querySelectorAll(sels);
                    for (const el of nodes) {
                        const r = el.getBoundingClientRect();
                        if (r.width>0 && r.height>0)
                            out.push({text:(el.innerText||'').trim().substring(0,60), cls:(el.className||'').substring(0,50)});
                    }
                    return out.slice(0,20);
                }
            """)
            print(f"[补全下拉] {len(sugg)} 项:")
            for s in sugg:
                print(f"    - {s['text']} | {s['cls']}")
            await dump_modal_elems(page, "step1_typed")

            # 点击第一个补全项（若有）
            if sugg:
                picked = await page.evaluate("""
                    () => {
                        const m = document.querySelector('.-sidepanel.lv-locate-in-store')
                                  || document.querySelector('.lv-locate-in-store');
                        if (!m) return false;
                        const sels = '[role="option"], [role="listbox"] li, .lv-address-search-form__suggestion, ul li, .lv-autocomplete li';
                        const nodes = m.querySelectorAll(sels);
                        for (const el of nodes) {
                            const r = el.getBoundingClientRect();
                            if (r.width>0 && r.height>0 && (el.innerText||'').trim()) {
                                el.click(); return true;
                            }
                        }
                        return false;
                    }
                """)
                print(f"点击补全项: {picked}")
                await asyncio.sleep(3)
                await dump_modal_elems(page, "step1_selected")

        # 点击"ストア検索"（放大镜按钮）先搜索门店
        print("\n=== 点击'ストア検索'按钮 ===")
        REQUESTS.clear()
        srch = page.locator(".-sidepanel.lv-locate-in-store .lv-address-search-form__button")
        if await srch.count() > 0 and not await srch.first.is_disabled():
            try:
                await srch.first.click(timeout=5000)
                print("已点击'ストア検索'")
            except Exception as e:
                print(f"点击失败: {e}")
        await asyncio.sleep(10)
        full = await page.evaluate("""
            () => {
                const m = document.querySelector('.-sidepanel.lv-locate-in-store')
                          || document.querySelector('.lv-locate-in-store');
                return m ? (m.innerText||'') : 'NO_MODAL';
            }
        """)
        print(f"[ストア検索后 弹窗文本]\n{full}")
        print(f"[ストア検索后 网络 {len(REQUESTS)} 条:")
        for r in REQUESTS:
            print(f"  [RESP {r['status']}] {r['url']}")
            if r["body"]:
                print(f"      BODY: {r['body'][:300]}")
        await dump_modal_elems(page, "after_store_search")

        # 点击"在庫状況を見る"
        print("\n=== 点击'在庫状況を見る' ===")
        REQUESTS.clear()
        see = page.locator(".-sidepanel.lv-locate-in-store button")
        clicked = False
        for i in range(await see.count()):
            t = await see.nth(i).inner_text()
            if "在庫状況を見る" in t:
                dis = await see.nth(i).is_disabled()
                print(f"按钮[{i}] '{t}' disabled={dis}")
                if not dis:
                    try:
                        await see.nth(i).click(timeout=5000)
                        clicked = True
                    except Exception as e:
                        print(f"点击失败: {e}")
                break
        if not clicked:
            print("未找到可点击的'在庫状況を見る'按钮")
        await asyncio.sleep(12)
        await dump_modal_elems(page, "step2_result")

        # dump 第二屏完整 innerText（不限长度）
        full = await page.evaluate("""
            () => {
                const m = document.querySelector('.-sidepanel.lv-locate-in-store')
                          || document.querySelector('.lv-locate-in-store');
                return m ? (m.innerText||'') : 'NO_MODAL';
            }
        """)
        print(f"\n[step2 完整文本]\n{full}")

        print(f"\n=== 点击后网络 ({len(REQUESTS)} 条) ===")
        for r in REQUESTS:
            print(f"  [RESP {r['status']}] {r['url']}")
            if r["body"]:
                print(f"      BODY: {r['body'][:300]}")

        # 检查门店卡片
        stores = await page.evaluate("""
            () => {
                const m = document.querySelector('.-sidepanel.lv-locate-in-store')
                          || document.querySelector('.lv-locate-in-store');
                if (!m) return [];
                const cards = m.querySelectorAll('[class*="store-card"], [class*="store-item"], [class*="store-list"], [class*="pos"]');
                const out = [];
                for (const el of cards) {
                    const r = el.getBoundingClientRect();
                    if (r.width>0 && r.height>0)
                        out.push({text:(el.innerText||'').substring(0,120), cls:(el.className||'').substring(0,60)});
                }
                return out.slice(0,15);
            }
        """)
        print(f"\nDOM 门店卡片: {len(stores)}")
        for s in stores:
            print(f"  - {s['text']} | {s['cls']}")

        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())