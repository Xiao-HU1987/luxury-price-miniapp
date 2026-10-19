#!/bin/bash
# Chrome CDP 管理脚本
# 统一管理Chrome启动、CDP端口、profile目录，避免重复启动和冲突

CHROME_APP="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
CDP_PORT=9333
PROFILE_DIR="/tmp/chrome-cdp-profile"
LOG_FILE="/tmp/chrome-cdp.log"

# 检查CDP是否已就绪
check_cdp() {
    curl -s --noproxy '*' --connect-timeout 2 "http://127.0.0.1:${CDP_PORT}/json/version" 2>/dev/null | grep -q "Browser"
}

# 启动Chrome
start_chrome() {
    if check_cdp; then
        echo "CDP已在运行 (端口 ${CDP_PORT})"
        return 0
    fi

    # 清理旧进程
    pkill -f "chrome-cdp-profile" 2>/dev/null
    sleep 2

    # 清理锁文件
    rm -f "${PROFILE_DIR}/SingletonLock" "${PROFILE_DIR}/SingletonCookie" "${PROFILE_DIR}/SingletonSocket" 2>/dev/null

    # 启动Chrome
    "${CHROME_APP}" \
        --remote-debugging-port=${CDP_PORT} \
        --user-data-dir=${PROFILE_DIR} \
        '--remote-allow-origins=*' \
        --no-first-run \
        --no-default-browser-check \
        > "${LOG_FILE}" 2>&1 &

    echo "Chrome启动中 (PID=$!)..."

    # 等待CDP就绪
    for i in $(seq 1 10); do
        if check_cdp; then
            echo "CDP就绪 (端口 ${CDP_PORT})"
            return 0
        fi
        sleep 2
    done

    echo "错误: CDP未能在20秒内就绪"
    return 1
}

# 停止Chrome
stop_chrome() {
    pkill -f "chrome-cdp-profile" 2>/dev/null
    echo "Chrome已停止"
}

# 重启Chrome
restart_chrome() {
    stop_chrome
    sleep 3
    start_chrome
}

case "${1:-start}" in
    start)   start_chrome ;;
    stop)    stop_chrome ;;
    restart) restart_chrome ;;
    status)  check_cdp && echo "CDP运行中" || echo "CDP未运行" ;;
    *)       echo "用法: $0 {start|stop|restart|status}" ;;
esac
