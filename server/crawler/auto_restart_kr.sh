#!/bin/bash
# KR 库存采集自动重试脚本
# 策略：等待1小时 → 启动 → 失败则等1小时 → 再启动 → 仍失败则通知用户

PYTHON=/opt/homebrew/bin/python3.11
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
LOG_FILE="$SCRIPT_DIR/auto_restart_kr.log"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

run_script() {
    log "启动 KR 库存采集脚本..."
    cd "$SCRIPT_DIR/.."
    $PYTHON -m crawler.lv_collect_inventory_kr 2>&1 | tee -a "$LOG_FILE"
    return ${PIPESTATUS[0]}
}

# 检查脚本是否已在运行
check_running() {
    local count=$(pgrep -f "lv_collect_inventory_kr" | grep -v $$ | wc -l)
    if [ "$count" -gt 0 ]; then
        log "脚本已在运行中 (PID: $(pgrep -f 'lv_collect_inventory_kr' | grep -v $$ | tr '\n' ' '))，跳过"
        return 1
    fi
    return 0
}

# 检查 Chrome CDP 是否可用
check_chrome() {
    if curl -s http://127.0.0.1:9333/json/version > /dev/null 2>&1; then
        return 0
    else
        log "ERROR: Chrome CDP (9333) 不可用，请手动启动 Chrome"
        return 1
    fi
}

# === 主流程 ===
log "=== 自动重试脚本启动 ==="
log "首次等待 1 小时冷却..."

sleep 3600

# 第 1 次尝试
log "=== 第 1 次尝试 ==="
if ! check_chrome; then
    log "Chrome 未运行，请手动启动后重试"
    exit 1
fi
if ! check_running; then
    exit 0
fi
run_script
EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then
    # 检查是否因 API 限流退出
    if grep -q "API 测试.*次均失败" "$LOG_FILE" 2>/dev/null; then
        log "第 1 次尝试：API 限流中，等待 1 小时后重试..."
    else
        log "=== 采集完成 ==="
        exit 0
    fi
else
    log "第 1 次尝试：脚本异常退出 (exit=$EXIT_CODE)，等待 1 小时后重试..."
fi

sleep 3600

# 第 2 次尝试
log "=== 第 2 次尝试 ==="
if ! check_chrome; then
    log "Chrome 未运行，请手动处理"
    log ">>> 需要人工介入：Chrome 不在运行，请手动启动 Chrome 并重新运行脚本"
    exit 1
fi
if ! check_running; then
    exit 0
fi
run_script
EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then
    if grep -q "API 测试.*次均失败" "$LOG_FILE" 2>/dev/null; then
        log "第 2 次尝试：API 仍限流"
        log ">>> 需要人工介入：2 次自动重试后 API 仍返回 403，请手动操作"
        exit 1
    else
        log "=== 采集完成 ==="
        exit 0
    fi
else
    log "第 2 次尝试：脚本异常退出 (exit=$EXIT_CODE)"
    log ">>> 需要人工介入：请手动检查并重新运行"
    exit 1
fi