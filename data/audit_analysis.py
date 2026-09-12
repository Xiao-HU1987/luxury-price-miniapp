#!/usr/bin/env python3
"""数据质量审计分析脚本"""

import json
import os
from collections import Counter, defaultdict
import statistics

BASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "lv")

# ============================================================
# 工具函数
# ============================================================
def read_jsonl(path):
    """流式读取 JSONL 文件"""
    records = []
    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def print_sep(title):
    print(f"\n{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}")


# ============================================================
# 1. 三国商品 SKU 统计
# ============================================================
print_sep("1. 三国商品 SKU 统计")

# --- CN ---
cn_products = read_jsonl(os.path.join(BASE, "CN/products_CN.jsonl"))
cn_sku_ids = [r.get("sku_id", "") for r in cn_products]
cn_sku_set = set(cn_sku_ids)
cn_prices = [r.get("price") for r in cn_products if r.get("price") is not None]

print("\n--- CN 商品 SKU ---")
print(f"  总记录数: {len(cn_products)}")
print(f"  唯一 SKU 数: {len(cn_sku_set)}")
print(f"  重复 SKU 数: {len(cn_sku_ids) - len(cn_sku_set)}")
# SKU 格式分布
cn_format = Counter()
for s in cn_sku_set:
    prefix = s[0] if s else "空"
    cn_format[prefix] += 1
print(f"  SKU 格式分布: {dict(cn_format)}")
if cn_prices:
    print(f"  价格范围: min={min(cn_prices):.0f}, max={max(cn_prices):.0f}, avg={statistics.mean(cn_prices):.0f}")
# 列出重复 SKU
cn_dup = [s for s, c in Counter(cn_sku_ids).items() if c > 1]
if cn_dup:
    print(f"  重复 SKU 列表 (前20): {cn_dup[:20]}")

# --- JP ---
jp_products = read_jsonl(os.path.join(BASE, "JP/products_JP.jsonl"))
jp_sku_ids = [r.get("sku_id", "") for r in jp_products]
jp_sku_set = set(jp_sku_ids)
jp_prices = [r.get("price") for r in jp_products if r.get("price") is not None]

print("\n--- JP 商品 SKU ---")
print(f"  总记录数: {len(jp_products)}")
print(f"  唯一 SKU 数: {len(jp_sku_set)}")
print(f"  重复 SKU 数: {len(jp_sku_ids) - len(jp_sku_set)}")
jp_format = Counter()
for s in jp_sku_set:
    prefix = s[0] if s else "空"
    jp_format[prefix] += 1
print(f"  SKU 格式分布: {dict(jp_format)}")
if jp_prices:
    print(f"  价格范围: min={min(jp_prices):.0f}, max={max(jp_prices):.0f}, avg={statistics.mean(jp_prices):.0f}")
jp_dup = [s for s, c in Counter(jp_sku_ids).items() if c > 1]
if jp_dup:
    print(f"  重复 SKU 列表 (前20): {jp_dup[:20]}")

# JP 有 JPY 价格但无 CNY 价格的 SKU 数
# 需要从 JP 页面数据中看是否有 CNY 价格, 但 JP 数据中 currency 都是 JPY
# 检查 price_values 中是否有非 JPY 的价格
# 实际上 JP 产品数据中 currency 固定为 JPY，不会出现 CNY 价格
# 所以这个指标解释为：JP 中所有 SKU 都只有 JPY 价格
print(f"  有 JPY 价格但无 CNY 价格的 SKU 数: {len(jp_sku_set)} (JP 数据中 currency 均为 JPY)")

# --- KR ---
kr_products = read_jsonl(os.path.join(BASE, "KR/products_KR.jsonl"))
kr_sku_ids = [r.get("sku_id", "") for r in kr_products]
kr_sku_set = set(kr_sku_ids)
kr_prices = [r.get("price") for r in kr_products if r.get("price") is not None]

print("\n--- KR 商品 SKU ---")
print(f"  总记录数: {len(kr_products)}")
print(f"  唯一 SKU 数: {len(kr_sku_set)}")
print(f"  重复 SKU 数: {len(kr_sku_ids) - len(kr_sku_set)}")
kr_format = Counter()
for s in kr_sku_set:
    prefix = s[0] if s else "空"
    kr_format[prefix] += 1
print(f"  SKU 格式分布: {dict(kr_format)}")
if kr_prices:
    print(f"  价格范围: min={min(kr_prices):.0f}, max={max(kr_prices):.0f}, avg={statistics.mean(kr_prices):.0f}")
