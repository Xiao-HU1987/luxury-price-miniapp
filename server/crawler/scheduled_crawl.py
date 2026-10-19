"""LV 定时爬虫运行脚本

功能：
    定时执行 LV 日本官网数据采集任务。运行前自动执行健康检查
    （CDP 连接、Chrome 状态、数据库连接），通过后调用 lv_crawler.run()
    进行全量抓取（mode='all', fetch_store_inventory=True），并记录每次
    运行的统计信息与异常告警。

使用说明：
    在 server/ 目录下运行（需先激活 venv）：

    # 只运行一次（执行完退出，异常以非零码退出）
    venv/bin/python3.11 -m crawler.scheduled_crawl --once

    # 每 24 小时运行一次（默认间隔，循环执行）
    venv/bin/python3.11 -m crawler.scheduled_crawl --interval 24

    # 只做健康检查，不实际抓取
    venv/bin/python3.11 -m crawler.scheduled_crawl --dry-run

    # 组合：只做一次健康检查
    venv/bin/python3.11 -m crawler.scheduled_crawl --once --dry-run

前置条件：
    1. Chrome 已以调试模式启动并访问过 LV 完成验证：
       "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \\
           --remote-debugging-port=9333 --user-data-dir=/tmp/chrome-crawl
    2. 数据库已初始化
    3. server/venv 虚拟环境可用，playwright 已安装

日志：
    所有运行记录写入 crawler/crawl_history.log

注意：
    - 脚本使用 caffeinate -i 防止 Mac 休眠，退出时自动释放。
    - 代理环境变量（http_proxy 等）在启动时被清空，与 lv_crawler.py 一致。
    - 任何异常都不会导致脚本崩溃退出（除非是 --once 模式）。
"""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import sched
import sys
import time
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import urlparse

# ==================== 代理环境变量清空 ====================
# 关键：清空代理环境变量，避免 CDP 连接（127.0.0.1:9333）被系统代理拦截
# 与 lv_crawler.py 保持一致
for _proxy_var in ("http_proxy", "https_proxy", "HTTP_PROXY", "HTTPS_PROXY",
                    "all_proxy", "ALL_PROXY"):
    os.environ.pop(_proxy_var, None)

# ==================== 路径设置 ====================
# 把 server/ 加入 import 路径（使得 crawler/database 可以作为包被引用）
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

# ==================== 日志配置 ====================
# 在导入 lv_crawler 之前配置根日志器，使其 basicConfig 不再生效
LOG_FILE = Path(__file__).resolve().parent / "crawl_history.log"

_root_logger = logging.getLogger()
_root_logger.setLevel(logging.INFO)
if not _root_logger.handlers:
    _file_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
    _file_handler.setFormatter(
        logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
    )
    _root_logger.addHandler(_file_handler)
    _console_handler = logging.StreamHandler()
    _console_handler.setFormatter(logging.Formatter("%(message)s"))
    _root_logger.addHandler(_console_handler)

logger = logging.getLogger("scheduled_crawl")

# ==================== 项目模块导入 ====================
from crawler import config as crawler_config  # noqa: E402
from crawler import lv_crawler  # noqa: E402

# ==================== 常量 ====================
CDP_ENDPOINT = crawler_config.CDP_ENDPOINT
CDP_PORT = urlparse(CDP_ENDPOINT).port or 9333
CHROME_EXECUTABLE = crawler_config.CHROME_EXECUTABLE
CHROME_START_CMD = (
    f'"{CHROME_EXECUTABLE}" --remote-debugging-port=9333 '
    f'--user-data-dir=/tmp/chrome-crawl'
)


# ==================== 工具函数 ====================

def _now() -> str:
    """当前时间字符串。"""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _format_elapsed(seconds: float) -> str:
    """把秒数格式化为 '8分32秒' / '45秒'。"""
    total = int(seconds)
    minutes, secs = divmod(total, 60)
    if minutes > 0:
        return f"{minutes}分{secs}秒"
    return f"{secs}秒"


