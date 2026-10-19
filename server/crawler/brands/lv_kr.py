"""LV 韩国官网（KR）适配器：包包类商品 + 门店库存 + 商品价格

- 域名：https://kr.louisvuitton.com
- 区域路径：/kor-kr/
- 货币：KRW
- 抓取目标分类：
    * 女士手袋（Women Handbags）: /kor-kr/women/handbags/_/N-tfr7qdp
    * 男士手袋（Men Bags）: /kor-kr/men/bags/_/N-t3rblbv
"""
from crawler.brands.base import BrandAdapter


class LVKRAdapter(BrandAdapter):
    """Louis Vuitton 韩国官网适配器"""

    @property
    def brand_id(self) -> str:
        return "LV"

    @property
    def brand_name(self) -> str:
        return "Louis Vuitton"

    @property
    def brand_name_cn(self) -> str:
        return "路易威登"

    @property
    def country(self) -> str:
        return "KR"

    @property
    def currency(self) -> str:
        return "KRW"

    @property
    def base_url(self) -> str:
        return "https://kr.louisvuitton.com"

    @property
    def default_category(self) -> str:
        return "handbags"

    # ===== URL 模板 =====

    @property
    def category_urls(self) -> list[str]:
        """所有要抓取的包包类分类页 URL（女士 + 男士）"""
        return [
            # 女士 手袋（Handbags / Crossbodies / Shoulder bags / Totes 都包含在 N-tfr7qdp 下）
            "https://kr.louisvuitton.com/kor-kr/women/handbags/_/N-tfr7qdp",
            # 男士 包袋 - 全部
            "https://kr.louisvuitton.com/kor-kr/men/bags/all-bags/_/N-t1uezqf4",
        ]

    @property
    def category_url_template(self) -> str:
        # 留空，使用 category_urls 列表
        return ""

    @property
    def product_url_template(self) -> str:
        return "https://kr.louisvuitton.com/kor-kr/products/{slug}"

    @property
    def inventory_api_template(self) -> str:
        """韩国门店库存 API 模板（占位，实际根据 network 面板调整）"""
        return "https://api.louisvuitton.com/api/kor-kr/catalog/inventory/{sku_id}"

    # ===== DOM 选择器 =====

    @property
    def selectors(self) -> dict[str, str]:
        return {
            "product_list_container": ".lv-product-list",
            "product_item": "a[href*='/kor-kr/products/']",
            "product_name": "h1",
            "product_price": ".lv-price",
            "product_image": "picture source[srcset], img[src]",
            "product_sku": "meta[property='product:sku']",
            # 韩文“查看更多”
            "load_more_button": "button:has-text('더 보기'), button:has-text('더보기')",
        }

    # ===== 反爬策略（韩国LV Akamai更严苛，与JP完全独立）=====

    @property
    def batch_size(self) -> int:
        """每批商品数量（KR：15条一批，与JP持平）"""
        return 15

    @property
    def request_interval_range(self) -> tuple[float, float]:
        """请求间隔（KR：4-10秒，仍属正常浏览行为）"""
        return (4.0, 10.0)

    @property
    def batch_cooldown_range(self) -> tuple[float, float]:
        """批次间冷却（KR：3-5分钟，本轮未触发反爬可适度收紧）"""
        return (180.0, 300.0)

    @property
    def blocked_cooldown(self) -> int:
        return 900  # 15 分钟

    @property
    def max_consecutive_blocks(self) -> int:
        return 3

    # ===== 数据过滤：只保留包包 =====

    @property
    def non_product_keywords(self) -> list[str]:
        """非包包类关键词，URL 或 slug 包含则排除。"""
        return [
            'sunglass', 'sneaker', 'jacket', 'knit-top', 'blanket',
            'card-holder', 'key-pouch', 'babies', 'scarf', 'belt',
            'hat', 'glove', 'jewelry', 'watch', 'ring', 'necklace',
            'earring', 'bracelet', 'shoe', 'sandal', 'boot', 'shirt',
            'pant', 'dress', 'skirt', 'coat', 'swimwear', 'umbrella',
            'phone-case', 'airpods', 'mask', 'pet', 'baby', 'toy',
            'book', 'pen', 'notebook', 'agenda', 'planner',
            'wallet', 'brazza', 'zippy', 'slender',
            # 保留 wallet-on-chain ？ 排除非包包
            'small-leather-goods', 'slg',
            'perfume', 'fragrance', 'cosmetic', 'makeup',
            'lipstick', 'parfum',
        ]

    @property
    def min_price(self) -> float:
        # KRW 最小合理价格（韩元，不含税），约 50 万韩元以上的包包
        return 500_000

    @property
    def max_price(self) -> float:
        return 200_000_000
