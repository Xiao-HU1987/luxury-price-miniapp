#!/usr/bin/env python3
"""盘点 /data/lv/ 目录下 CN/JP/KR 三个国家的数据文件情况"""

import json
import os
from collections import defaultdict

BASE_DIR = "/Users/huxiao/Public/测试项目-1-26.6.27/data/lv"
COUNTRIES = ["CN", "JP", "KR"]


def count_lines(filepath):
    """统计文件行数（非空行）"""
    if not os.path.exists(filepath):
        return 0
    count = 0
    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                count += 1
    return count


def get_file_size(filepath):
    """获取文件大小的人类可读格式"""
    if not os.path.exists(filepath):
        return "N/A"
    size = os.path.getsize(filepath)
    if size < 1024:
        return f"{size} B"
    elif size < 1024 * 1024:
        return f"{size / 1024:.1f} KB"
    else:
        return f"{size / (1024 * 1024):.2f} MB"


def extract_skus_from_products(filepath):
    """从 products 文件中提取 SKU 集合和行数"""
    if not os.path.exists(filepath):
        return set(), 0
    skus = set()
    line_count = 0
    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            line_count += 1
            try:
                obj = json.loads(line)
                sid = obj.get("sku_id")
                if sid:
                    skus.add(sid)
            except json.JSONDecodeError:
                pass
    return skus, line_count


def extract_skus_from_inventory(filepath):
    """从 inventory 文件中提取 SKU 集合和记录数"""
    if not os.path.exists(filepath):
        return set(), 0
    skus = set()
    record_count = 0
    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            record_count += 1
            try:
                obj = json.loads(line)
                sid = obj.get("sku_id")
                if sid:
                    skus.add(sid)
            except json.JSONDecodeError:
                pass
    return skus, record_count


def analyze_merged_file(filepath):
    """分析 merged 文件"""
    if not os.path.exists(filepath):
        return None
    skus, record_count = extract_skus_from_inventory(filepath)
    return {"skus": skus, "records": record_count}


def analyze_inventory_store_file(filepath):
    """分析 inventories_stores 文件（展开的 store 级别记录）"""
    if not os.path.exists(filepath):
        return None
    skus = set()
    record_count = 0
    stores_in_stock = 0
    stores_out_stock = 0
    stores_unknown = 0
    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            record_count += 1
            try:
                obj = json.loads(line)
                sid = obj.get("sku_id")
                if sid:
                    skus.add(sid)
                st = obj.get("stock_status", "")
                if st == "in_stock":
                    stores_in_stock += 1
                elif st == "out_of_stock":
                    stores_out_stock += 1
                else:
                    stores_unknown += 1
            except json.JSONDecodeError:
                pass
    return {
        "skus": skus,
        "records": record_count,
        "stores_in_stock": stores_in_stock,
        "stores_out_stock": stores_out_stock,
        "stores_unknown": stores_unknown,
    }


def classify_files(files):
    """将文件分类"""
    categories = {
        "products": [],
        "inventories": [],
        "merged": [],
        "other": [],
    }
    for f in files:
        base = f.lower()
        if "product" in base and "url" not in base:
            categories["products"].append(f)
        elif "inventor" in base:
            categories["inventories"].append(f)
        elif "merged" in base:
            categories["merged"].append(f)
        else:
            categories["other"].append(f)
    return categories