kr_dup = [s for s, c in Counter(kr_sku_ids).items() if c > 1]
if kr_dup:
    print(f"  重复 SKU 列表 (前20): {kr_dup[:20]}")


# ============================================================
# 2. 三国库存数据统计
# ============================================================
print_sep("2. 三国库存数据统计")

# --- JP merged ---
jp_merged = read_jsonl(os.path.join(BASE, "JP/merged_JP.jsonl"))
jp_inv_sku_ids = [r.get("sku_id", "") for r in jp_merged]
jp_inv_sku_set = set(jp_inv_sku_ids)

print("\n--- JP 库存数据 (merged_JP.jsonl) ---")
print(f"  有库存数据的 SKU 数: {len(jp_inv_sku_set)}")
print(f"  JP 商品 SKU 总数: {len(jp_sku_set)}")
jp_missing_sku = jp_sku_set - jp_inv_sku_set
print(f"  缺失库存的 SKU 数量: {len(jp_missing_sku)}")

# 每个 SKU 的门店数分布
jp_store_counts = [r.get("total_stores", 0) for r in jp_merged]
if jp_store_counts:
    print(f"  门店数分布: min={min(jp_store_counts)}, max={max(jp_store_counts)}, "
          f"avg={statistics.mean(jp_store_counts):.1f}, median={statistics.median(jp_store_counts):.0f}")

# 库存状态分布
jp_total_in_stock = sum(r.get("stores_in_stock", 0) for r in jp_merged)
jp_total_out = sum(r.get("stores_out_of_stock", 0) for r in jp_merged)
jp_total_unknown = sum(r.get("stores_unknown", 0) for r in jp_merged)
jp_total_store_records = jp_total_in_stock + jp_total_out + jp_total_unknown
if jp_total_store_records > 0:
    print(f"  库存状态分布 (按门店记录): in_stock={jp_total_in_stock} ({jp_total_in_stock/jp_total_store_records*100:.1f}%), "
          f"out_of_stock={jp_total_out} ({jp_total_out/jp_total_store_records*100:.1f}%), "
          f"unknown={jp_total_unknown} ({jp_total_unknown/jp_total_store_records*100:.1f}%)")

# 门店城市分布
jp_city_counter = Counter()
for r in jp_merged:
    for s in r.get("stores", []):
        city = s.get("store_city", "")
        jp_city_counter[city] += 1
print(f"  门店城市分布 (Top 10):")
for city, cnt in jp_city_counter.most_common(10):
    print(f"    {city or '(空)'}: {cnt}")

# 异常数据检测
jp_anomalies = []
for r in jp_merged:
    for s in r.get("stores", []):
        issues = []
        if not s.get("store_name", "").strip():
            issues.append("store_name为空")
        if not s.get("store_address", "").strip():
            issues.append("store_address为空")
        if s.get("stock_status") is None:
            issues.append("stock_status为null")
        if not s.get("store_city", "").strip():
            issues.append("store_city为空")
        if issues:
            jp_anomalies.append((r["sku_id"], s.get("store_name", ""), issues))
print(f"  JP 异常门店记录数: {len(jp_anomalies)}")
if jp_anomalies:
    print(f"  异常示例 (前10):")
    for sku, name, issues in jp_anomalies[:10]:
        print(f"    SKU={sku}, 门店={name}, 问题={issues}")

# --- KR API 库存 ---
kr_api = read_jsonl(os.path.join(BASE, "KR/inventories_KR_api.jsonl"))
kr_api_sku_ids = [r.get("sku_id", "") for r in kr_api]
kr_api_sku_set = set(kr_api_sku_ids)

print("\n--- KR 库存数据 (inventories_KR_api.jsonl) ---")
print(f"  总记录数 (门店级别): {len(kr_api)}")
print(f"  有库存数据的 SKU 数: {len(kr_api_sku_set)}")
print(f"  KR 商品 SKU 总数: {len(kr_sku_set)}")
kr_missing_api = kr_sku_set - kr_api_sku_set
print(f"  缺失库存的 SKU 数量: {len(kr_missing_api)}")

# 每个 SKU 的门店数分布
kr_api_store_per_sku = Counter(kr_api_sku_ids)
kr_api_store_counts = list(kr_api_store_per_sku.values())
if kr_api_store_counts:
    print(f"  门店数分布: min={min(kr_api_store_counts)}, max={max(kr_api_store_counts)}, "
          f"avg={statistics.mean(kr_api_store_counts):.1f}, median={statistics.median(kr_api_store_counts):.0f}")

