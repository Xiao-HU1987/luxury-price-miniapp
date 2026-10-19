"""
LV 网络请求监控脚本
连接 CDP，监听用户手动操作时触发的所有 API 请求，
特别关注门店搜索相关的请求。
"""
import asyncio
import json
import time
from datetime import datetime
from playwright.async_api import async_playwright

CDP_ENDPOINT = "http://127.0.0.1:9333"
OUTPUT_FILE = "/tmp/lv_network_captures.jsonl"


async def main():
    async with async_playwright() as pw:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] 连接 Chrome CDP: {CDP_ENDPOINT}")
        browser = await pw.chromium.connect_over_cdp(CDP_ENDPOINT)
        ctx = browser.contexts[0]
        page = ctx.pages[0] if ctx.pages else await ctx.new_page()

        print(f"当前页面: {page.url}")
        print(f"页面标题: {await page.title()}")
        print()
        print("=" * 60)
        print("  网络监控已启动！")
        print("  请在 Chrome 窗口中手动操作：")
        print("  1. 登录 LV JP 官网")
        print("  2. 打开任意商品页")
        print("  3. 点击「ストアの在庫状況を確認する」")
        print("  4. 手动输入城市名搜索门店")
        print("=" * 60)
        print()

        # 监听网络请求
        captured = []

        def on_request(request):
            url = request.url
            method = request.method
            resource_type = request.resource_type

            # 只关注 XHR/Fetch 请求
            if resource_type not in ("xhr", "fetch"):
                return

            # 过滤静态资源
            skip_patterns = (".png", ".jpg", ".jpeg", ".gif", ".svg", ".css",
                             ".woff", ".woff2", ".ttf", ".ico")
            if any(url.lower().endswith(p) for p in skip_patterns):
                return

            # post_data 可能是二进制数据，安全获取
            try:
                pd = request.post_data
            except Exception:
                pd = None

            record = {
                "timestamp": datetime.now().strftime("%H:%M:%S.%f")[:-3],
                "method": method,
                "url": url,
                "resource_type": resource_type,
                "headers": dict(request.headers),
                "post_data": pd,
            }
            captured.append(record)

            # 打印到终端
            print(f"[{record['timestamp']}] {method} {url[:200]}")
            if record["post_data"]:
                print(f"  POST DATA: {record['post_data'][:500]}")

            # 保存到文件
            with open(OUTPUT_FILE, "a") as f:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")

        async def on_response(response):
            request = response.request
            url = request.url
            resource_type = request.resource_type

            if resource_type not in ("xhr", "fetch"):
                return

            skip_patterns = (".png", ".jpg", ".jpeg", ".gif", ".svg", ".css",
                             ".woff", ".woff2", ".ttf", ".ico")
            if any(url.lower().endswith(p) for p in skip_patterns):
                return

            try:
                status = response.status
                body = await response.body()
                body_text = body[:2000].decode("utf-8", errors="replace") if body else ""
            except Exception:
                status = "?"
                body_text = ""

            print(f"  -> RESPONSE [{status}]: {body_text[:300]}")

            # 找到对应的 request 记录并更新
            for r in reversed(captured):
                if r["url"] == url:
                    r["response_status"] = status
                    r["response_body_preview"] = body_text[:1000]
                    break

        page.on("request", on_request)
        page.on("response", on_response)

        # 持续监控
        last_url = page.url
        print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 开始监控... 按 Ctrl+C 停止\n")

        try:
            while True:
                await asyncio.sleep(1)
                current_url = page.url
                if current_url != last_url:
                    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 页面跳转: {current_url}")
                    last_url = current_url
        except KeyboardInterrupt:
            pass

        print(f"\n\n[{datetime.now().strftime('%H:%M:%S')}] 监控结束")
        print(f"共捕获 {len(captured)} 个 API 请求")
        print(f"详细日志已保存到: {OUTPUT_FILE}")

        # 输出摘要
        print("\n" + "=" * 60)
        print("  捕获到的 API 请求摘要:")
        print("=" * 60)
        store_related = []
        for r in captured:
            url = r["url"]
            if any(kw in url.lower() for kw in ("store", "availability", "stock",
                                                  "inventory", "shop", "retail")):
                store_related.append(r)
                print(f"\n  [{r['timestamp']}] {r['method']} {url}")
                if r.get("post_data"):
                    print(f"  POST DATA: {r['post_data']}")
                if r.get("response_status"):
                    print(f"  STATUS: {r['response_status']}")
                if r.get("response_body_preview"):
                    print(f"  BODY: {r['response_body_preview'][:500]}")

        if not store_related:
            print("\n  (未捕获到门店/库存相关 API 请求)")

        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())