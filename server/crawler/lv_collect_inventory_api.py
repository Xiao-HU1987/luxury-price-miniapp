"""
LV JP 门店库存采集 — API 方案
通过 CDP 连接 Chrome，从页面提取认证信息，直接调用 stores/query API
"""
import asyncio
import json
import logging
import os
import random
import sys
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

from playwright.async_api import async_playwright

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("lv_inventory_api")

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / "data" / "lv" / "JP"
CDP_ENDPOINT = "http://127.0.0.1:9333"

# 日本城市列表
CITIES = [
    "東京", "大阪", "京都", "横浜", "名古屋", "神戸", "福岡",
    "札幌", "仙台", "埼玉", "千葉", "広島", "沖縄",
]

# 节奏控制（对齐 lv_anti_detect.py 已验证参数）
REQUEST_DELAY = (6.0, 12.0)       # 同 SKU 内城市间延迟
SKU_DELAY = (20.0, 45.0)          # SKU 间延迟（对齐旧脚本 REQUEST_INTERVAL）
BATCH_SIZE = 4                     # 每 N 个 SKU 后长冷却（对齐旧脚本）
BATCH_COOLDOWN = (600, 1080)       # 批次冷却 10-18 分钟（对齐旧脚本）
CONSECUTIVE_403_LIMIT = 3          # 连续 403 上限，达到后冷却重试
RETRY_403_DELAY = (300, 600)       # 遇到 403 后冷却时间（5-10分钟）
API_TEST_RETRY_WAIT = [300, 600, 900]  # API 测试失败重试等待时间


async def extract_credentials(page) -> dict:
    """从页面提取 API 认证信息"""
    creds = {}

    # client_id / client_secret 从页面 HTML 提取
    html = await page.content()
    import re
    m = re.search(r'"([a-f0-9]{32})"\s*,\s*"([a-fA-F0-9]{32})"', html)
    if m:
        creds["client_id"] = m.group(1)
        creds["client_secret"] = m.group(2)
        logger.info(f"提取 client_id: {creds['client_id'][:8]}...")
    else:
        # fallback: 使用已知值
        creds["client_id"] = "607e3016889f431fb8020693311016c9"
        creds["client_secret"] = "60bbcdcD722D411B88cBb72C8246a22F"
        logger.warning("未从页面提取到 client_id/secret，使用已知值")

    # x-device-id 从 localStorage 提取
    device_id = await page.evaluate(
        "() => localStorage.getItem('LV.jpn-jp.deviceId')"
    )
    creds["x_device_id"] = device_id or str(uuid.uuid4())
    logger.info(f"x-device-id: {creds['x_device_id'][:8]}...")

    # 当前商品页 URL（作为 Referer）
    creds["referer"] = page.url
    return creds


async def query_stores(page, sku: str, city: str, creds: dict) -> dict:
    """调用 stores/query API 搜索门店"""
    x_correlation_id = str(uuid.uuid4()).replace("-", "")[:16]

    result = await page.evaluate("""
        async ([sku, city, creds, xid]) => {
            const headers = {
                'Content-Type': 'application/json',
                'Accept': 'application/json',
                'client_id': creds.client_id,
                'client_secret': creds.client_secret,
                'x-device-id': creds.x_device_id,
                'x-correlation-id': xid,
                'Origin': 'https://jp.louisvuitton.com',
                'Referer': creds.referer,
            };

            const resp = await fetch(
                'https://api.louisvuitton.com/eco-eu/search-merch-eapi/v1/jpn-jp/stores/query',
                {
                    method: 'POST',
                    credentials: 'include',
                    headers: headers,
                    body: JSON.stringify({
                        flagShip: false,
                        country: '',
                        query: city,
                        clickAndCollect: false,
                        skuId: sku,
                        pageType: 'productsheet'
                    })
                }
            );

            const status = resp.status;
            let data = null;
            try { data = await resp.json(); } catch(e) { data = {error: String(e)}; }
            return {status, data};
        }
    """, [sku, city, creds, x_correlation_id])
    return result


