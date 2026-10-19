#!/bin/bash
# 启动带 CDP 调试端口的 Chrome（LV 爬虫专用）
# 使用：先关闭所有 Chrome 窗口，然后执行此脚本
# 关闭：killall -9 "Google Chrome"
#
# 注意：必须用 nohup + 二进制直接启动，open -na 方式在 macOS 上无法正确
# 传递 --remote-debugging-port 参数给主进程。
#
# 运行爬虫时，必须用此脚本提供的 run 子命令（自动清空代理环境变量）：
#   ./start_lv_chrome.sh run --mode single --url "https://..."
set -e

PORT=${1:-9333}
CHROME_BIN="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
USER_DATA_DIR="$HOME/Library/Application Support/Google/Chrome-LV-Crawler"
LOG_FILE="/tmp/chrome-lv-crawler.log"

# 启动 Chrome 的函数（直连模式，不使用代理——VPN代理IP会被Akamai封禁）
start_chrome() {
    echo "🛑 关闭旧 Chrome 进程..."
    pkill -f "Google Chrome" 2>/dev/null || true
    sleep 2

    rm -f "$USER_DATA_DIR/SingletonLock" 2>/dev/null || true
    mkdir -p "$USER_DATA_DIR"

    echo "🚀 启动 Chrome (CDP port=$PORT, 直连模式无代理)..."
    echo "   用户数据目录: $USER_DATA_DIR"
    echo "   说明: VPN代理IP(203.10.99.75)被Akamai封禁，直连(上海移动住宅IP)可绕过"
    nohup "$CHROME_BIN" \
        --remote-debugging-port=$PORT \
        --disable-blink-features=AutomationControlled \
        --user-data-dir="$USER_DATA_DIR" \
        --no-first-run \
        --no-default-browser-check \
        > "$LOG_FILE" 2>&1 &

    sleep 3
    echo ""
    echo "🔍 验证 CDP 端口..."
    if curl --noproxy '*' -s "http://127.0.0.1:$PORT/json/version" | head -c 300; then
        echo ""
        echo ""
        echo "✅ CDP 端口 $PORT 已就绪！"
        echo ""
        echo "📋 后续步骤："
        echo "   1. 在弹出的 Chrome 中手动访问 https://jp.louisvuitton.com"
        echo "      （如遇验证码/人机验证，请手动完成）"
        echo ""
        echo "   2. 验证通过后，运行爬虫（自动清空代理环境变量）："
        echo "      ./start_lv_chrome.sh run --mode single \\"
        echo "          --url 'https://jp.louisvuitton.com/jpn-jp/products/YOUR_URL'"
        echo ""
        echo "   3. 关闭 Chrome：./start_lv_chrome.sh stop"
        echo ""
        echo "📂 启动日志：$LOG_FILE"
    else
        echo ""
        echo "❌ CDP 端口 $PORT 未就绪！查看日志：cat $LOG_FILE"
        exit 1
    fi
}

# 停止 Chrome
stop_chrome() {
    echo "🛑 关闭 Chrome..."
    pkill -f "Google Chrome" 2>/dev/null || true
    echo "✅ 已关闭"
}

# 在干净的环境下运行爬虫
run_crawler() {
    # 清空代理环境变量，避免 Playwright 连接 127.0.0.1:9333 被代理拦截
    cd "$(dirname "$0")/server"
    env -u HTTP_PROXY -u HTTPS_PROXY -u http_proxy -u https_proxy \
        -u all_proxy -u ALL_PROXY -u SOCKS_PROXY -u socks_proxy \
        venv/bin/python3.11 -m crawler.lv_crawler_multi "$@"
}

# 检查状态
check_status() {
    if lsof -i :$PORT >/dev/null 2>&1; then
        echo "✅ Chrome CDP 在端口 $PORT 监听"
        curl --noproxy '*' -s "http://127.0.0.1:$PORT/json/version" | python3 -m json.tool
    else
        echo "❌ 端口 $PORT 未监听，请先执行：$0"
    fi
}

# 入口分发
case "${1:-start}" in
    start|"")
        start_chrome
        ;;
    stop)
        stop_chrome
        ;;
    status)
        check_status
        ;;
    run)
        shift
        run_crawler "$@"
        ;;
    *)
        echo "用法: $0 [start|stop|status|run ...crawler-args]"
        echo ""
        echo "  start  - 启动 Chrome（默认）"
        echo "  stop   - 关闭 Chrome"
        echo "  status - 查看 CDP 端口状态"
        echo "  run    - 在干净环境下运行爬虫（推荐）"
        echo ""
        echo "示例："
        echo "  $0 start"
        echo "  $0 run --mode single --url 'https://jp.louisvuitton.com/jpn-jp/products/nano-speedy-nanogram-monogram-008476'"
        echo "  $0 stop"
        exit 1
        ;;
esac

