"""LV 欧洲多国家官网适配器

LV 欧洲官网体系：
  * 所有欧洲国家使用统一域名 https://eu.louisvuitton.com
  * 切换国家通过 URL 中的 locale 路径，例如：
      - 法国 FR-FRA 法语/欧元: /eng-fr/women/handbags/_/N-tfr7qdp
      - 英国 UK-GBP 英语/英镑: /eng-gb/women/handbags/_/N-tfr7qdp
      - 德国 DE-EUR 德语/欧元: /eng-de/women/handbags/_/N-tfr7qdp
      - 意大利 IT-EUR 意语/欧元: /eng-it/women/handbags/_/N-tfr7qdp
      - 西班牙 ES-EUR 西语/欧元: /eng-es/women/handbags/_/N-tfr7qdp
      - 瑞士 CH-CHF 法语/瑞士法郎: /fra-ch/women/handbags/_/N-tfr7qdp

典型的 LV 欧洲价格策略：
  * 欧元区（FR/DE/IT/ES）价格相同 → 只爬 1 个欧元区国家即可，推荐 FR
  * 英国（GBP 英镑）单独价格 + 退税优势 → 必爬
  * 瑞士（CHF 瑞士法郎）单独价格，退税后常有优势 → 推荐爬
  * 丹麦（DKK 丹麦克朗）北欧价较高 → 可选
  * 瑞典（SEK 瑞典克朗）→ 可选

建议默认爬取国家（由用户确认）：
  ✅ 法国 FR (EUR) — 欧元区基准价
  ✅ 英国 GB (GBP) — 英镑区 / 退税
  ✅ 瑞士 CH (CHF) — 瑞士法郎 / 退税

用户可根据需要在 CLI 用 --country FR|GB|CH 选择。
"""
from crawler.brands.base import BrandAdapter


# 欧洲各国配置表
EU_COUNTRIES: dict[str, dict] = {
    "FR": {
        "name_cn": "法国",
        "currency": "EUR",
        "locale": "fra-fr",          # 法语/法国
        "locale_alt": "eng-fr",       # 英语/法国（兜底，便于解析）
        "store_name_suffix": "法国官网",
        "city_default": "巴黎",
    },
    "GB": {
        "name_cn": "英国",
        "currency": "GBP",
        "locale": "eng-gb",
        "locale_alt": "eng-gb",
        "store_name_suffix": "英国官网",
        "city_default": "伦敦",
    },
    "CH": {
        "name_cn": "瑞士",
        "currency": "CHF",
        "locale": "fra-ch",          # 法语区/瑞士（瑞士多语种，法语接口返回更稳定）
        "locale_alt": "eng-ch",
        "store_name_suffix": "瑞士官网",
        "city_default": "日内瓦",
    },
    "DE": {
        "name_cn": "德国",
        "currency": "EUR",
        "locale": "deu-de",
        "locale_alt": "eng-de",
        "store_name_suffix": "德国官网",
        "city_default": "慕尼黑",
    },
    "IT": {
        "name_cn": "意大利",
        "currency": "EUR",
        "locale": "ita-it",
        "locale_alt": "eng-it",
        "store_name_suffix": "意大利官网",
        "city_default": "米兰",
    },
    "ES": {
        "name_cn": "西班牙",
        "currency": "EUR",
        "locale": "spa-es",
        "locale_alt": "eng-es",
        "store_name_suffix": "西班牙官网",
        "city_default": "马德里",
    },
}


class LVEUAdapter(BrandAdapter):
    """Louis Vuitton 欧洲多国家适配器（工厂化：通过构造函数传入 country code）。"""

    def __init__(self, country_code: str = "FR"):
        country_code = country_code.upper()
        if country_code not in EU_COUNTRIES:
            raise ValueError(
                f"LV 欧洲暂不支持国家 {country_code}，可用: {', '.join(EU_COUNTRIES.keys())}"
            )
        self._country = country_code
        self._cfg = EU_COUNTRIES[country_code]

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
        return self._country

    @property
    def currency(self) -> str:
        return self._cfg["currency"]

    @property
    def base_url(self) -> str:
        return "https://eu.louisvuitton.com"

    @property
    def default_category(self) -> str:
        return "handbags"

    # ===== URL 模板 =====
    @property
    def category_urls(self) -> list[str]:
        locale = self._cfg["locale"]
        return [
            f"https://eu.louisvuitton.com/{locale}/women/handbags/_/N-tfr7qdp",
            f"https://eu.louisvuitton.com/{locale}/men/bags/_/N-t3rblbv",
        ]

    @property
    def category_url_template(self) -> str:
        return ""

    @property
    def product_url_template(self) -> str:
        return f"https://eu.louisvuitton.com/{self._cfg['locale']}/products/{{slug}}"

    @property
    def inventory_api_template(self) -> str:
        # 欧洲门店库存：同 KR/JP 模板，locale 替换
        return f"https://api.louisvuitton.com/api/{self._cfg['locale']}/catalog/inventory/{{sku_id}}"

    # ===== DOM 选择器（适配多语种按钮文案） =====
    @property
    def selectors(self) -> dict[str, str]:
        locale_path = f"/{self._cfg['locale']}/products/"
        return {
            "product_list_container": ".lv-product-list",
            "product_item": f"a[href*='{locale_path}']",
            "product_name": "h1",
            "product_price": ".lv-price",
            "product_image": "picture source[srcset], img[src]",
            "product_sku": "meta[property='product:sku']",
            # 欧洲各国“加载更多”按钮文案：
            # FR: Afficher plus / EN: Show more / DE: Mehr anzeigen
            # IT: Mostra altro / ES: Mostrar más / CH: 依 locale
            "load_more_button": (
                "button:has-text('Afficher plus'),"
                "button:has-text('Show more'),"
                "button:has-text('More')"
            ),
        }

    # ===== 反爬策略 =====
    @property
    def batch_size(self) -> int:
        return 15

    @property
    def request_interval_range(self) -> tuple[float, float]:
        return (3.0, 8.0)

    @property
    def batch_cooldown_range(self) -> tuple[float, float]:
        return (180, 300)

    @property
    def blocked_cooldown(self) -> int:
        return 600

    @property
    def max_consecutive_blocks(self) -> int:
        return 3

    # ===== 数据过滤：只保留包包类 =====
    @property
    def non_product_keywords(self) -> list[str]:
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
        # 欧洲 LV 包包最低参考价
        # FR/DE/IT/ES: ~500 EUR；GB: ~450 GBP；CH: ~500 CHF
        return {
            "EUR": 400,
            "GBP": 350,
            "CHF": 400,
        }.get(self.currency, 300)

    @property
    def max_price(self) -> float:
        return 1_000_000
