#!/bin/bash

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
PLIST_SOURCE="$SCRIPT_DIR/com.luxuryprice.gitsync.plist"
PLIST_DEST="$HOME/Library/LaunchAgents/com.luxuryprice.gitsync.plist"
LOG_DIR="$PROJECT_DIR/logs"

PYTHON_PATH=$(which python3)
PLIST_TMP="$PLIST_SOURCE.tmp"

mkdir -p "$LOG_DIR"

sed "s|/usr/bin/python3|$PYTHON_PATH|g" "$PLIST_SOURCE" > "$PLIST_TMP"

echo "=========================================="
echo "  GitHub自动同步 - 安装向导"
echo "=========================================="
echo ""
echo "项目目录: $PROJECT_DIR"
echo "Python路径: $PYTHON_PATH"
echo "触发方式: 每次用户登录时（每天仅执行一次）"
echo ""

if [ -f "$PLIST_DEST" ]; then
    echo "检测到已有定时任务，先卸载..."
    launchctl unload "$PLIST_DEST" 2>/dev/null
    rm -f "$PLIST_DEST"
fi

cp "$PLIST_TMP" "$PLIST_DEST"
rm -f "$PLIST_TMP"

launchctl load "$PLIST_DEST"

if [ $? -eq 0 ]; then
    echo ""
    echo "✓ 安装成功！"
    echo ""
    echo "工作原理："
    echo "  - 每次登录电脑时自动触发"
    echo "  - 每天仅执行一次（当天已同步则跳过）"
    echo "  - 有变更才提交推送，无变更直接跳过"
    echo ""
    echo "常用命令："
    echo "  查看状态: launchctl list | grep gitsync"
    echo "  手动执行: launchctl start com.luxuryprice.gitsync"
    echo "  卸载任务: launchctl unload $PLIST_DEST"
    echo "  查看日志: cat $LOG_DIR/auto_git_sync.log"
    echo ""
    echo "注意："
    echo "  - 首次使用请确保Git已配置好GitHub认证"
    echo "  - 日志保存在 logs/ 目录下"
    echo ""
else
    echo "✗ 安装失败，请检查错误信息"
fi