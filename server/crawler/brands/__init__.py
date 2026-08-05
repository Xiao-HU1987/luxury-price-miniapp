"""品牌适配器注册表（支持多国家/地区版本）

新增品牌/国家步骤：
1. 在 brands/ 下创建新文件（如 lv_kr.py），继承 BrandAdapter
2. 实现所有抽象属性与方法
3. 在本文件的 _BRAND_REGISTRY 中注册，键为 "{brand_id}_{country}"
4. 爬虫通过 --brand LV --country KR 参数指定
"""
from crawler.brands.base import BrandAdapter
from crawler.brands.lv import LVAdapter
from crawler.brands.lv_kr import LVKRAdapter
from crawler.brands.lv_cn import LVCNAdapter
from crawler.brands.lv_eu import LVEUAdapter, EU_COUNTRIES

# 品牌-国家 注册表，键格式: f"{brand_id}_{country}"
_BRAND_REGISTRY: dict[str, BrandAdapter] = {}


def _key(brand_id: str, country: str) -> str:
    return f"{brand_id.upper()}_{country.upper()}"


def register_brand(adapter: BrandAdapter) -> None:
    """注册品牌适配器（brand+country 联合键）。"""
    k = _key(adapter.brand_id, adapter.country)
    _BRAND_REGISTRY[k] = adapter
    print(f"[品牌注册] {adapter.brand_id}/{adapter.country} - {adapter.brand_name} [{adapter.currency}]")


# 初始化注册所有品牌 + 国家
register_brand(LVAdapter())     # LV_JP
register_brand(LVKRAdapter())   # LV_KR
register_brand(LVCNAdapter())   # LV_CN
# 欧洲各国：单独实例化每个国家
for eu_country in EU_COUNTRIES.keys():
    register_brand(LVEUAdapter(eu_country))  # LV_FR / LV_GB / LV_CH / LV_DE / LV_IT / LV_ES


def get_brand(brand_id: str, country: str = "") -> BrandAdapter:
    """获取品牌适配器。

    Args:
        brand_id: 品牌 ID，如 "LV"
        country:  国家代码，如 "JP", "KR", "CN", "FR", "GB", "CH"。
                  留空时优先取 JP，否则取第一个命中
    """
    if country:
        k = _key(brand_id, country)
        if k not in _BRAND_REGISTRY:
            raise ValueError(
                f"未知品牌/国家组合: {brand_id}/{country}，可用: {', '.join(_BRAND_REGISTRY.keys())}"
            )
        return _BRAND_REGISTRY[k]
    # country 留空：优先按推荐顺序找 LV_JP → LV_KR → LV_CN → LV_FR → 第一个
    for suffix in ("_JP", "_KR", "_CN", "_FR", "_GB", "_CH"):
        k = f"{brand_id.upper()}{suffix}"
        if k in _BRAND_REGISTRY:
            return _BRAND_REGISTRY[k]
    for k, v in _BRAND_REGISTRY.items():
        if k.startswith(f"{brand_id.upper()}_"):
            return v
    raise ValueError(f"未知品牌: {brand_id}，可用: {', '.join(_BRAND_REGISTRY.keys())}")


def list_brands() -> list[dict]:
    """列出所有已注册品牌-国家。"""
    return [
        {
            "brand_id": a.brand_id,
            "brand_name": a.brand_name,
            "brand_name_cn": a.brand_name_cn,
            "country": a.country,
            "currency": a.currency,
            "category": a.default_category,
            "base_url": a.base_url,
        }
        for a in _BRAND_REGISTRY.values()
    ]


__all__ = [
    "BrandAdapter",
    "get_brand",
    "list_brands",
    "register_brand",
]