"""方案A v15：检查弹窗 Vue 组件实例内部数据 + 尝试"現在地で検索"。

1. 遍历弹窗 DOM 上的 __vue__ 实例，找门店/城市/地址相关数据
2. geolocation 授权 + set_geolocation
3. 点击"現在地で検索"观察网络请求和弹窗状态

用法：venv/bin/python3.11 -m crawler.lv_diag_store_v15 <URL>
"""
import asyncio
import json
import os
import sys
from pathlib import Path

for v in ("http_proxy", "https_proxy", "HTTP_PROXY", "HTTPS_PROXY",
          "all_proxy", "ALL_PROXY"):
    os.environ.pop(v, None)

from playwright.async_api import async_playwright

OUT_DIR = Path("/tmp/lv_diag_out")
OUT_DIR.mkdir(exist_ok=True)
REQUESTS = []


async def hook_network(page):
    await page.add_init_script(r"""
        (() => {
            if (window.__hooked) return;
            window.__hooked = true;
            window.__reqs = [];
            const record = (url, method, status, body) => {
                window.__reqs.push({url: String(url), method, status, body: body||''});
            };
            const of = window.fetch;
            window.fetch = function(...args) {
                const u = args[0] && (args[0].url || args[0]) || '';
                return of.apply(this, args).then(res => {
                    const ct = res.headers && res.headers.get('content-type') || '';
                    if (ct.includes('json')) {
                        return res.clone().text().then(body => {
                            record(u, 'FETCH', res.status, body.substring(0,3000));
                            return res;
                        });
                    }
                    record(u, 'FETCH', res.status, '');
                    return res;
                }).catch(e => { record(u,'FETCH','ERR',String(e)); throw e; });
            };
        })();
    """)


async def open_modal(page):
    await page.evaluate(r"""
        () => {
            const panels = document.querySelectorAll('.lv-expandable-panel');
            for (const p of panels) {
                if ((p.innerText||'').includes('ストアの在庫状況を確認する')) {
                    const btn = p.querySelector('button[aria-expanded]');
                    if (btn && btn.getAttribute('aria-expanded') !== 'true') btn.click();
                    break;
                }
            }
        }
    """)
    await asyncio.sleep(2)
    await page.evaluate("""
        () => {
            const btn = document.querySelector('.lv-product-locate-in-store__container');
            if (btn) btn.click();
        }
    """)
    await asyncio.sleep(5)


async def select_size(page):
    size_sel = page.locator("#displayedModelList")
    if await size_sel.count() > 0:
        opts = await size_sel.locator("option").all_inner_texts()
        real = [o.strip() for o in opts if "サイズを選んで" not in o]
        if real:
            await size_sel.select_option(label=real[0])
            await asyncio.sleep(2)


async def dump_vue(page):
    """检查弹窗相关元素的 Vue 实例数据。"""
    data = await page.evaluate("""
        () => {
            const out = {found: [], keys: new Set()};
            // 从弹窗根元素向上找 __vue__
            const m = document.querySelector('.lv-locate-in-store');
            if (m) {
                let el = m;
                while (el && !el.__vue__) el = el.parentElement;
                if (el && el.__vue__) {
                    out.found.push('modal-root');
                    // 收集组件名和 data 键
                    const chain = [];
                    let v = el.__vue__;
                    for (let i=0;i<12 && v;i++){
                        const name = v.\u0024options && (v.\u0024options.name || v.\u0024options.__name) || '';
                        let dataKeys = [];
                        try { dataKeys = Object.keys(v.\u0024data || {}); } catch(e){}
                        chain.push({name: String(name), dataKeys: dataKeys.slice(0,40)});
                        v = v.\u0024parent;
                    }
                    out.chain = chain;
                }
            }
            // 全局搜索含 store/address/city 的 vue 数据
            const walk = (node, depth) => {
                if (!node || depth>6 || out.found.length>8) return;
                if (node.__vue__) {
                    try {
                        const keys = Object.keys(node.__vue__.\u0024data || {});
                        const rel = keys.filter(k => /store|address|city|geo|locat|pos|inventory/i.test(k));
                        if (rel.length) {
                            const name = node.__vue__.\u0024options && (node.__vue__.\u0024options.name||node.__vue__.\u0024options.__name)||'';
                            out.found.push({name:String(name), rel:rel.slice(0,30)});
                        }
                    } catch(e){}
                }
                for (const c of node.children) walk(c, depth+1);
            };
            walk(document.body, 0);
            return out;
        }
    """)
    print("=== Vue 实例数据 ===")
    if data.get("chain"):
        print("弹窗组件链:")
        for c in data["chain"]:
            print(f"  <{c['name']}> data={c['dataKeys']}")
    print(f"含 store/address 相关数据组件({len(data.get('found',[]))}):")
    for f in data.get("found", []):
        print(f"  {f}")


async def main():
    url = sys.argv[1] if len(sys.argv) > 1 else "https://jp.louisvuitton.com/jpn-jp/products/-/M29195"
    async with async_playwright() as pw:
        browser = await pw.chromium.connect_over_cdp("http://127.0.0.1:9333")
        ctx = browser.contexts[0] if browser.contexts else await browser.new_context()
        await ctx.grant_permissions(['geolocation'])
        await ctx.set_geolocation({"latitude": 35.6762, "longitude": 139.6503})
        page = await ctx.new_page()
        await page.set_viewport_size({"width": 1440, "height": 900})
        await hook_network(page)

        print(f"=== 导航: {url} ===")
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=45000)
        except Exception as e:
            print(f"导航异常: {str(e).split(chr(10))[0]}")
        await asyncio.sleep(8)
        await open_modal(page)
        await select_size(page)
        await dump_vue(page)

        # 点击"現在地で検索"
        print("\n=== 点击'現在地で検索' ===")
        geo = page.locator(".lv-store-geolocation__get-button")
        if await geo.count() > 0:
            try:
                await geo.first.click(timeout=5000)
                print("已点击")
            except Exception as e:
                print(f"点击异常: {str(e).split(chr(10))[0]}")
        await asyncio.sleep(8)

        reqs = await page.evaluate("window.__reqs || []")
        print(f"\n请求({len(reqs)}):")
        for r in reqs:
            if "louisvuitton.com" in r["url"] or "api." in r["url"]:
                print(f"  [{r['method']} {r['status']}] {r['url'][:180]}")
                if r["body"] and "json" in r["body"][:200].lower() or "{" in r["body"][:20]:
                    print(f"      BODY: {r['body'][:500]}")

        # 弹窗当前状态
        st = await page.evaluate("""
            () => {
                const m = document.querySelector('.lv-locate-in-store');
                if (!m) return 'NO_MODAL';
                const cards = m.querySelectorAll('.lv-store-card-detailed');
                return {modal: true, cards: cards.length, text: (m.innerText||'').substring(0,300)};
            }
        """)
        print(f"\n弹窗状态: {st}")

        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())