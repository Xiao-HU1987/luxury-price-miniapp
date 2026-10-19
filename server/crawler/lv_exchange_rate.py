"""LV 实时汇率获取与存储脚本

从公开汇率API获取 JPY/CNY、KRW/CNY 汇率，写入 exchange_rates 表。
支持失败回退默认值，用于对齐脚本动态换算外币价格。

数据源优先级：
1. https://open.er-api.com/v6/latest/CNY （免费、无需key、有CORS）
2. https://api.exchangerate-api.com/v4/latest/CNY （备用）
3. 缓存/默认值兜底

用法：
    python3 -m crawler.lv_exchange_rate   # 获取并写入数据库
    python3 -m crawler.lv_exchange_rate --dry-run  # 仅打印不写入
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

import logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("lv_exchange_rate")

# 默认兜底汇率（2026年8月参考值）
DEFAULT_RATES = {
    "JPY": 0.048,   # 1 JPY = ? CNY
    "KRW": 0.0053,  # 1 KRW = ? CNY
    "USD": 7.25,    # 1 USD = ? CNY  通用
}

# API 源
API_SOURCES = [
    {
        "name": "exchangerate-api",
        "url": "https://api.exchangerate-api.com/v4/latest/CNY",
        "extract": lambda data: {
            "JPY": 1.0 / data["rates"].get("JPY", 0),
            "KRW": 1.0 / data["rates"].get("KRW", 0),
            "USD": 1.0 / data["rates"].get("USD", 0),
        } if data.get("rates") else {},
    },
]


def _fetch_url(url: str, timeout: int = 15) -> Optional[Dict[str, Any]]:
    """用 requests/urllib3 发请求，失败返回 None"""
    try:
        import urllib.request
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            "Accept": "application/json",
        })
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            if resp.status == 200:
                return json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        logger.warning("请求 %s 失败: %s", url, e)
    return None


def fetch_latest_rates() -> Dict[str, Any]:
    """获取最新汇率，包含 source 和 update_time"""
    rates: Dict[str, float] = {}
    source = ""

    for src in API_SOURCES:
        data = _fetch_url(src["url"])
        if data:
            try:
                extracted = src["extract"](data)
                if all(k in extracted and extracted[k] > 0 for k in ("JPY", "KRW")):
                    rates = extracted
                    source = src["name"]
                    logger.info("从 %s 获取汇率成功: JPY=%f, KRW=%f",
                                source, rates["JPY"], rates["KRW"])
                    break
            except Exception as e:
                logger.warning("解析 %s 失败: %s", src["name"], e)

    if not rates:
        logger.warning("所有API均失败，使用默认兜底汇率")
        rates = DEFAULT_RATES.copy()
        source = "default/fallback"

    return {
        "base": "CNY",
        "rates": rates,
        "source": source,
        "update_time": datetime.now(timezone.utc).isoformat(),
    }


def save_to_database(rates_data: Dict[str, Any]) -> bool:
    """写入 exchange_rates 表"""
    try:
        from database import SessionLocal, engine
        from models import ExchangeRate

        # 先建表（不存在时）
        from database import Base
        from models.exchange import ExchangeRate as _  # noqa: F401 - 确保表注册
        Base.metadata.create_all(bind=engine)

        db = SessionLocal()
        try:
            record = ExchangeRate(
                base=rates_data["base"],
                rates=rates_data["rates"],
            )
            db.add(record)
            db.commit()
            db.refresh(record)
            logger.info("汇率写入数据库成功 id=%d, rates=%s", record.id, record.rates)
            return True
        finally:
            db.close()
    except Exception as e:
        logger.error("写入数据库失败: %s", e)
        return False


def get_latest_from_db() -> Optional[Dict[str, Any]]:
    """从数据库读取最新汇率"""
    try:
        from database import SessionLocal
        from models import ExchangeRate

        db = SessionLocal()
        try:
            latest = db.query(ExchangeRate).order_by(ExchangeRate.update_time.desc()).first()
            if latest:
                return {
                    "id": latest.id,
                    "base": latest.base,
                    "rates": latest.rates,
                    "update_time": latest.update_time.isoformat() if latest.update_time else None,
                }
        finally:
            db.close()
    except Exception as e:
        logger.warning("读取数据库汇率失败: %s", e)
    return None


def convert(amount: float, from_currency: str, rates: Dict[str, float]) -> float:
    """
    按 CNY 为基准的 rates 表换算。
    rates[k] = 1 k = ? CNY，所以 amount*rates[from_cur] = CNY
    """
    from_currency = from_currency.upper()
    rate = rates.get(from_currency)
    if rate is None or rate <= 0:
        return 0.0
    return round(amount * rate, 2)


def main():
    parser = argparse.ArgumentParser(description="LV 汇率获取与存储")
    parser.add_argument("--dry-run", action="store_true", help="仅获取并打印，不写入")
    parser.add_argument("--force", action="store_true", help="即使数据库有今日数据也强制刷新")
    args = parser.parse_args()

    # 先查数据库已有值
    db_rates = get_latest_from_db()
    need_fetch = args.force or not db_rates

    if db_rates and not need_fetch:
        # 检查是否是今日更新
        today = datetime.now(timezone.utc).date()
        if db_rates["update_time"]:
            try:
                upd_date = datetime.fromisoformat(db_rates["update_time"]).date()
                if upd_date != today:
                    need_fetch = True
                    logger.info("数据库汇率非今日(%s)，需要刷新", upd_date)
            except Exception:
                need_fetch = True

    if need_fetch:
        logger.info("获取最新汇率...")
        rates_data = fetch_latest_rates()
    else:
        rates_data = db_rates
        logger.info("使用数据库已缓存汇率 (id=%s, update=%s)",
                    db_rates.get("id"), db_rates.get("update_time"))

    print(f"\n{'='*60}")
    print(f"  当前汇率（基准 CNY）")
    print(f"{'='*60}")
    for cur in ["JPY", "KRW", "USD"]:
        rate = rates_data["rates"].get(cur, 0)
        print(f"  1 {cur} = {rate:.6f} CNY  ({1/rate:.2f} {cur}/CNY)" if rate > 0 else f"  {cur}: N/A")
    print(f"  Source: {rates_data.get('source', 'db')}")
    print(f"  Update: {rates_data.get('update_time', 'N/A')}")

    if not args.dry_run and need_fetch:
        ok = save_to_database(rates_data)
        if ok:
            print(f"\n✅ 汇率已写入 exchange_rates 表")
        else:
            print(f"\n❌ 写入数据库失败（打印值仍可用）")


if __name__ == "__main__":
    main()