async def query_availability(page, sku: str, creds: dict) -> dict:
    """调用 availability API 检查在线库存"""
    x_correlation_id = str(uuid.uuid4()).replace("-", "")[:16]

    result = await page.evaluate("""
        async ([sku, creds, xid]) => {
            const headers = {
                'Content-Type': 'application/json',
                'Accept': 'application/json',
                'client_id': creds.client_id,
                'client_secret': creds.client_secret,
                'x-device-id': creds.x_device_id,
                'x-correlation-id': xid,
                'Origin': 'https://jp.louisvuitton.com',
                'Referer': creds.referer,
            };

            const resp = await fetch(
                'https://api.louisvuitton.com/eco-as/lvcom-prodct-dtl-eapi/v2/products/jpn-jp/availability',
                {
                    method: 'POST',
                    credentials: 'include',
                    headers: headers,
                    body: JSON.stringify({
                        version: 'V2',
                        locationId: 'V02',
                        channel: 'ECO',
                        inventoryCode: 'lv_inventory_jp',
                        orderType: 'SALE',
                        availability: [{type: 'sku', identifier: sku}]
                    })
                }
            );

            const status = resp.status;
            let data = null;
            try { data = await resp.json(); } catch(e) { data = {error: String(e)}; }
            return {status, data};
        }
    """, [sku, creds, x_correlation_id])
    return result


def parse_store_hit(hit: dict, city: str, sku: str) -> dict:
    """解析 stores/query 返回的单个门店"""
    address = hit.get("address", {})

    # 构建完整地址
    if isinstance(address, dict):
        parts = []
        # 实际 API 字段: streetAddress, postalCode, addressLocality, state, addressCountry
        for k in ("streetAddress", "postalCode", "addressLocality", "state", "addressCountry"):
            v = address.get(k, "")
            if v:
                parts.append(v)
        addr_str = ", ".join(parts)
        city_name = address.get("addressLocality", "") or address.get("state", "") or city
    else:
        addr_str = str(address) if address else ""
        city_name = city

    # 库存状态（从 additionalProperty 数组中提取 stockAvailability）
    in_stock = False
    additional_props = hit.get("additionalProperty", [])
    if isinstance(additional_props, list):
        for prop in additional_props:
            if prop.get("name") == "stockAvailability":
                in_stock = prop.get("value") == "true"
                break

    if in_stock:
        stock_status = "in_stock"
    else:
        stock_status = "out_of_stock"

    return {
        "sku_id": sku,
        "country": "JP",
        "store_name": hit.get("name", ""),
        "store_address": addr_str,
        "store_city": city_name,
        "store_telephone": hit.get("telephone", ""),
        "store_geo": hit.get("geo", {}),
        "stock_status": stock_status,
        "in_stock": in_stock,
        "crawled_at": datetime.now().isoformat(),
    }