def _start_caffeinate() -> None:
    """启动 caffeinate -i 防止 Mac 休眠。

    使用 -w <pid> 让 caffeinate 在本脚本退出时自动结束。
    """
    try:
        os.system("caffeinate -i -w %d &" % os.getpid())
        logger.info("☕ 已启动 caffeinate -i 防止系统休眠 (PID=%d)", os.getpid())
    except Exception as e:
        logger.warning("启动 caffeinate 失败: %s", e)


# ==================== 健康检查 ====================

def _check_cdp() -> tuple[bool, str]:
    """检查 CDP 端口是否可连接、Chrome 是否响应调试协议。"""
    try:
        resp = urllib.request.urlopen(
            CDP_ENDPOINT + "/json/version", timeout=5
        )
        data = json.loads(resp.read())
        browser = data.get("Browser", "unknown")
        logger.info("  CDP 浏览器版本: %s", str(browser)[:50])
        return True, ""
    except Exception:
        return False, f"CDP连接失败 - Chrome未启动或端口{CDP_PORT}未监听"


def _check_chrome_process() -> tuple[bool, str]:
    """检查 Chrome 进程是否在运行。"""
    try:
        ret = os.system("pgrep -f 'Google Chrome' > /dev/null 2>&1")
        if ret == 0:
            return True, ""
        return False, "Chrome 进程未运行"
    except Exception as e:
        # pgrep 不可用时降级为不阻塞
        logger.debug("pgrep 检查失败，跳过: %s", e)
        return True, ""


def _check_database() -> tuple[bool, str]:
    """检查数据库连接是否正常。"""
    try:
        from database import engine
        from sqlalchemy import text
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True, ""
    except Exception as e:
        return False, f"数据库连接失败: {e}"


def health_check() -> tuple[bool, str]:
    """执行完整健康检查（CDP、Chrome、数据库）。

    Returns:
        (all_ok, failure_reason) — all_ok 为 True 时 failure_reason 为空字符串。
    """
    try:
        # 1. CDP 连接（最关键）
        ok, reason = _check_cdp()
        if not ok:
            return False, reason

        # 2. Chrome 进程状态
        ok, reason = _check_chrome_process()
        if not ok:
            return False, reason

        # 3. 数据库连接
        ok, reason = _check_database()
        if not ok:
            return False, reason

        return True, ""
    except Exception as e:
        return False, f"健康检查异常: {e}"


def _print_health_alert(reason: str) -> None:
    """打印健康检查失败的告警信息。"""
    logger.info("⚠️ 告警: %s", reason)
    # CDP 或 Chrome 相关故障，给出启动命令
    if "CDP" in reason or "Chrome" in reason:
        logger.info("请执行以下命令启动Chrome:")
        logger.info("  %s", CHROME_START_CMD)


# ==================== 爬虫任务执行 ====================

