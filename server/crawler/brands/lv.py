"""LV（Louis Vuitton）品牌适配器

实现 LV 日本官网的特定配置和解析逻辑。
新增品牌时可作为参考模板。
"""
from crawler.brands.base import BrandAdapter


class LVAdapter(BrandAdapter):
    """Louis Vuitton 品牌适配器。"""

    # ===== 基本信息 =====

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
        return "JP"

    @property
    def currency(self) -> str:
        return "JPY"

    @property
    def base_url(self) -> str:
        return "https://jp.louisvuitton.com"

    @property
    def default_category(self) -> str:
        return "handbags"

    # ===== URL 模板 =====

    @property
    def category_url_template(self) -> str:
        # 为 category_urls 让路：优先使用 category_urls 列表
        return ""

    @property
    def category_urls(self) -> list[str]:
        """所有要抓取的包包类分类页 URL（女士 + 男士）"""
        return [
            # 女士 手袋（Handbags / Crossbodies / Shoulder bags / Totes 都包含在 N-tfr7qdp 下）
            "https://jp.louisvuitton.com/jpn-jp/women/handbags/_/N-tfr7qdp",
            # 男士 包袋 - 全部（KR同款分类ID N-t1uezqf4 + N-t3rblbv 兜底）
            "https://jp.louisvuitton.com/jpn-jp/men/bags/all-bags/_/N-t1uezqf4",
            "https://jp.louisvuitton.com/jpn-jp/men/bags/_/N-t3rblbv",
        ]

    @property
    def product_url_template(self) -> str:
        return "https://jp.louisvuitton.com/jpn-jp/products/{slug}"

    # ===== DOM 选择器 =====

    @property
    def selectors(self) -> dict[str, str]:
        return {
            "product_list_container": ".lv-product-list",
            "product_item": "a[href*='/jpn-jp/products/']",
            "product_name": "h1",
            "product_price": ".lv-price",
            "product_image": "picture source[srcset], img[src]",
            "product_sku": "meta[property='product:sku']",
            "load_more_button": "button:has-text('さらに表示する')",
        }

    # ===== 反爬策略（真人节奏优化版，2026-08-06 中国联通切换后调参）=====
    # 设计理念：真人浏览LV官网的典型节奏
    #   - 打开详情页 → 看图片/价格 → 滚动看描述 → 找门店库存按钮
    #   → 点开弹窗 → 逐个城市查库存（约2-3分钟/SKU）
    #   → 休息一会再看下一个（避免1分钟内连刷多个商品页）
    # 实测 Akamai 软封禁触发阈值：15分钟内约 8-10 个详情页+库存操作

    @property
    def batch_size(self) -> int:
        """每批次处理 SKU 数：真人一次不会连续看超过4个包"""
        return 4

    @property
    def request_interval_range(self) -> tuple[float, float]:
        """SKU 之间的间隔（秒）：模拟人思考/对比/切页面的时间
        之前 (5,12) 太机械，Akamai 一眼看穿；现在放宽到 20-45 秒"""
        return (20.0, 45.0)

    @property
    def batch_cooldown_range(self) -> tuple[float, float]:
        """批次之间的长休息（秒）：看完4个包，模拟起身倒水/刷手机一会
        之前 (240,360)=4-6分太短；现在 10-18 分基本不会触发风控"""
        return (600.0, 1080.0)

    @property
    def blocked_cooldown(self) -> int:
        """被封禁后的冷却时间（秒）：Akamai 住宅IP封禁通常 30-90 分钟，取 45 分钟保守值"""
        return 2700

    @property
    def max_consecutive_blocks(self) -> int:
        """连续被封次数阈值：连续2次封就进入长冷却，避免死磕"""
        return 2

    # ===== 数据过滤 =====

    @property
    def non_product_keywords(self) -> list[str]:
        return [
            'sunglass', 'sneaker', 'jacket', 'knit-top', 'blanket',
            'card-holder', 'key-pouch', 'babies', 'wallet-on-chain',
            'scarf', 'belt', 'hat', 'glove', 'jewelry', 'watch',
            'ring', 'necklace', 'earring', 'bracelet',
            'shoe', 'sandal', 'boot', 'shirt', 'pant', 'dress',
            'skirt', 'coat', 'swimwear', 'umbrella', 'phone-case',
            'airpods', 'mask', 'pet', 'baby', 'toy', 'book',
            'pen', 'notebook', 'agenda', 'planner',
        ]

    @property
    def min_price(self) -> float:
        return 1000

    @property
    def max_price(self) -> float:
        return 50_000_000