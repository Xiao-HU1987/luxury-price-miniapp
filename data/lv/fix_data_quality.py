"""数据质量修复脚本
1. 过滤 JP 线上客服记录
2. 标准化 JP 城市名
3. 去重 CN 商品记录
4. 排查 JP/KR 价格为 0 的 SKU
"""
import json
import shutil
from pathlib import Path

BASE = Path(__file__).resolve().parent

# ============================================================
# 1. JP 城市名标准化映射（市 → 都道府県）
# ============================================================
CITY_STANDARDIZE = {
    "大阪市": "大阪府",
    "名古屋市": "愛知県",
    "福岡市": "福岡県",
    "京都市": "京都府",
    "横浜市": "神奈川県",
    "札幌市": "北海道",
}

# ============================================================
# 1+2. 修复 JP merged_JP.jsonl
# ============================================================
print("=" * 60)
print("1+2. 修复 JP merged_JP.jsonl")
print("=" * 60)

jp_path = BASE / "JP" / "merged_JP.jsonl"
jp_bak = BASE / "JP" / "merged_JP.jsonl.bak"
shutil.copy2(jp_path, jp_bak)

filtered_online = 0
city_standardized = 0
total_skus = 0
total_stores_before = 0
total_stores_after = 0

with open(jp_path, "r") as f_in, open(str(jp_path) + ".tmp", "w") as f_out:
    for line in f_in:
        r = json.loads(line.strip())
        total_skus += 1
        stores = r.get("stores", [])
        total_stores_before += len(stores)

        # 过滤线上客服
        new_stores = []
        for s in stores:
            if "オンライン" in s.get("store_name", ""):
                filtered_online += 1
                continue
            # 标准化城市名
            city = s.get("store_city", "")
            if city in CITY_STANDARDIZE:
                s["store_city"] = CITY_STANDARDIZE[city]
                city_standardized += 1
            new_stores.append(s)

        r["stores"] = new_stores
        total_stores_after += len(new_stores)

        # 更新汇总字段
        r["total_stores"] = len(new_stores)
        in_stock = sum(1 for s in new_stores if s.get("stock_status") == "in_stock")
        out_stock = sum(1 for s in new_stores if s.get("stock_status") == "out_of_stock")
        unknown = len(new_stores) - in_stock - out_stock
        r["stores_in_stock"] = in_stock
        r["stores_out_of_stock"] = out_stock
        r["stores_unknown"] = unknown
        # 更新 channel_status
        if in_stock > 0:
            r["channel_status"] = "门店有售且有库存"
        else:
            r["channel_status"] = "门店有售无库存"

        f_out.write(json.dumps(r, ensure_ascii=False) + "\n")

Path(str(jp_path) + ".tmp").replace(jp_path)
print(f"  SKU 总数: {total_skus}")
print(f"  过滤线上客服: {filtered_online} 条")
print(f"  城市名标准化: {city_standardized} 条")
print(f"  门店数: {total_stores_before} → {total_stores_after}")
print(f"  备份: {jp_bak}")

# 验证
print("\n  验证城市名:")
city_verify = {}
with open(jp_path) as f:
    for line in f:
        r = json.loads(line.strip())
        for s in r.get("stores", []):
            c = s.get("store_city", "")
            city_verify[c] = city_verify.get(c, 0) + 1
for c, n in sorted(city_verify.items(), key=lambda x: -x[1])[:12]:
    print(f"    {c}: {n}")

online_verify = 0
with open(jp_path) as f:
    for line in f:
        r = json.loads(line.strip())
        for s in r.get("stores", []):
            if "オンライン" in s.get("store_name", ""):
                online_verify += 1
print(f"  线上客服残留: {online_verify}")

# ============================================================
# 3. 去重 CN products_CN.jsonl
# ============================================================
print("\n" + "=" * 60)
print("3. 去重 CN products_CN.jsonl")
print("=" * 60)

cn_path = BASE / "CN" / "products_CN.jsonl"
cn_bak = BASE / "CN" / "products_CN.jsonl.bak"
shutil.copy2(cn_path, cn_bak)

seen = set()
dup_count = 0
total_cn = 0
with open(cn_path, "r") as f_in, open(str(cn_path) + ".tmp", "w") as f_out:
    for line in f_in:
        total_cn += 1
        r = json.loads(line.strip())
        sid = r.get("sku_id", "")
        if sid in seen:
            dup_count += 1
            continue
        seen.add(sid)
        f_out.write(line)

Path(str(cn_path) + ".tmp").replace(cn_path)
print(f"  原始记录: {total_cn}")
print(f"  去重移除: {dup_count}")
print(f"  保留唯一: {len(seen)}")
print(f"  备份: {cn_bak}")

# 验证
verify = set()
with open(cn_path) as f:
    for line in f:
        verify.add(json.loads(line.strip()).get("sku_id", ""))
print(f"  验证唯一 SKU: {len(verify)}")

# ============================================================
# 4. 排查 JP/KR 价格为 0 的 SKU
# ============================================================
print("\n" + "=" * 60)
print("4. 排查 JP/KR 价格为 0 的 SKU")
print("=" * 60)

# 检查这些 SKU 是否有 URL 和名称
for country, file_name in [("JP", "JP/products_JP.jsonl"), ("KR", "KR/products_KR.jsonl")]:
    print(f"\n  [{country}]")
    zero_skus = []
    with open(BASE / file_name) as f:
        for line in f:
            r = json.loads(line.strip())
            if r.get("price", 0) == 0:
                zero_skus.append(r)

    for r in zero_skus:
        has_url = bool(r.get("url", ""))
        has_name = bool(r.get("name", ""))
        has_name_cn = bool(r.get("name_cn", ""))
        print(f"    {r['sku_id']}: url={has_url} name={has_name} name_cn={has_name_cn} "
              f"url={r.get('url','')[:60] if has_url else 'N/A'}")

    # 在三国其他数据中查找这些 SKU
    print(f"    在三国交叉查找:")
    for z in zero_skus:
        sid = z["sku_id"]
        found_in = []
        for other, ofile in [("JP", "JP/products_JP.jsonl"), ("CN", "CN/products_CN.jsonl"), ("KR", "KR/products_KR.jsonl")]:
            if other == country:
                continue
            with open(BASE / ofile) as f:
                for line in f:
                    r = json.loads(line.strip())
                    if r.get("sku_id") == sid and r.get("price", 0) > 0:
                        found_in.append(f"{other}(¥{r['price']})" if "JP" in other or "CN" in other else f"{other}(₩{r['price']})")
                        break
        if found_in:
            print(f"      {sid}: 其他国有价格 → {', '.join(found_in)}")
        else:
            print(f"      {sid}: 三国均无价格")

print("\n" + "=" * 60)
print("修复完成")
print("=" * 60)