async def process_sku(page, sku: str, creds: dict, output_path: Path) -> dict:
    """处理单个 SKU：查 availability + 所有城市门店"""
    logger.info(f"--- 处理 SKU: {sku} ---")

    summary = {
        "sku": sku,
        "online_available": None,
        "total_stores": 0,
        "stores_in_stock": 0,
        "stores_out_of_stock": 0,
        "stores_unknown": 0,
        "cities_queried": 0,
        "cities_403": 0,
    }

    # 1. 查在线库存
    avail = await query_availability(page, sku, creds)
    if avail["status"] == 200 and avail["data"]:
        sku_avail = (avail["data"].get("skuAvailability") or [{}])[0]
        summary["online_available"] = sku_avail.get("inStock", False)
        summary["sourcing"] = sku_avail.get("sourcing", "")
        logger.info(f"  在线库存: inStock={summary['online_available']}, "
                     f"sourcing={summary['sourcing']}")
    elif avail["status"] == 403:
        logger.warning(f"  availability API 返回 403，冷却后重试...")
        await asyncio.sleep(random.uniform(*RETRY_403_DELAY))
        avail = await query_availability(page, sku, creds)
        if avail["status"] == 200 and avail["data"]:
            sku_avail = (avail["data"].get("skuAvailability") or [{}])[0]
            summary["online_available"] = sku_avail.get("inStock", False)
            summary["sourcing"] = sku_avail.get("sourcing", "")
            logger.info(f"  在线库存(重试成功): inStock={summary['online_available']}")
        else:
            logger.warning(f"  availability API 重试仍失败: {avail['status']}")
    else:
        logger.warning(f"  availability API 返回 {avail['status']}")

    # 2. 逐城市查门店
    consecutive_403 = 0
    for city in CITIES:
        result = await query_stores(page, sku, city, creds)
        summary["cities_queried"] += 1

        if result["status"] == 403:
            consecutive_403 += 1
            summary["cities_403"] += 1
            logger.warning(f"  [{city}] API 返回 403 (连续{consecutive_403}次)")

            if consecutive_403 >= CONSECUTIVE_403_LIMIT:
                logger.warning(f"  连续 {consecutive_403} 次 403，冷却 {RETRY_403_DELAY}s 后重试...")
                await asyncio.sleep(random.uniform(*RETRY_403_DELAY))
                consecutive_403 = 0  # 重置计数器

                # 重试当前城市
                result = await query_stores(page, sku, city, creds)
                if result["status"] == 403:
                    logger.warning(f"  [{city}] 重试仍 403，跳过剩余城市")
                    break
                # 重试成功，继续处理
            else:
                await asyncio.sleep(random.uniform(*REQUEST_DELAY))
                continue

        elif result["status"] != 200:
            logger.warning(f"  [{city}] API 返回 {result['status']}")
            consecutive_403 = 0
            await asyncio.sleep(random.uniform(*REQUEST_DELAY))
            continue

        consecutive_403 = 0  # 成功后重置

        hits = (result["data"] or {}).get("hits", [])
        nb_hits = (result["data"] or {}).get("nbHits", 0)
        logger.info(f"  [{city}] {nb_hits} 家门店")

        for hit in hits:
            record = parse_store_hit(hit, city, sku)
            summary["total_stores"] += 1

            if record["stock_status"] == "in_stock":
                summary["stores_in_stock"] += 1
            elif record["stock_status"] == "out_of_stock":
                summary["stores_out_of_stock"] += 1
            else:
                summary["stores_unknown"] += 1

            # 写入 JSONL
            with open(output_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")

        await asyncio.sleep(random.uniform(*REQUEST_DELAY))

    logger.info(f"  SKU {sku} 完成: {summary['total_stores']}家门店, "
                 f"有货{summary['stores_in_stock']}, "
                 f"无货{summary['stores_out_of_stock']}, "
                 f"未知{summary['stores_unknown']}, "
                 f"403:{summary['cities_403']}")
    return summary


async def main():
    sku_file = DATA_DIR / "products_JP.jsonl"       # 全部 384 SKU
    output_path = DATA_DIR / "inventories_JP_api.jsonl"
    stores_path = DATA_DIR / "inventories_JP_stores.jsonl"  # 旧爬虫数据
    MIN_STORES_THRESHOLD = 20  # SKU 至少要有这么多门店记录才算完成

    # 加载全部 SKU 列表
    if not sku_file.exists():
        logger.error(f"SKU 文件不存在: {sku_file}")
        return

    all_skus = set()
    with open(sku_file, "r") as f:
        for line in f:
            try:
                r = json.loads(line.strip())
                sid = r.get("sku_id", r.get("sku", ""))
                if sid:
                    all_skus.add(sid)
            except Exception:
                pass
    logger.info(f"全部 JP SKU: {len(all_skus)} 个")

    # 加载 API 已完成的 SKU
    sku_record_count = {}
    if output_path.exists():
        with open(output_path, "r") as f:
            for line in f:
                try:
                    r = json.loads(line.strip())
                    sid = r.get("sku_id", "")
                    sku_record_count[sid] = sku_record_count.get(sid, 0) + 1
                except Exception:
                    pass

    api_done_skus = {s for s, c in sku_record_count.items() if c >= MIN_STORES_THRESHOLD}
    api_partial_skus = {s for s, c in sku_record_count.items() if c < MIN_STORES_THRESHOLD}
    logger.info(f"API 已完成 SKU: {len(api_done_skus)} 个")

    # 加载旧爬虫已完成的 SKU
    stores_done_skus = set()
    if stores_path.exists():
        with open(stores_path, "r") as f:
            for line in f:
                try:
                    r = json.loads(line.strip())
                    stores_done_skus.add(r.get("sku_id", ""))
                except Exception:
                    pass
    logger.info(f"旧爬虫已完成 SKU: {len(stores_done_skus)} 个")

    # 合并已完成
    done_skus = api_done_skus | stores_done_skus
    logger.info(f"合并已完成 SKU: {len(done_skus)} 个")

    # 清理 API 部分完成的 SKU 数据
    if api_partial_skus and output_path.exists():
        to_clean = api_partial_skus - stores_done_skus
        if to_clean:
            logger.info(f"清理 API 部分完成的 SKU 数据: {to_clean}")
            temp_path = output_path.with_suffix(".tmp")
            with open(output_path, "r") as fin, open(temp_path, "w") as fout:
                for line in fin:
                    try:
                        r = json.loads(line.strip())
                        if r.get("sku_id", "") in to_clean:
                            continue
                        fout.write(line)
                    except Exception:
                        fout.write(line)
            temp_path.replace(output_path)
            logger.info(f"已清理 {len(to_clean)} 个部分完成的 SKU")

    pending = sorted(all_skus - done_skus)
    logger.info(f"仍缺失: {len(pending)} 个 SKU")
    if pending:
        logger.info(f"缺失 SKU 前10: {pending[:10]}")

    if not pending:
        logger.info("所有 SKU 已完成，无需处理")
        return

    # 连接 Chrome
    async with async_playwright() as pw:
        logger.info(f"连接 Chrome CDP: {CDP_ENDPOINT}")
        browser = await pw.chromium.connect_over_cdp(CDP_ENDPOINT)
        ctx = browser.contexts[0]
        page = ctx.pages[0] if ctx.pages else await ctx.new_page()

        # 提取认证信息
        creds = await extract_credentials(page)
        if not creds.get("client_id") or not creds.get("client_secret"):
            logger.error("无法提取认证信息，退出")
            await browser.close()
            return

        # 验证 API 可用性（支持重试）
        logger.info("验证 API 可用性...")
        test_ok = False
        for retry in range(3):
            test = await query_stores(page, pending[0], "東京", creds)
            if test["status"] == 200:
                logger.info(f"API 测试通过: {test['data'].get('nbHits', 0)} 家门店")
                test_ok = True
                break
            else:
                logger.warning(f"API 测试失败 (第{retry+1}次): status={test['status']}")
                if retry < 2:
                    wait = API_TEST_RETRY_WAIT[retry]
                    logger.info(f"等待 {wait}s 后重试...")
                    await asyncio.sleep(wait)
        if not test_ok:
            logger.error("API 测试 3 次均失败，请等待更长时间后重试")
            await browser.close()
            return

        # 逐个处理 SKU
        summaries = []
        for i, sku in enumerate(pending):
            logger.info(f"\n[{i+1}/{len(pending)}] {sku}")
            summary = await process_sku(page, sku, creds, output_path)
            summaries.append(summary)

            if i < len(pending) - 1:
                delay = random.uniform(*SKU_DELAY)
                logger.info(f"SKU 间隔 {delay:.1f}s")
                await asyncio.sleep(delay)

            # 批次冷却
            if (i + 1) % BATCH_SIZE == 0 and i < len(pending) - 1:
                cooldown = random.uniform(*BATCH_COOLDOWN)
                logger.info(f"批次冷却 {cooldown:.0f}s ({i+1}/{len(pending)} 完成)...")
                await asyncio.sleep(cooldown)

        # 输出汇总
        logger.info("\n" + "=" * 60)
        logger.info("采集完成汇总")
        logger.info("=" * 60)
        total = sum(s["total_stores"] for s in summaries)
        in_stock = sum(s["stores_in_stock"] for s in summaries)
        out_stock = sum(s["stores_out_of_stock"] for s in summaries)
        unknown = sum(s["stores_unknown"] for s in summaries)
        logger.info(f"SKU 数: {len(summaries)}")
        logger.info(f"门店总数: {total}")
        logger.info(f"  有货: {in_stock}")
        logger.info(f"  无货: {out_stock}")
        logger.info(f"  未知: {unknown}")
        logger.info(f"输出文件: {output_path}")

        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())