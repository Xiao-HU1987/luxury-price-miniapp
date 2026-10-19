"""品牌适配器基类

每个品牌适配器需要定义：
- 基本信息（品牌 ID、名称、URL 等）
- 分类页和详情页 URL 模板
- DOM 解析选择器
- 反爬策略参数
- 数据验证规则

新增品牌只需继承 BrandAdapter 并实现所有属性/方法。
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Optional


class BrandAdapter(ABC):
    """品牌适配器基类。"""

    # ===== 基本信息（必须由子类定义） =====

    @property
    @abstractmethod
    def brand_id(self) -> str:
        """品牌唯一标识，如 'LV', 'HERMES'"""
        ...

    @property
    @abstractmethod
    def brand_name(self) -> str:
        """品牌英文名，如 'Louis Vuitton'"""
        ...

    @property
    @abstractmethod
    def brand_name_cn(self) -> str:
        """品牌中文名，如 '路易威登'"""
        ...

    @property
    @abstractmethod
    def country(self) -> str:
        """国家代码，如 'JP', 'KR'"""
        ...

    @property
    @abstractmethod
    def currency(self) -> str:
        """货币代码，如 'JPY', 'KRW'"""
        ...

    @property
    @abstractmethod
    def base_url(self) -> str:
        """官网基础 URL"""
        ...

    @property
    @abstractmethod
    def default_category(self) -> str:
        """默认分类 ID"""
        ...

    # ===== URL 模板 =====

    @property
    @abstractmethod
    def category_url_template(self) -> str:
        """分类页 URL 模板，可用 {category} 占位"""
        ...

    @property
    @abstractmethod
    def product_url_template(self) -> str:
        """商品详情页 URL 模板，可用 {slug} 占位"""
        ...

    # ===== DOM 解析选择器 =====

    @property
    @abstractmethod
    def selectors(self) -> dict[str, str]:
        """DOM 选择器映射：
        {
            "product_list_container": "...",
            "product_item": "...",
            "product_name": "...",
            "product_price": "...",
            "product_image": "...",
            "product_sku": "...",
            "load_more_button": "...",
        }
        """
        ...

    # ===== 反爬策略 =====

    @property
    def batch_size(self) -> int:
        """每批爬取商品数量"""
        return 15

    @property
    def request_interval_range(self) -> tuple[float, float]:
        """请求间隔范围（秒）"""
        return (3.0, 8.0)

    @property
    def batch_cooldown_range(self) -> tuple[float, float]:
        """批次冷却范围（秒）"""
        return (180, 300)

    @property
    def blocked_cooldown(self) -> int:
        """被拦截后等待时间（秒）"""
        return 600

    @property
    def max_consecutive_blocks(self) -> int:
        """最大连续拦截次数"""
        return 3

    # ===== 数据过滤 =====

    @property
    def non_product_keywords(self) -> list[str]:
        """非商品类关键词（slug/url 包含则排除）"""
        return []

    @property
    def min_price(self) -> float:
        """最低合理价格"""
        return 100

    @property
    def max_price(self) -> float:
        """最高合理价格"""
        return 100_000_000

    # ===== 辅助方法 =====

    def contains_non_product_keyword(self, text: str) -> Optional[str]:
        """检查文本是否包含非商品关键词。

        返回命中的关键词（便于日志），未命中返回 None。
        采用 "词边界匹配" 避免前缀误匹配：
          - 关键词前后必须是 [^a-z0-9] 字符（空格/-/_/句末/词首）
          - 例：'pet'  不命中 "petit palais"
                'slg'  不命中 "slogan"
        """
        import re
        if not text:
            return None
        text_lc = " " + text.lower() + " "  # 两端包空格，词首/末都能匹配
        for kw in self.non_product_keywords:
            if not kw:
                continue
            kw_lc = kw.lower()
            # 构造正则：前后非 [a-z0-9] 即可，- / _ 也算边界
            pattern = r"(?<![a-z0-9])" + re.escape(kw_lc) + r"(?![a-z0-9])"
            if re.search(pattern, text_lc):
                return kw
        return None

    def is_valid_product(self, article_no: str, name: str, price: float = 0) -> bool:
        """验证商品数据是否合理。"""
        if not article_no or not name:
            return False
        text = f"{article_no} {name}".lower()
        if self.contains_non_product_keyword(text):
            return False
        if price and (price < self.min_price or price > self.max_price):
            return False
        return True

    def get_category_url(self, category: str = "") -> str:
        """获取分类页 URL。"""
        cat = category or self.default_category
        return self.category_url_template.format(category=cat)

    def get_product_url(self, slug: str) -> str:
        """获取商品详情页 URL。"""
        return self.product_url_template.format(slug=slug)