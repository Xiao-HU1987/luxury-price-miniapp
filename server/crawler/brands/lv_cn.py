"""LV 中国官网（CN）适配器：包包类商品 + 门店库存 + 商品价格

- 域名：https://www.louisvuitton.cn
- 区域路径：/zhs-cn/
- 货币：CNY（人民币）
- 抓取目标分类：
    * 女士手袋（Women Handbags）
    * 男士包袋（Men Bags）

注意：
- CN 站域名是 www.louisvuitton.cn（不是 cn.louisvuitton.com）
- 路径前缀是 zhs-cn（不是 chn-cn）
- CN 站反爬较弱，curl 直连即可获取 HTML
- 价格单位为人民币（¥），无需汇率转换
"""
from crawler.brands.base import BrandAdapter


class LVCNAdapter(BrandAdapter):
    """Louis Vuitton 中国官网适配器"""

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
        return "CN"

    @property
    def currency(self) -> str:
        return "CNY"

    @property
    def base_url(self) -> str:
        return "https://www.louisvuitton.cn"

    @property
    def default_category(self) -> str:
        return "handbags"

    # ===== URL 模板 =====

    @property
    def category_urls(self) -> list[str]:
        """所有要抓取的包包类分类页 URL（女士 + 男士）

        注意：CN 站分类页 URL 结构与 JP/KR 类似（亚洲站统一系统），
        亚洲站 N- 参数是统一的分类ID。
        """
        return [
            # 女士 手袋（与JP/KR同N-tfr7qdp分类ID）
            "https://www.louisvuitton.cn/zhs-cn/women/handbags/_/N-tfr7qdp",
            # 男士 包袋 - 全部（与KR同分类ID兜底）
            "https://www.louisvuitton.cn/zhs-cn/men/bags/all-bags/_/N-t1uezqf4",
            "https://www.louisvuitton.cn/zhs-cn/men/bags/_/N-t3rblbv",
            # 常见备用分类：男士信使/双肩/腰包（CN可能不识别N-，但路径是对的）
            "https://www.louisvuitton.cn/zhs-cn/men/bags/messenger-bags/_/N-13jnd34",
            "https://www.louisvuitton.cn/zhs-cn/men/bags/backpacks/_/N-13jnd35",
            "https://www.louisvuitton.cn/zhs-cn/men/bags/cross-body-bags/_/N-13jnd32",
        ]

    @property
    def category_url_template(self) -> str:
        return ""

    @property
    def product_url_template(self) -> str:
        return "https://www.louisvuitton.cn/zhs-cn/products/{slug}"

    @property
    def inventory_api_template(self) -> str:
        """中国门店库存 API 模板（占位，实际根据 network 面板调整）"""
        return "https://api.louisvuitton.cn/api/zhs-cn/catalog/inventory/{sku_id}"

    # ===== DOM 选择器 =====

    @property
    def selectors(self) -> dict[str, str]:
        return {
            "product_list_container": ".lv-product-list",
            "product_item": "a[href*='/zhs-cn/products/']",
            "product_name": "h1",
            # CN站价格结构与JP/KR一致：div.lv-price > span.notranslate
            "product_price": ".lv-price .notranslate, .lv-price",
            "product_image": "picture source[srcset], img[src]",
            "product_sku": "meta[property='product:sku']",
            # 中文"查看更多"
            "load_more_button": "button:has-text('查看更多'), button:has-text('加载更多')",
        }

    # ===== 反爬策略（CN站反爬较弱，可适当加速）=====

    @property
    def batch_size(self) -> int:
        """每批商品数量（CN：20条一批，反爬较弱可加大批次）"""
        return 20

    @property
    def request_interval_range(self) -> tuple[float, float]:
        """请求间隔（CN：3-8秒，国内访问延迟低）"""
        return (3.0, 8.0)

    @property
    def batch_cooldown_range(self) -> tuple[float, float]:
        """批次间冷却（CN：2-4分钟，反爬压力小）"""
        return (120.0, 240.0)

    @property
    def blocked_cooldown(self) -> int:
        return 600  # 10 分钟

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
            'small-leather-goods', 'slg',
            'perfume', 'fragrance', 'cosmetic', 'makeup',
            'lipstick', 'parfum',
        ]

    @property
    def min_price(self) -> float:
        # CNY 最小合理价格（人民币），约 5000 元以上的包包
        return 5_000

    @property
    def max_price(self) -> float:
        return 500_000
