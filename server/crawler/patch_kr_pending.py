"""补抓 KR 站 10 条 pending 记录

使用 playwright 通过 CDP 连接已存活的 Chrome 会话（端口 9333），
复用 Chrome 的 Akamai 信任分，避免被反爬拦截。
"""
import json
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

# 数据文件路径
PROJECT_ROOT = Path("/Users/huxiao/Public/测试项目-1-26.6.27")
PENDING_FILE = PROJECT_ROOT / "data/lv/KR/products_KR_pending.jsonl"
PATCHED_FILE = PROJECT_ROOT / "data/lv/KR/products_KR_patched.jsonl"

# 请求间隔（秒）
REQUEST_INTERVAL = 6.0
PAGE_WAIT = 5000  # 页面加载等待（毫秒）


def extract_product_from_page(page, target_sku: str, url: str) -> dict:
    """从当前页面提取商品信息"""
    js_code = """
    (() => {
        const result = {
            name: '',
            price: 0,
            currency: 'KRW',
            images: [],
            sku_id: '',
            sku_ids: [],
        };

        // 1. 商品名 - 多种选择器尝试
        const nameSelectors = [
            'h1.product-name',
            'h1[class*="ProductName"]',
            '[data-testid="product-name"]',
            '.product-header h1',
            'h1',
        ];
        for (const sel of nameSelectors) {
            const el = document.querySelector(sel);
            if (el && el.textContent.trim()) {
                result.name = el.textContent.trim();
                break;
            }
        }

        // 2. 价格 - LV韩国站实际结构：div.lv-price > span.notranslate
        const priceSelectors = [
            '.lv-price .notranslate',          // LV标准价格结构
            '.lv-product__price .notranslate', // 产品页主价格
            '.lv-product-purchase-bar .lv-price',
            '.lv-price',                       // 通用lv-price
            '.price-display',
            '[data-testid="price"]',
            '.product-price',
            '[class*="Price"]',
            'span[class*="price"]',
        ];
        for (const sel of priceSelectors) {
            const el = document.querySelector(sel);
            if (el) {
                const txt = el.textContent.trim();
                // 提取数字（支持 ₩5,950,000 / 5950000 / 5,950,000 等格式）
                const match = txt.match(/[\\d,]+/);
                if (match) {
                    const num = parseInt(match[0].replace(/,/g, ''), 10);
                    if (num > 1000) {  // 过滤掉非价格数字（如购物车数量3）
                        result.price = num;
                        if (txt.includes('₩') || txt.includes('KRW')) result.currency = 'KRW';
                        else if (txt.includes('¥') || txt.includes('JPY')) result.currency = 'JPY';
                        break;
                    }
                }
            }
        }

        // 3. 图片
        const imgSelectors = [
            'img.product-image',
            '.product-gallery img',
            '[class*="ProductImage"] img',
            'picture img',
        ];
        for (const sel of imgSelectors) {
            const imgs = document.querySelectorAll(sel);
            if (imgs.length > 0) {
                result.images = Array.from(imgs)
                    .map(img => img.src || img.getAttribute('data-src') || '')
                    .filter(src => src && !src.includes('data:'))
                    .slice(0, 8);
                if (result.images.length > 0) break;
            }
        }

        // 4. SKU - 从URL提取
        const url = window.location.href;
        const urlMatch = url.match(/\\/([A-Z]\\d{4,5}|N\\d{4,5})(?:\\?|$)/);
        if (urlMatch) result.sku_id = urlMatch[1];

        // 5. 关联SKU - 从页面中找所有SKU链接
        const skuLinks = document.querySelectorAll('a[href*="/products/"]');
        const skuSet = new Set();
        for (const link of skuLinks) {
            const href = link.getAttribute('href') || '';
            const m = href.match(/\\/([A-Z]\\d{4,5}|N\\d{4,5})(?:\\?|$)/);
            if (m) skuSet.add(m[1]);
        }
        result.sku_ids = Array.from(skuSet);

        // 6. 从JSON-LD提取更准确的数据
        const jsonLd = document.querySelector('script[type="application/ld+json"]');
        if (jsonLd) {
            try {
                const data = JSON.parse(jsonLd.textContent);
                if (data.name && !result.name) result.name = data.name;
                if (data.sku && !result.sku_id) result.sku_id = data.sku;
                if (data.offers) {
                    const offers = Array.isArray(data.offers) ? data.offers : [data.offers];
                    for (const o of offers) {
                        if (o.price && !result.price) {
                            result.price = parseInt(String(o.price).replace(/[^\\d]/g, ''), 10);
                        }
                        if (o.priceCurrency && result.currency === 'KRW') {
                            result.currency = o.priceCurrency;
                        }
                    }
                }
                if (data.image && result.images.length === 0) {
                    result.images = Array.isArray(data.image) ? data.image : [data.image];
                }
            } catch (e) {}
        }

        return result;
    })()
    """

    data = page.evaluate(js_code)

    # 补充元数据
    data["source_url"] = url
    data["country"] = "KR"
    data["currency"] = data.get("currency", "KRW") or "KRW"
    data["sku_id"] = target_sku
    if not data.get("sku_ids"):
        data["sku_ids"] = [target_sku]
    data["crawled_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    data["name_local"] = data.pop("name", "")

    return data


def main():
    print("=" * 60)
    print("KR 站 10 条 pending 记录补抓 (playwright CDP)")
    print("=" * 60)

    # 1. 读取 pending 记录
    pending = []
    with open(PENDING_FILE) as f:
        for line in f:
            pending.append(json.loads(line))
    print(f"待补抓: {len(pending)} 条")

    # 2. 通过 playwright CDP 连接现有 Chrome
    patched = []
    failed = []

    with sync_playwright() as p:
        # 连接到已运行的 Chrome 实例
        try:
            browser = p.chromium.connect_over_cdp("http://127.0.0.1:9333")
            print(f"✅ 已连接 Chrome CDP")
        except Exception as e:
            print(f"❌ CDP 连接失败: {e}")
            return

        # 获取现有上下文和页面
        context = browser.contexts[0] if browser.contexts else browser.new_context()
        page = context.pages[0] if context.pages else context.new_page()

        # 记录原始URL，用于最后恢复
        original_url = page.url
        print(f"当前页面: {original_url[:60]}")

        # 3. 逐个抓取
        for i, rec in enumerate(pending, 1):
            sku = rec["sku_id"]
            url = rec["source_url"]
            print(f"\n[{i}/{len(pending)}] 抓取 SKU {sku}")
            print(f"  URL: {url[:80]}...")

            try:
                # 导航到目标页面
                page.goto(url, wait_until="domcontentloaded", timeout=30000)
                page.wait_for_timeout(PAGE_WAIT)

                # 提取数据
                data = extract_product_from_page(page, sku, url)

                if data.get("name_local") and data.get("price", 0) > 0:
                    print(f"  ✅ 成功: name={data['name_local'][:30]}, price=₩{data['price']:,}")
                    patched.append(data)
                else:
                    # 重试 - 等待更长时间
                    print(f"  ⚠️ 数据不完整，重试(等待8秒)...")
                    page.wait_for_timeout(8000)
                    data = extract_product_from_page(page, sku, url)
                    if data.get("name_local") and data.get("price", 0) > 0:
                        print(f"  ✅ 重试成功: name={data['name_local'][:30]}, price=₩{data['price']:,}")
                        patched.append(data)
                    else:
                        print(f"  ❌ 重试仍失败: name={data.get('name_local','')!r}, price={data.get('price',0)}")
                        failed.append({"sku_id": sku, "url": url})
            except Exception as e:
                print(f"  ❌ 异常: {e}")
                failed.append({"sku_id": sku, "url": url, "error": str(e)})

            # 请求间隔
            if i < len(pending):
                time.sleep(REQUEST_INTERVAL)

        # 恢复原始页面
        try:
            page.goto(original_url, wait_until="domcontentloaded", timeout=15000)
        except:
            pass

        browser.close()

    # 4. 保存结果
    print("\n" + "=" * 60)
    print(f"补抓完成: 成功 {len(patched)}, 失败 {len(failed)}")

    if patched:
        with open(PATCHED_FILE, "w") as f:
            for d in patched:
                f.write(json.dumps(d, ensure_ascii=False) + "\n")
        print(f"补抓数据写入: {PATCHED_FILE}")

    if failed:
        print(f"\n⚠️ 失败的SKU:")
        for f_rec in failed:
            print(f"  {f_rec['sku_id']}: {f_rec.get('url','')[:70]}")

    return patched, failed


if __name__ == "__main__":
    main()