# 库存状态分布
kr_api_status_counter = Counter(r.get("stock_status", "null") for r in kr_api)
print(f"  库存状态分布: ")
for status, cnt in kr_api_status_counter.most_common():
    print(f"    {status}: {cnt} ({cnt/len(kr_api)*100:.1f}%)")

# 门店城市分布
kr_api_city = Counter(r.get("store_city", "") for r in kr_api)
print(f"  门店城市分布 (Top 10):")
for city, cnt in kr_api_city.most_common(10):
    print(f"    {city or '(空)'}: {cnt}")

# 异常数据
kr_api_anomalies = []
for r in kr_api:
    issues = []
    if not r.get("store_name", "").strip():
        issues.append("store_name为空")
    if not r.get("store_address", "").strip():
        issues.append("store_address为空")
    if r.get("stock_status") is None:
        issues.append("stock_status为null")
    if not r.get("store_city", "").strip():
        issues.append("store_city为空")
    if issues:
        kr_api_anomalies.append((r["sku_id"], r.get("store_name", ""), issues))
print(f"  KR API 异常门店记录数: {len(kr_api_anomalies)}")
if kr_api_anomalies:
    print(f"  异常示例 (前10):")
    for sku, name, issues in kr_api_anomalies[:10]:
        print(f"    SKU={sku}, 门店={name}, 问题={issues}")

# --- KR 旧爬虫库存 ---
kr_stores = read_jsonl(os.path.join(BASE, "KR/inventories_KR_stores.jsonl"))
kr_stores_sku_ids = [r.get("sku_id", "") for r in kr_stores]
kr_stores_sku_set = set(kr_stores_sku_ids)

print("\n--- KR 旧爬虫库存 (inventories_KR_stores.jsonl) ---")
print(f"  总记录数 (门店级别): {len(kr_stores)}")
print(f"  有库存数据的 SKU 数: {len(kr_stores_sku_set)}")
kr_missing_stores = kr_sku_set - kr_stores_sku_set
print(f"  缺失库存的 SKU 数量: {len(kr_missing_stores)}")

kr_stores_store_per_sku = Counter(kr_stores_sku_ids)
kr_stores_store_counts = list(kr_stores_store_per_sku.values())
if kr_stores_store_counts:
    print(f"  门店数分布: min={min(kr_stores_store_counts)}, max={max(kr_stores_store_counts)}, "
          f"avg={statistics.mean(kr_stores_store_counts):.1f}, median={statistics.median(kr_stores_store_counts):.0f}")

kr_stores_status = Counter(r.get("stock_status", "null") for r in kr_stores)
print(f"  库存状态分布: ")
for status, cnt in kr_stores_status.most_common():
    print(f"    {status}: {cnt} ({cnt/len(kr_stores)*100:.1f}%)")

kr_stores_city = Counter(r.get("store_city", "") for r in kr_stores)
print(f"  门店城市分布 (Top 10):")
for city, cnt in kr_stores_city.most_common(10):
    print(f"    {city or '(空)'}: {cnt}")

kr_stores_anomalies = []
for r in kr_stores:
    issues = []
    if not r.get("store_name", "").strip():
        issues.append("store_name为空")
    if not r.get("store_address", "").strip():
        issues.append("store_address为空")
    if r.get("stock_status") is None:
        issues.append("stock_status为null")
    if not r.get("store_city", "").strip():
        issues.append("store_city为空")
    if issues:
        kr_stores_anomalies.append((r["sku_id"], r.get("store_name", ""), issues))
print(f"  KR 旧爬虫异常门店记录数: {len(kr_stores_anomalies)}")
if kr_stores_anomalies:
    print(f"  异常示例 (前10):")
    for sku, name, issues in kr_stores_anomalies[:10]:
        print(f"    SKU={sku}, 门店={name}, 问题={issues}")


# ============================================================
# 3. 三国交叉比对
# ============================================================
print_sep("3. 三国交叉比对")

print(f"  CN 唯一 SKU 数: {len(cn_sku_set)}")
print(f"  JP 唯一 SKU 数: {len(jp_sku_set)}")
print(f"  KR 唯一 SKU 数: {len(kr_sku_set)}")

cn_jp = cn_sku_set & jp_sku_set
cn_kr = cn_sku_set & kr_sku_set
jp_kr = jp_sku_set & kr_sku_set
all_three = cn_sku_set & jp_sku_set & kr_sku_set

