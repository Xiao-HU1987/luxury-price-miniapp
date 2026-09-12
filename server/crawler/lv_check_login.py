"""检查当前 Chrome 的 LV 登录状态。"""
import asyncio
import os
import sys

for v in ("http_proxy", "https_proxy", "HTTP_PROXY", "HTTPS_PROXY",
          "all_proxy", "ALL_PROXY"):
    os.environ.pop(v, None)

from playwright.async_api import async_playwright

async def main():
    url = sys.argv[1] if len(sys.argv) > 1 else "https://jp.louisvuitton.com/jpn-jp/homepage"
    async with async_playwright() as pw:
        browser = await pw.chromium.connect_over_cdp("http://127.0.0.1:9333")
        ctx = browser.contexts[0] if browser.contexts else await browser.new_context()
        page = await ctx.new_page()
        await page.goto(url, wait_until="domcontentloaded", timeout=45000)
        await asyncio.sleep(6)
        # 收集登录状态线索
        info = await page.evaluate("""() => {
            const out = {loginLinks:[], myLV:[], bodyText:''};
            // 查找登录/账号相关元素
            const links = document.querySelectorAll('a,button,[role="button"]');
            for (const el of links) {
                const t = (el.innerText||'').trim();
                if (/(ログイン|LOG IN|ログアウト|My LV|マイ・LV|アカウント|サインイン|Sign \\s*[Ii]n|ログイン|ようこそ)/i.test(t)) {
                    out.loginLinks.push({text:t.substring(0,40), href:(el.getAttribute('href')||'').substring(0,80), cls:(el.className||'').substring(0,40)});
                }
            }
            const body = document.body?document.body.innerText||'':'';
            out.hasLoginLink = /ログイン|LOG IN|Sign In|サインイン/i.test(body);
            out.hasMyLV = /ようこそ|My LV|マイ・LV|マイLV/i.test(body);
            return out;
        }""")
        print("=== 登录状态线索 ===")
        print(f"hasLoginLink(有登录链接): {info['hasLoginLink']}")
        print(f"hasMyLV(有账号欢迎语): {info['hasMyLV']}")
        print("登录/账号相关元素:")
        for l in info.get('loginLinks', [])[:10]:
            print(f"  - [{l['text']}] href={l['href']} cls={l['cls']}")
        # 检查cookie里是否有LV会话
        try:
            cookies = await ctx.cookies("https://jp.louisvuitton.com")
            lv = [c for c in cookies if c['name'].lower() in ('access_token','refresh_token','x-lv-token','session','sid','_gu','okta','clovis','connect.sid') or 'token' in c['name'].lower() or 'session' in c['name'].lower()]
            print(f"\nLV cookies 总数: {len(cookies)}")
            print("会话/token类 cookies:")
            for c in lv[:20]:
                print(f"  {c['name']} (domain={c['domain']}) value_len={len(c['value'])}")
        except Exception as e:
            print(f"cookie查询异常: {e}")
        # 只关闭 page，保留 Chrome 进程（connect_over_cdp 下 browser.close() 会关闭整个 Chrome）
        try:
            await page.close()
        except Exception:
            pass

if __name__ == "__main__":
    asyncio.run(main())