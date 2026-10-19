"""爬虫健康度检查与告警模块

功能：
1. 数据完整性校验 — 检查抓取结果关键字段是否缺失
2. 页面结构检测 — 验证关键 DOM 选择器是否仍然有效
3. 告警通知 — 检测到异常时通过配置的渠道通知

设计原则：
- 不影响正常抓取流程（检查失败只记录，不中断）
- 可配置告警渠道（目前支持日志 + 控制台，后续可扩展邮件/飞书等）
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger("lv_crawler.health")


# ==================== 健康检查结果 ====================

@dataclass
class HealthCheckResult:
    """单次健康检查结果。"""
    name: str
    passed: bool
    message: str = ""
    severity: str = "warning"  # info / warning / error / critical

    def __post_init__(self):
        if self.severity not in ("info", "warning", "error", "critical"):
            self.severity = "warning"


@dataclass
class CrawlHealthReport:
    """完整抓取的健康报告。"""
    checks: List[HealthCheckResult] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)

    def add(self, check: HealthCheckResult):
        self.checks.append(check)
        if not check.passed:
            level = check.severity
            msg = f"[健康检查-{level.upper()}] {check.name}: {check.message}"
            if level in ("error", "critical"):
                logger.error(msg)
                self.errors.append(msg)
            elif level == "warning":
                logger.warning(msg)
            else:
                logger.info(msg)

    @property
    def has_critical_issues(self) -> bool:
        return any(c.severity == "critical" and not c.passed for c in self.checks)

    @property
    def has_errors(self) -> bool:
        return any(c.severity in ("error", "critical") and not c.passed for c in self.checks)

    def summary(self) -> str:
        total = len(self.checks)
        passed = sum(1 for c in self.checks if c.passed)
        failed = total - passed
        return f"健康检查: {passed}/{total} 通过, {failed} 失败"


# ==================== 数据完整性校验 ====================

DETAIL_REQUIRED_FIELDS = (
    "name",
    "article_no",
    "price",
)

INVENTORY_REQUIRED_FIELDS = (
    "store_name",
    "in_stock",
)


def validate_detail(detail: Dict[str, Any]) -> List[HealthCheckResult]:
    """校验商品详情数据完整性。"""
    results: List[HealthCheckResult] = []

    for field in DETAIL_REQUIRED_FIELDS:
        value = detail.get(field)
        if value is None or value == "":
            results.append(HealthCheckResult(
                name=f"详情字段-{field}",
                passed=False,
                message=f"商品 {detail.get('article_no', 'unknown')} 缺少字段 {field}",
                severity="error",
            ))
        else:
            results.append(HealthCheckResult(
                name=f"详情字段-{field}",
                passed=True,
                severity="info",
            ))

    # 价格合理性检查
    price = detail.get("price")
    if price is not None:
        try:
            p = float(price)
            if p <= 0 or p > 10000000:  # LV 手袋一般在 10万-100万日元区间
                results.append(HealthCheckResult(
                    name="价格合理性",
                    passed=False,
                    message=f"价格 {p} 不在合理范围内（1-10,000,000 日元）",
                    severity="warning",
                ))
            else:
                results.append(HealthCheckResult(
                    name="价格合理性",
                    passed=True,
                    severity="info",
                ))
        except (TypeError, ValueError):
            results.append(HealthCheckResult(
                name="价格格式",
                passed=False,
                message=f"价格 {price} 不是有效数字",
                severity="error",
            ))

    # 图片数量检查
    images = detail.get("images", [])
    if isinstance(images, list) and len(images) < 2:
        results.append(HealthCheckResult(
            name="图片数量",
            passed=False,
            message=f"图片数量偏少: {len(images)} 张",
            severity="warning",
        ))
    else:
        results.append(HealthCheckResult(
            name="图片数量",
            passed=True,
            severity="info",
        ))

    return results


def validate_inventories(inventories: List[Dict[str, Any]],
                          min_expected: int = 10) -> List[HealthCheckResult]:
    """校验库存数据完整性。"""
    results: List[HealthCheckResult] = []

    # 数量检查
    if len(inventories) < min_expected:
        results.append(HealthCheckResult(
            name="库存数量",
            passed=False,
            message=f"库存记录数过少: {len(inventories)} 条（预期至少 {min_expected} 条）",
            severity="warning",
        ))
    else:
        results.append(HealthCheckResult(
            name="库存数量",
            passed=True,
            severity="info",
        ))

    # 关键字段检查
    for i, inv in enumerate(inventories[:5]):  # 抽样检查前 5 条
        for field in INVENTORY_REQUIRED_FIELDS:
            value = inv.get(field)
            if value is None or (isinstance(value, str) and value == ""):
                results.append(HealthCheckResult(
                    name=f"库存字段-{field}-#{i}",
                    passed=False,
                    message=f"库存记录 #{i} 缺少字段 {field}",
                    severity="warning",
                ))

    # 日本门店占比检查
    japan_count = sum(
        1 for inv in inventories
        if any(k in inv.get("store_address", "") for k in ['県', '都', '道', '府'])
    )
    if inventories and japan_count / len(inventories) < 0.5:
        results.append(HealthCheckResult(
            name="日本门店占比",
            passed=False,
            message=f"日本门店占比过低: {japan_count}/{len(inventories)}",
            severity="warning",
        ))

    return results


# ==================== 页面结构检测 ====================

# 关键 DOM 选择器 — 如果这些选择器找不到元素，说明页面结构可能变了
CRITICAL_SELECTORS = {
    "商品标题": "h1",
    "价格元素": ".lv-price",
    "库存折叠面板": ".lv-expandable-panel",
    "库存按钮": ".lv-product-locate-in-store__container",
    "库存弹窗第一步": ".lv-locate-in-store__first-step-modal",
    "库存弹窗第二步": ".lv-locate-in-store__second-step-modal",
    "门店卡片": ".lv-store-card-detailed",
    "门店名称": ".lv-store-card-detailed__name",
}


async def check_page_structure(page, selectors: Optional[Dict[str, str]] = None) -> List[HealthCheckResult]:
    """检查页面关键 DOM 结构是否正常。

    用于检测 LV 官网是否改版，导致选择器失效。
    """
    if selectors is None:
        selectors = CRITICAL_SELECTORS

    results: List[HealthCheckResult] = []

    for name, selector in selectors.items():
        try:
            count = await page.evaluate(f'''
                (sel) => document.querySelectorAll(sel).length
            ''', selector)
            if count == 0:
                results.append(HealthCheckResult(
                    name=f"DOM选择器-{name}",
                    passed=False,
                    message=f"选择器 '{selector}' 未找到任何元素，页面可能已改版",
                    severity="error",
                ))
            else:
                results.append(HealthCheckResult(
                    name=f"DOM选择器-{name}",
                    passed=True,
                    severity="info",
                ))
        except Exception as e:
            results.append(HealthCheckResult(
                name=f"DOM选择器-{name}",
                passed=False,
                message=f"检查选择器时出错: {e}",
                severity="warning",
            ))

    return results


# ==================== 告警 ====================

def send_alert(message: str, level: str = "warning",
               channel: str = "log") -> None:
    """发送告警。

    目前仅支持日志输出，后续可扩展：
    - 飞书/钉钉/企业微信 webhook
    - 邮件
    - Server 酱
    """
    if channel == "log":
        msg = f"[告警-{level.upper()}] {message}"
        if level in ("error", "critical"):
            logger.error(msg)
        else:
            logger.warning(msg)
    else:
        logger.warning("未知告警渠道: %s，回退到日志", channel)


# ==================== 写入前数据验证 ====================

# 商品名称中不允许出现的无意义关键词
_INVALID_NAME_KEYWORDS = [
    "メインコンテンツ", "ウィッシュリスト", "ショッピングバッグ",
    "ヘルプ", "メニュー", "検索", "すべて", "ホーム",
    "アクセス拒否", "access denied", "error", "エラー",
]

# 合理价格范围（日元）
_MIN_PRICE_JPY = 1000      # 最低 1000 日元
_MAX_PRICE_JPY = 50_000_000  # 最高 5000 万日元


def validate_detail_before_write(detail: Dict[str, Any]) -> List[HealthCheckResult]:
    """写入前验证商品数据质量，返回验证结果列表。

    用于在 persist_detail 之前过滤掉明显无效的数据。
    """
    results: List[HealthCheckResult] = []

    name = (detail.get("name") or "").strip()
    article_no = (detail.get("article_no") or "").strip()
    price = detail.get("price")
    images = detail.get("images") or []

    # 1. 名称验证
    if not name:
        results.append(HealthCheckResult(
            name="商品名称",
            passed=False,
            message="商品名称为空",
            severity="error",
        ))
    elif len(name) < 2:
        results.append(HealthCheckResult(
            name="商品名称",
            passed=False,
            message=f"商品名称过短: '{name}'",
            severity="error",
        ))
    elif len(name) > 200:
        results.append(HealthCheckResult(
            name="商品名称",
            passed=False,
            message=f"商品名称过长 ({len(name)} 字符)，可能是误抓",
            severity="warning",
        ))
    elif any(kw.lower() in name.lower() for kw in _INVALID_NAME_KEYWORDS):
        results.append(HealthCheckResult(
            name="商品名称",
            passed=False,
            message=f"商品名称含无效关键词: '{name}'",
            severity="error",
        ))
    else:
        results.append(HealthCheckResult(
            name="商品名称",
            passed=True,
            severity="info",
        ))

    # 2. 货号验证
    if not article_no:
        results.append(HealthCheckResult(
            name="商品货号",
            passed=False,
            message="商品货号为空，可能无法唯一标识",
            severity="warning",
        ))
    elif len(article_no) < 3:
        results.append(HealthCheckResult(
            name="商品货号",
            passed=False,
            message=f"商品货号过短: '{article_no}'",
            severity="warning",
        ))
    else:
        results.append(HealthCheckResult(
            name="商品货号",
            passed=True,
            severity="info",
        ))

    # 3. 价格验证
    if price is not None:
        try:
            p = float(price)
            if p <= 0:
                results.append(HealthCheckResult(
                    name="价格",
                    passed=False,
                    message=f"价格为零或负数: {p}",
                    severity="error",
                ))
            elif p < _MIN_PRICE_JPY:
                results.append(HealthCheckResult(
                    name="价格",
                    passed=False,
                    message=f"价格过低: {p} 日元（最低 {_MIN_PRICE_JPY}）",
                    severity="warning",
                ))
            elif p > _MAX_PRICE_JPY:
                results.append(HealthCheckResult(
                    name="价格",
                    passed=False,
                    message=f"价格过高: {p} 日元（最高 {_MAX_PRICE_JPY}）",
                    severity="warning",
                ))
            else:
                results.append(HealthCheckResult(
                    name="价格",
                    passed=True,
                    severity="info",
                ))
        except (TypeError, ValueError):
            results.append(HealthCheckResult(
                name="价格",
                passed=False,
                message=f"价格格式无效: {price}",
                severity="error",
            ))
    else:
        results.append(HealthCheckResult(
            name="价格",
            passed=False,
            message="价格缺失（列表页常见，详情页应修复）",
            severity="warning",
        ))

    # 4. 图片数量验证
    if not images:
        results.append(HealthCheckResult(
            name="商品图片",
            passed=False,
            message="无商品图片",
            severity="warning",
        ))
    elif len(images) < 2:
        results.append(HealthCheckResult(
            name="商品图片",
            passed=False,
            message=f"图片数量偏少: {len(images)} 张",
            severity="warning",
        ))
    else:
        results.append(HealthCheckResult(
            name="商品图片",
            passed=True,
            severity="info",
        ))

    return results


def is_valid_detail_for_write(detail: Dict[str, Any]) -> bool:
    """快速判断商品详情是否适合写入数据库（无严重错误）。"""
    results = validate_detail_before_write(detail)
    critical_errors = [r for r in results if not r.passed and r.severity == "error"]
    if critical_errors:
        for err in critical_errors:
            logger.error("❌ 数据验证失败: %s - %s", err.name, err.message)
        return False
    warnings = [r for r in results if not r.passed and r.severity == "warning"]
    for warn in warnings:
        logger.warning("⚠️  数据警告: %s - %s", warn.name, warn.message)
    return True
