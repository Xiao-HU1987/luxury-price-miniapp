"""LV 专属数据模型

与通用 models/sku.py 中的 SPU/SKU/SKUPrice 配套使用，
仅承载 LV 日本官网爬虫所需的特有数据（按门店维度的库存记录）。
"""
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, Index
from sqlalchemy.sql import func

from database import Base


class LvInventory(Base):
    """LV 商品在特定门店的库存记录

    设计要点：
    - 一个 SKU 在同一家门店一天可能有多次抓取，按 (sku_id, store_id, store_name) 维度保留历史
    - 使用 unique 约束保证同一门店同一 SKU 的最新记录可被 upsert
    - stock_status 原文保存（"在庫あり" / "在庫なし" / "残りわずか" 等），
      方便前端展示日文原文
    - 翻译字段（_cn 后缀）存储中文翻译，translate_status 控制校对流程：
      pending → translated（已翻译待校对）→ approved（已校对确认）
    """
    __tablename__ = "lv_inventories"

    id = Column(Integer, primary_key=True, index=True)
    sku_id = Column(String(64), index=True, nullable=False)
    spu_id = Column(String(64), index=True, default="")
    store_id = Column(String(64), default="", index=True)
    store_name = Column(String(128), default="")
    store_name_cn = Column(String(128), default="")           # 中文翻译
    store_address = Column(String(255), default="")
    store_address_cn = Column(String(255), default="")        # 中文翻译
    store_city = Column(String(64), default="")
    store_city_cn = Column(String(64), default="")            # 中文翻译
    in_stock = Column(Boolean, default=False)
    stock_status = Column(String(32), default="")
    translate_status = Column(String(16), default="pending", index=True)  # pending / translated / approved
    translated_at = Column(DateTime(timezone=True), nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    queried_at = Column(DateTime(timezone=True), server_default=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    __table_args__ = (
        Index("idx_lv_inv_sku_store", "sku_id", "store_id"),
    )