def main():
    print("=" * 72)
    print("   LV 数据文件盘点报告")
    print("=" * 72)

    # 用于跨国家对比的 products SKU 汇总
    all_products_skus = {}

    for country in COUNTRIES:
        country_dir = os.path.join(BASE_DIR, country)
        if not os.path.isdir(country_dir):
            print(f"\n  [{country}] 目录不存在")
            continue

        all_files = sorted(os.listdir(country_dir))
        # 过滤掉子目录和备份文件
        files = [f for f in all_files if os.path.isfile(os.path.join(country_dir, f))]
        classified = classify_files(files)

        print(f"\n{'─' * 72}")
        print(f"  [{country}] 目录: {country_dir}")
        print(f"{'─' * 72}")

        # 1. 文件清单
        print(f"\n  📁 全部文件 ({len(files)} 个):")
        for f in files:
            fpath = os.path.join(country_dir, f)
            size = get_file_size(fpath)
            lines = count_lines(fpath)
            print(f"      {f:<50s}  {size:>8s}  {lines:>6d} 行")

        # 2. Products 文件分析
        print(f"\n  📦 Products（商品信息）文件:")
        if classified["products"]:
            for f in classified["products"]:
                fpath = os.path.join(country_dir, f)
                skus, line_count = extract_skus_from_products(fpath)
                print(f"      {f}")
                print(f"         → 记录数: {line_count:,}  去重 SKU: {len(skus):,}")
                if line_count > 0 and len(skus) > 0:
                    dup_rate = (1 - len(skus) / line_count) * 100
                    print(f"         → 重复率: {dup_rate:.1f}%")
                # 保存主 products 文件的 SKU 用于后续交叉分析
                if f in ("products_CN.jsonl", "products_JP.jsonl", "products_KR.jsonl"):
                    all_products_skus[country] = skus
        else:
            print(f"      (无)")

        # 3. Inventories 文件分析
        print(f"\n  🏪 Inventories（库存数据）文件:")
        if classified["inventories"]:
            for f in classified["inventories"]:
                fpath = os.path.join(country_dir, f)
                # 判断是 stores 展开格式还是聚合格式
                if "_stores" in f.lower():
                    result = analyze_inventory_store_file(fpath)
                    if result:
                        print(f"      {f}")
                        print(f"         → 记录数: {result['records']:,}  去重 SKU: {len(result['skus']):,}")
                        print(f"         → 有货: {result['stores_in_stock']:,}  "
                              f"缺货: {result['stores_out_stock']:,}  "
                              f"未知: {result['stores_unknown']:,}")
                else:
                    skus, record_count = extract_skus_from_inventory(fpath)
                    print(f"      {f}")
                    print(f"         → 记录数: {record_count:,}  去重 SKU: {len(skus):,}")
        else:
            print(f"      (无)")

        # 4. Merged 文件分析
        print(f"\n  🔗 Merged（合并数据）文件:")
        if classified["merged"]:
            for f in classified["merged"]:
                fpath = os.path.join(country_dir, f)
                result = analyze_merged_file(fpath)
                if result:
                    print(f"      {f}  ✅ 存在")
                    print(f"         → 记录数: {result['records']:,}  去重 SKU: {len(result['skus']):,}")
        else:
            print(f"      (无)")

        # 5. Other 文件
        if classified["other"]:
            print(f"\n  📄 其他文件:")
            for f in classified["other"]:
                fpath = os.path.join(country_dir, f)
                lines = count_lines(fpath)
                print(f"      {f:<50s}  {lines:>6d} 行")

    # 6. 跨国家 SKU 交叉分析
    print(f"\n{'═' * 72}")
    print(f"  跨国家 SKU 交叉分析")
    print(f"{'═' * 72}")

    for country in COUNTRIES:
        if country in all_products_skus:
            print(f"\n  [{country}] products 文件 SKU 数量: {len(all_products_skus[country]):,}")

    if len(all_products_skus) >= 2:
        countries_list = list(all_products_skus.keys())
        print(f"\n  SKU 交集/并集分析:")
        for i, c1 in enumerate(countries_list):
            for c2 in countries_list[i + 1 :]:
                s1 = all_products_skus[c1]
                s2 = all_products_skus[c2]
                common = s1 & s2
                only_c1 = s1 - s2
                only_c2 = s2 - s1
                print(f"      {c1} ∩ {c2}: {len(common):,} 个共同 SKU")
                print(f"      {c1} 独有: {len(only_c1):,} 个")
                print(f"      {c2} 独有: {len(only_c2):,} 个")

    # 7. 检查 aligned 目录
    aligned_dir = os.path.join(BASE_DIR, "aligned")
    if os.path.isdir(aligned_dir):
        print(f"\n{'─' * 72}")
        print(f"  [aligned/] 整合目录")
        print(f"{'─' * 72}")
        for f in sorted(os.listdir(aligned_dir)):
            fpath = os.path.join(aligned_dir, f)
            if os.path.isfile(fpath):
                size = get_file_size(fpath)
                lines = count_lines(fpath)
                print(f"      {f:<50s}  {size:>8s}  {lines:>6d} 行")

    # 根目录额外文件
    extra_files = [f for f in os.listdir(BASE_DIR) if os.path.isfile(os.path.join(BASE_DIR, f))]
    if extra_files:
        print(f"\n  📄 lv/ 根目录文件:")
        for f in sorted(extra_files):
            fpath = os.path.join(BASE_DIR, f)
            size = get_file_size(fpath)
            lines = count_lines(fpath)
            print(f"      {f:<50s}  {size:>8s}  {lines:>6d} 行")

    print(f"\n{'=' * 72}")
    print("  盘点完成")
    print(f"{'=' * 72}")


if __name__ == "__main__":
    main()