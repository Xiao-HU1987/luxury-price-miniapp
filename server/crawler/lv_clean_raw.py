"""LV 三站原始数据清理脚本

清理规则：
1. 修复 sku_id 错位（用 source_url 中的真实 SKU 替换）
2. 按 sku_id 去重（保留最新一条）
3. 删除无价格、无名称的无用条目
4. 保留原始文件不变，生成 _clean 后缀的清理后文件

用法：
    python3 -m crawler.lv_clean_raw
"""
from __future__ import annotations

import json
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

DATA_ROOT = BASE_DIR.parent / "data" / "lv"


def _extract_sku_from_url(url: str) -> str:
    """从 source_url 中提取真实 SKU"""
    if not url:
        return ""
    # 匹配 /products/slug-name/SKU 格式
    m = re.search(r'/products/[^/]+/([A-Z]\w{4,})', url)
    if m:
        return m.group(1).upper()
    # 匹配 /products/-/SKU 格式
    m = re.search(r'/products/-/([A-Z]\w{4,})', url)
    if m:
        return m.group(1).upper()
    return ""


def _load_jsonl(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    records = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def _save_jsonl(path: Path, records: List[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def clean_country(country: str) -> Dict[str, int]:
    """清理单个国家的原始数据"""
    orig_file = DATA_ROOT / country / f"products_{country}.jsonl"
    clean_file = DATA_ROOT / country / f"products_{country}_clean.jsonl"

    orig = _load_jsonl(orig_file)
    if not orig:
        print(f"[{country}] 原始文件不存在或为空: {orig_file}")
        return {"original": 0, "cleaned": 0, "duplicates": 0, "invalid": 0}

    print(f"\n[{country}] 原始数据: {len(orig)} 条")

    # 1. 修复 sku_id 错位（用 source_url 中的真实 SKU 替换）
    fixed_count = 0
    for p in orig:
        url_sku = _extract_sku_from_url(p.get("source_url", ""))
        if url_sku and p.get("sku_id", "").upper() != url_sku:
            p["sku_id"] = url_sku
            fixed_count += 1

    if fixed_count > 0:
        print(f"[{country}] 修复 sku_id 错位: {fixed_count} 条")

    # 2. 过滤无用条目（无sku_id、无价格、无名称）
    valid = []
    invalid = 0
    for p in orig:
        sku_id = p.get("sku_id", "").strip().upper()
        price = p.get("price")
        name_local = p.get("name_local", "") or p.get("name", "")

        if not sku_id:
            invalid += 1
            continue
        # 价格为0或None且无备选价格
        if (price is None or price <= 0):
            # 检查price_values是否有有效值
            price_values = p.get("price_values", [])
            if not price_values or all(v is None or v <= 0 for v in price_values):
                invalid += 1
                continue
        # 无名称（KR站可能name_local和name都为空）
        if not name_local:
            invalid += 1
            continue

        valid.append(p)

    print(f"[{country}] 过滤无用条目: {invalid} 条，剩余: {len(valid)} 条")

    # 2. 按 sku_id 去重（保留最新一条，按crawled_at排序）
    by_sku: Dict[str, Dict[str, Any]] = {}
    for p in valid:
        sku_id = p["sku_id"].strip().upper()
        existing = by_sku.get(sku_id)
        if existing is None:
            by_sku[sku_id] = p
        else:
            # 保留crawled_at更新的，或图片更多的
            existing_time = existing.get("crawled_at", "")
            new_time = p.get("crawled_at", "")
            if new_time > existing_time:
                by_sku[sku_id] = p
            elif new_time == existing_time:
                # 时间相同，保留图片更多的
                existing_imgs = len(existing.get("images") or [])
                new_imgs = len(p.get("images") or [])
                if new_imgs > existing_imgs:
                    by_sku[sku_id] = p

    cleaned = list(by_sku.values())
    duplicates = len(valid) - len(cleaned)

    print(f"[{country}] 去重: {duplicates} 条，最终: {len(cleaned)} 条")

    # 3. 保存清理后数据
    _save_jsonl(clean_file, cleaned)
    print(f"[{country}] 已保存: {clean_file}")

    return {
        "original": len(orig),
        "cleaned": len(cleaned),
        "duplicates": duplicates,
        "invalid": invalid,
    }


def main():
    print("=" * 60)
    print("LV 三站原始数据清理")
    print("=" * 60)

    total_stats = {}
    for country in ["CN", "JP", "KR"]:
        total_stats[country] = clean_country(country)

    print("\n" + "=" * 60)
    print("清理统计汇总")
    print("=" * 60)
    print(f"{'国家':<6} {'原始':<8} {'清理后':<8} {'重复':<8} {'无效':<8}")
    for country, stats in total_stats.items():
        print(f"{country:<6} {stats['original']:<8} {stats['cleaned']:<8} "
              f"{stats['duplicates']:<8} {stats['invalid']:<8}")

    print("\n✅ 原始数据清理完成！")
    print("注意：原始文件 products_XX.jsonl 保持不变，清理后文件为 products_XX_clean.jsonl")


if __name__ == "__main__":
    main()
