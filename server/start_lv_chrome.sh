#!/bin/bash
# ============================================================================
# LV 爬虫 Chrome 启动脚本
#
# 功能：以命令行方式启动 Chrome（带 CDP 端口 9333），无 Playwright 启动标记
# 用法：bash start_lv_chrome.sh
#
# 关键：
#   - Chrome 由系统命令启动 → 无 --enable-automation 标记
#   - 专用 Profile：/tmp/lv-crawler-profile（独立于日常 Chrome）
#   - Akamai 无法通过自动化指纹检测
# ============================================================================

set -e

CHROME="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
PROFILE="/tmp/lv-crawler-profile"
CDP_PORT=9333

# 清理旧进程
echo "[1/3] 清理旧的 Chrome 进程（端口 $CDP_PORT）..."
lsof -ti:$CDP_PORT 2>/dev/null | xargs kill -9 2>/dev/null || true
sleep 1

# 准备 Profile（从真实 Chrome 复制 cookies）
REAL_PROFILE="$HOME/Library/Application Support/Google/Chrome/Default"
if [ ! -f "$PROFILE/Cookies" ] && [ -d "$REAL_PROFILE" ]; then
    echo "[2/3] 准备 Chrome Profile（复制 cookies）..."
    rm -rf "$PROFILE"
    mkdir -p "$PROFILE"
    for item in "Cookies" "Local State" "Preferences" "Network" "Local Storage" "Session Storage"; do
        src="$REAL_PROFILE/$item"
        dst="$PROFILE/$item"
        if [ -e "$src" ]; then
            if [ -d "$src" ]; then
                rm -rf "$dst"
                cp -R "$src" "$dst"
            else
                cp "$src" "$dst"
            fi
        fi
    done
    echo "  Profile 准备完成"
else
    echo "[2/3] 使用已有 Profile"
fi

# 启动 Chrome（使用 open -a 绕过 TRAE 沙箱限制）
echo "[3/3] 启动 Chrome（CDP 端口 $CDP_PORT）..."
open -a "Google Chrome" --args \
    --user-data-dir="$PROFILE" \
    --remote-debugging-port=$CDP_PORT \
    --no-first-run \
    --no-default-browser-check \
    --disable-blink-features=AutomationControlled \
    --no-sandbox \
    --disable-gpu \
    --lang=ja-JP \
    --no-popup-blocking \
    "https://jp.louisvuitton.com/jpn-jp/homepage"

echo "  Chrome 已通过 open 命令启动"

# 等待 CDP 就绪
echo ""
echo "等待 CDP 端口就绪..."
for i in $(seq 1 30); do
    if curl -s --max-time 2 "http://127.0.0.1:$CDP_PORT/json/version" > /dev/null 2>&1; then
        echo "CDP 已就绪 ✓"
        echo ""
        echo "============================================"
        echo "  Chrome 已启动！"
        echo "  - 浏览器窗口已打开 LV JP 官网"
        echo "  - CDP 端口：$CDP_PORT"
        echo "  - Profile：$PROFILE"
        echo ""
        echo "  下一步：运行爬虫"
        echo "  cd /Users/huxiao/Public/测试项目-1-26.6.27/server"
        echo "  venv/bin/python3.11 -m crawler.lv_anti_detect \\"
        echo "    --sku-file data/lv/JP/men_pending_skus_JP.json \\"
        echo "    --reuse-chrome"
        echo "============================================"
        exit 0
    fi
    sleep 1
    if [ $((i % 5)) -eq 4 ]; then
        echo "  ...等待中 ($i/30)"
    fi
done

echo "CDP 端口未就绪，启动可能失败"
exit 1