cn_only = cn_sku_set - jp_sku_set - kr_sku_set
jp_only = jp_sku_set - cn_sku_set - kr_sku_set
kr_only = kr_sku_set - cn_sku_set - jp_sku_set

print(f"\n  交叉比对结果:")
print(f"  CN ∩ JP: {len(cn_jp)} 个 SKU")
print(f"  CN ∩ KR: {len(cn_kr)} 个 SKU")
print(f"  JP ∩ KR: {len(jp_kr)} 个 SKU")
print(f"  CN ∩ JP ∩ KR: {len(all_three)} 个 SKU")
print(f"  仅 CN 独有: {len(cn_only)} 个 SKU")
print(f"  仅 JP 独有: {len(jp_only)} 个 SKU")
print(f"  仅 KR 独有: {len(kr_only)} 个 SKU")


# ============================================================
# 4. 数据异常检测
# ============================================================
print_sep("4. 数据异常检测")

# 4.1 门店名称为空或异常
print("\n--- 4.1 门店名称为空 ---")
jp_empty_name = sum(1 for r in jp_merged for s in r.get("stores", []) if not s.get("store_name", "").strip())
kr_api_empty_name = sum(1 for r in kr_api if not r.get("store_name", "").strip())
kr_stores_empty_name = sum(1 for r in kr_stores if not r.get("store_name", "").strip())
print(f"  JP 门店名称为空: {jp_empty_name}")
print(f"  KR API 门店名称为空: {kr_api_empty_name}")
print(f"  KR 旧爬虫门店名称为空: {kr_stores_empty_name}")

# 检查门店名称是否包含商品名
print("\n--- 4.1b 门店名称异常 (非标准门店名) ---")
# 检查 JP 中是否有不包含 "ルイ･ヴィトン" 或 "Louis Vuitton" 的门店名
jp_unusual_names = set()
for r in jp_merged:
    for s in r.get("stores", []):
        name = s.get("store_name", "")
        if name and "ルイ" not in name and "Louis" not in name:
            jp_unusual_names.add(name)
if jp_unusual_names:
    print(f"  JP 非标准门店名 (前20): {list(jp_unusual_names)[:20]}")

# 4.2 地址为空或格式异常
print("\n--- 4.2 地址异常 ---")
jp_empty_addr = sum(1 for r in jp_merged for s in r.get("stores", []) if not s.get("store_address", "").strip())
kr_api_empty_addr = sum(1 for r in kr_api if not r.get("store_address", "").strip())
kr_stores_empty_addr = sum(1 for r in kr_stores if not r.get("store_address", "").strip())
print(f"  JP 地址为空: {jp_empty_addr}")
print(f"  KR API 地址为空: {kr_api_empty_addr}")
print(f"  KR 旧爬虫地址为空: {kr_stores_empty_addr}")

# 检查地址格式异常（仅包含邮编、非完整地址）
# JP: 地址以 "─" 开头
jp_addr_anomaly = []
for r in jp_merged:
    for s in r.get("stores", []):
        addr = s.get("store_address", "")
        if addr.startswith("─"):
            jp_addr_anomaly.append((r["sku_id"], s.get("store_name", ""), addr))
print(f"  JP 地址以'─'开头 (异常): {len(jp_addr_anomaly)}")
if jp_addr_anomaly:
    for sku, name, addr in jp_addr_anomaly[:5]:
        print(f"    SKU={sku}, 门店={name}, 地址={addr}")

# 4.3 库存状态全部为 unknown 的 SKU
print("\n--- 4.3 库存状态全部为 unknown 的 SKU ---")
# JP
jp_all_unknown = []
for r in jp_merged:
    if r.get("stores_unknown", 0) > 0 and r.get("stores_in_stock", 0) == 0 and r.get("stores_out_of_stock", 0) == 0:
        jp_all_unknown.append(r["sku_id"])
print(f"  JP 全部 unknown 的 SKU 数: {len(jp_all_unknown)}")
if jp_all_unknown:
    print(f"    SKU 列表: {jp_all_unknown[:20]}")

# KR API
kr_api_sku_status = defaultdict(set)
for r in kr_api:
    kr_api_sku_status[r["sku_id"]].add(r.get("stock_status", ""))
kr_api_all_unknown = [sku for sku, statuses in kr_api_sku_status.items() if statuses == {"unknown"} or statuses == {""}]
print(f"  KR API 全部 unknown 的 SKU 数: {len(kr_api_all_unknown)}")

