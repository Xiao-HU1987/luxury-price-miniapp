#!/bin/bash
# KR 库存采集 — 自适应冷却包装器
# 基础冷却 2h，每轮失败 +1h，直到 API 恢复

BASE_COOLDOWN=$((2 * 3600))   # 2 小时
COOLDOWN_INCREMENT=$((1 * 3600))  # 每次 +1 小时
MAX_COOLDOWNS=10  # 最多 10 轮（避免无限循环）

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$PROJECT_DIR"

echo "=============================================="
echo "KR 库存采集 — 自适应冷却模式"
echo "基础冷却: 2h, 增量: +1h/轮"
echo "启动时间: $(date '+%Y-%m-%d %H:%M:%S')"
echo "=============================================="

cooldown_round=0
current_cooldown=$BASE_COOLDOWN

while true; do
    # 统计剩余 SKU
    remaining=$(python3 -c "
import json
with open('$PROJECT_DIR/../data/lv/KR/products_KR_clean.jsonl') as f:
    all_skus = {json.loads(l.strip())['sku_id'] for l in f if l.strip()}
done = set()
try:
    with open('$PROJECT_DIR/../data/lv/KR/inventories_KR_api.jsonl') as f:
        for l in f:
            r = json.loads(l.strip())
            done.add(r['sku_id'])
except: pass
try:
    with open('$PROJECT_DIR/../data/lv/KR/inventories_KR_stores.jsonl') as f:
        for l in f:
            r = json.loads(l.strip())
            done.add(r['sku_id'])
except: pass
remaining = all_skus - done
print(f'{len(done)}/{len(all_skus)} ({len(remaining)} 剩余)')
" 2>/dev/null)

    echo ""
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] 当前进度: $remaining"

    # 运行采集脚本
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] 启动采集..."
    /opt/homebrew/bin/python3.11 -m crawler.lv_collect_inventory_kr 2>&1
    exit_code=$?

    # 检查是否还有剩余
    remaining_count=$(python3 -c "
import json
with open('$PROJECT_DIR/../data/lv/KR/products_KR_clean.jsonl') as f:
    all_skus = {json.loads(l.strip())['sku_id'] for l in f if l.strip()}
done = set()
try:
    with open('$PROJECT_DIR/../data/lv/KR/inventories_KR_api.jsonl') as f:
        for l in f:
            r = json.loads(l.strip())
            done.add(r['sku_id'])
except: pass
try:
    with open('$PROJECT_DIR/../data/lv/KR/inventories_KR_stores.jsonl') as f:
        for l in f:
            r = json.loads(l.strip())
            done.add(r['sku_id'])
except: pass
print(len(all_skus - done))
" 2>/dev/null)

    if [ "$remaining_count" -eq 0 ] 2>/dev/null; then
        echo ""
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] 全部采集完成！"
        break
    fi

    # 自适应冷却
    echo ""
    if [ $exit_code -eq 0 ] && [ "$remaining_count" -gt 0 ]; then
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] 脚本正常退出，还有 $remaining_count 个 SKU，冷却后重试"
    else
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] 脚本因 403 限流退出，剩余 $remaining_count 个 SKU"
    fi

    cooldown_round=$((cooldown_round + 1))
    if [ $cooldown_round -gt 1 ]; then
        current_cooldown=$((current_cooldown + COOLDOWN_INCREMENT))
    fi

    echo "[$(date '+%Y-%m-%d %H:%M:%S')] 第 ${cooldown_round} 轮冷却: ${current_cooldown}s ($((current_cooldown / 3600))h $(((current_cooldown % 3600) / 60))m)"
    echo "  预计恢复: $(date -v+${current_cooldown}S '+%Y-%m-%d %H:%M:%S')"

    if [ $cooldown_round -ge $MAX_COOLDOWNS ]; then
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] 已达最大冷却轮数 ($MAX_COOLDOWNS)，退出"
        break
    fi

    sleep $current_cooldown

    # 检查 Chrome 是否还在运行
    if ! curl -s http://127.0.0.1:9333/json/version > /dev/null 2>&1; then
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] Chrome 已关闭，需要重新启动"
        bash "$SCRIPT_DIR/start_lv_chrome.sh"
        sleep 10
    fi
done

echo ""
echo "[$(date '+%Y-%m-%d %H:%M:%S')] 任务结束"