def run_task(dry_run: bool = False, once: bool = False) -> int:
    """执行一次完整的爬虫任务（健康检查 + 抓取 + 统计）。

    Args:
        dry_run: 只做健康检查，不实际抓取。
        once: 是否为 --once 模式（异常会重新抛出以非零码退出）。

    Returns:
        0 表示成功，非 0 表示失败。
    """
    start_time = time.time()
    start_str = _now()

    logger.info("=" * 40)
    logger.info("[%s] 开始定时爬虫任务", start_str)
    logger.info("=" * 40)

    # ===== 步骤1: 健康检查 =====
    ok, reason = health_check()
    if ok:
        logger.info("步骤1: 健康检查... ✅")
    else:
        logger.info("步骤1: 健康检查... ❌")
        _print_health_alert(reason)
        logger.info("=" * 40)
        return 1

    # ===== --dry-run：只做健康检查 =====
    if dry_run:
        logger.info("步骤2: 跳过抓取（--dry-run 模式，仅健康检查）")
        logger.info("步骤3: 结果统计... ✅")
        logger.info("=" * 40)
        logger.info("[%s] 健康检查任务完成", _now())
        logger.info("=" * 40)
        return 0

    # ===== 步骤2: 启动爬虫 =====
    logger.info("步骤2: 启动爬虫...")
    try:
        summary = asyncio.run(lv_crawler.run(
            mode="all",
            dry_run=False,
            fetch_store_inventory=True,
        ))
    except Exception as e:
        elapsed = time.time() - start_time
        logger.info("步骤2: 爬虫执行失败 ❌")
        logger.info("⚠️ 告警: 爬虫执行异常 - %s", e)
        logger.info("告警时间: %s", _now())
        logger.info("=" * 40)
        logger.info("[%s] 爬虫任务失败 (耗时 %s)", _now(), _format_elapsed(elapsed))
        logger.info("=" * 40)
        if once:
            raise
        return 1

    # ===== 结果统计 =====
    elapsed = time.time() - start_time
    listings = summary.get("listings", 0)
    details = summary.get("details", 0)
    inventories = summary.get("inventories", 0)
    errors = summary.get("errors", 0)

    logger.info("  - 商品列表: %d个", listings)
    logger.info("  - 详情抓取: %d/%d 成功", details, listings)
    logger.info("  - 库存记录: %d条", inventories)
    if errors > 0:
        logger.info("  - 失败数: %d", errors)
    logger.info("  - 耗时: %s", _format_elapsed(elapsed))

    # ===== 步骤3: 结果统计 =====
    if errors == 0:
        logger.info("步骤3: 结果统计... ✅")
    else:
        logger.info("步骤3: 结果统计... ⚠️ (有 %d 个错误)", errors)

    logger.info("=" * 40)
    logger.info("[%s] 爬虫任务完成", _now())
    logger.info("=" * 40)

    return 0 if errors == 0 else 1


# ==================== 定时调度 ====================

def run_scheduled(dry_run: bool, interval_seconds: float) -> None:
    """使用 sched 调度循环执行的爬虫任务。

    任何异常都不会导致脚本崩溃（try/except 包裹），失败后会继续安排下次运行。
    """
    scheduler = sched.scheduler(time.time, time.sleep)

    def _scheduled_run() -> None:
        try:
            run_task(dry_run=dry_run, once=False)
        except Exception as e:
            logger.info("⚠️ 告警: 爬虫任务异常退出 - %s", e)
            logger.info("告警时间: %s", _now())
        # 安排下一次运行
        next_time = datetime.now() + timedelta(seconds=interval_seconds)
        logger.info("⏰ 下次运行: %s", next_time.strftime("%Y-%m-%d %H:%M:%S"))
        scheduler.enter(interval_seconds, 1, _scheduled_run)

    # 立即执行第一次
    scheduler.enter(0, 1, _scheduled_run)
    try:
        scheduler.run()
    except KeyboardInterrupt:
        logger.info("收到中断信号 (Ctrl+C)，正在退出...")


# ==================== 命令行入口 ====================

def main() -> int:
    parser = argparse.ArgumentParser(
        description="LV 定时爬虫运行脚本",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=24,
        help="运行间隔（小时），默认 24。仅在非 --once 模式下生效。",
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="只运行一次后退出（异常会以非零码退出）。",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="只做健康检查，不实际抓取。",
    )
    args = parser.parse_args()

    # 启动 caffeinate 防休眠
    _start_caffeinate()

    if args.once:
        # --once 模式：只运行一次
        logger.info("📍 运行模式: --once (单次执行)")
        return run_task(dry_run=args.dry_run, once=True)

    # --interval 模式：循环执行
    interval_seconds = args.interval * 3600.0
    logger.info("🔁 运行模式: --interval (每 %.1f 小时)", args.interval)
    if args.dry_run:
        logger.info("📍 --dry-run 已启用: 仅健康检查，不抓取")
    run_scheduled(dry_run=args.dry_run, interval_seconds=interval_seconds)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