# KR 旧爬虫
kr_stores_sku_status = defaultdict(set)
for r in kr_stores:
    kr_stores_sku_status[r["sku_id"]].add(r.get("stock_status", ""))
kr_stores_all_unknown = [sku for sku, statuses in kr_stores_sku_status.items() if statuses == {"unknown"} or statuses == {""}]
print(f"  KR 旧爬虫全部 unknown 的 SKU 数: {len(kr_stores_all_unknown)}")

# 4.4 同一个 SKU 在不同文件中门店数差异过大
print("\n--- 4.4 同一 SKU 在不同国家/文件中门店数差异 ---")
jp_sku_stores = {r["sku_id"]: r.get("total_stores", 0) for r in jp_merged}
kr_api_sku_stores = dict(Counter(kr_api_sku_ids))
kr_stores_sku_stores = dict(Counter(kr_stores_sku_ids))

# 比较 JP 和 KR API
common_jp_kr_api = set(jp_sku_stores.keys()) & set(kr_api_sku_stores.keys())
large_diff = []
for sku in common_jp_kr_api:
    jp_cnt = jp_sku_stores[sku]
    kr_cnt = kr_api_sku_stores[sku]
    if jp_cnt > 0 and kr_cnt > 0:
        ratio = max(jp_cnt, kr_cnt) / min(jp_cnt, kr_cnt)
        if ratio > 3:
            large_diff.append((sku, jp_cnt, kr_cnt, ratio))
large_diff.sort(key=lambda x: x[3], reverse=True)
print(f"  JP vs KR API 门店数差异>3倍的 SKU 数: {len(large_diff)}")
if large_diff:
    print(f"  差异最大的 (前10):")
    for sku, jp_cnt, kr_cnt, ratio in large_diff[:10]:
        print(f"    SKU={sku}: JP={jp_cnt} 门店, KR={kr_cnt} 门店, 倍率={ratio:.1f}")

# 4.5 城市名称为空的记录
print("\n--- 4.5 城市名称为空 ---")
jp_empty_city = sum(1 for r in jp_merged for s in r.get("stores", []) if not s.get("store_city", "").strip())
kr_api_empty_city = sum(1 for r in kr_api if not r.get("store_city", "").strip())
kr_stores_empty_city = sum(1 for r in kr_stores if not r.get("store_city", "").strip())
print(f"  JP 城市为空: {jp_empty_city}")
print(f"  KR API 城市为空: {kr_api_empty_city}")
print(f"  KR 旧爬虫城市为空: {kr_stores_empty_city}")

# 列出 KR 城市为空的示例
kr_api_empty_city_examples = [(r["sku_id"], r.get("store_name", ""), r.get("store_address", "")) for r in kr_api if not r.get("store_city", "").strip()]
if kr_api_empty_city_examples:
    print(f"  KR API 城市为空示例 (前5):")
    for sku, name, addr in kr_api_empty_city_examples[:5]:
        print(f"    SKU={sku}, 门店={name}, 地址={addr[:60]}...")

kr_stores_empty_city_examples = [(r["sku_id"], r.get("store_name", ""), r.get("store_address", "")) for r in kr_stores if not r.get("store_city", "").strip()]
if kr_stores_empty_city_examples:
    print(f"  KR 旧爬虫城市为空示例 (前5):")
    for sku, name, addr in kr_stores_empty_city_examples[:5]:
        print(f"    SKU={sku}, 门店={name}, 地址={addr[:60]}...")

# 4.6 额外检查: KR 旧爬虫中 store_id 与 store_name 不一致
print("\n--- 4.6 额外检查: KR 旧爬虫 store_id vs store_name ---")
kr_stores_id_name_mismatch = sum(1 for r in kr_stores if r.get("store_id", "") != r.get("store_name", ""))
print(f"  store_id != store_name 的记录数: {kr_stores_id_name_mismatch}")

# 4.7 KR 旧爬虫 city 值异常 (出现"여의도"这种区名而非城市名)
print("\n--- 4.7 KR 旧爬虫 store_city 异常值 ---")
kr_stores_city_samples = Counter(r.get("store_city", "") for r in kr_stores)
print(f"  KR 旧爬虫城市值分布:")
for city, cnt in kr_stores_city_samples.most_common():
    print(f"    {city or '(空)'}: {cnt}")

print("\n\n" + "="*70)
print("  分析完成")
print("="*70)