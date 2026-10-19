"""
LV 数据导入脚本 — 将 aligned 整合数据导入 MySQL 数据库

数据流：
  products_unified.jsonl → SPU + SKU + SKUPrice
  merged_JP.jsonl / merged_KR.jsonl → LvInventory

用法：
  python3 import_lv_data.py           # 全量导入
  python3 import_lv_data.py --dry-run # 仅统计不写入
"""
import json
import logging
import sys
from pathlib import Path
from datetime import datetime, timezone

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("import_lv")

BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from database import SessionLocal, engine, Base
from models.sku import SPU, SKU, SKUPrice
from models.lv import LvInventory
from models.product import Brand, Category
from sqlalchemy.dialects.mysql import insert as mysql_insert


def ensure_tables():
    """确保所有需要的表已创建"""
    Base.metadata.create_all(bind=engine)
    logger.info("数据库表已就绪")


def ensure_brand_category(db):
    """确保 LV 品牌和包包分类存在"""
    brand = db.query(Brand).filter(Brand.brand_id == "lv").first()
    if not brand:
        brand = Brand(
            brand_id="lv",
            name="Louis Vuitton",
            name_cn="路易威登",
            logo="👝",
            category="bags",
        )
        db.add(brand)
        db.flush()
        logger.info("创建品牌: Louis Vuitton")

    cat = db.query(Category).filter(Category.category_id == "bags").first()
    if not cat:
        cat = Category(
            category_id="bags",
            name="包包",
            icon="👜",
        )
        db.add(cat)
        db.flush()
        logger.info("创建分类: 包包")

    return brand, cat


def load_unified():
    """加载 products_unified.jsonl"""
    f = BASE_DIR.parent / "data" / "lv" / "aligned" / "products_unified.jsonl"
    products = []
    with open(f) as fh:
        for line in fh:
            products.append(json.loads(line.strip()))
    logger.info(f"加载 unified: {len(products)} 条")
    return products


def load_merged(country):
    """加载 merged_*.jsonl"""
    f = BASE_DIR.parent / "data" / "lv" / country / f"merged_{country}.jsonl"
    if not f.exists():
        logger.warning(f"文件不存在: {f}")
        return []
    records = []
    with open(f) as fh:
        for line in fh:
            records.append(json.loads(line.strip()))
    logger.info(f"加载 merged_{country}: {len(records)} 条")
    return records


def import_products(db, products, dry_run=False):
    """导入商品数据到 SPU/SKU/SKUPrice"""
    spu_count = sku_count = price_count = 0

    for p in products:
        sku_id_raw = p["sku_id"]
        spu_id = f"spu-lv-{sku_id_raw.lower()}"
        sku_id = f"sku-lv-{sku_id_raw.lower()}"

        # 1. SPU
        spu = db.query(SPU).filter(SPU.spu_id == spu_id).first()
        if not spu:
            spu = SPU(
                spu_id=spu_id,
                brand_id="lv",
                brand_name="路易威登",
                name=p.get("name_jp") or p.get("name_en") or p.get("name_cn") or "",
                name_cn=p.get("name_cn") or "",
                name_en=p.get("name_en") or "",
                image=p.get("image") or "",
                images=json.dumps(p.get("images", []), ensure_ascii=False) if p.get("images") else "",
                source_url=p.get("source_url_cn") or p.get("source_url_jp") or p.get("source_url_kr") or "",
                category_id="bags",
                translate_status="approved",  # 已验证数据
            )
            if not dry_run:
                db.add(spu)
            spu_count += 1
        else:
            # 更新
            spu.name = p.get("name_jp") or spu.name
            spu.name_cn = p.get("name_cn") or spu.name_cn
            spu.name_en = p.get("name_en") or spu.name_en
            spu.image = p.get("image") or spu.image
            spu.source_url = p.get("source_url_cn") or spu.source_url

        # 2. SKU
        sku = db.query(SKU).filter(SKU.sku_id == sku_id).first()
        if not sku:
            sku = SKU(
                sku_id=sku_id,
                spu_id=spu_id,
                name=p.get("name_jp") or p.get("name_en") or p.get("name_cn") or "",
            )
            if not dry_run:
                db.add(sku)
            sku_count += 1

        # 3. SKUPrice (CN/JP/KR)
        price_entries = []
        if p.get("source_cn") and p.get("price_cny"):
            price_entries.append(("CN", "CNY", p["price_cny"]))
        if p.get("source_jp") and p.get("price_jp"):
            price_entries.append(("JP", "JPY", p["price_jp"]))
        if p.get("source_kr") and p.get("price_kr"):
            price_entries.append(("KR", "KRW", p["price_kr"]))

        for country, currency, price in price_entries:
            existing = (
                db.query(SKUPrice)
                .filter(SKUPrice.sku_id == sku_id, SKUPrice.country == country)
                .first()
            )
            if not existing:
                sp = SKUPrice(
                    sku_id=sku_id,
                    country=country,
                    currency=currency,
                    price=price,
                )
                if not dry_run:
                    db.add(sp)
                price_count += 1
            else:
                existing.price = price
                existing.currency = currency

    if not dry_run:
        db.flush()

    logger.info(f"SPU: 新增 {spu_count}, SKU: 新增 {sku_count}, SKUPrice: 新增 {price_count}")
    return spu_count, sku_count, price_count


def import_inventory(db, records, country, dry_run=False):
    """导入库存数据到 LvInventory"""
    import_count = 0

    for r in records:
        sku_id = r["sku_id"]
        for store in r.get("stores", []):
            inv = LvInventory(
                sku_id=sku_id,
                spu_id=f"spu-lv-{sku_id.lower()}",
                store_name=store.get("store_name", ""),
                store_address=store.get("store_address", ""),
                store_city=store.get("store_city", ""),
                in_stock=store.get("in_stock", False),
                stock_status=store.get("stock_status", ""),
                translate_status="pending",
            )
            if not dry_run:
                db.add(inv)
            import_count += 1

    if not dry_run:
        db.flush()

    logger.info(f"{country} 库存: {import_count} 条")
    return import_count


def main():
    import argparse
    parser = argparse.ArgumentParser(description="LV 数据导入")
    parser.add_argument("--dry-run", action="store_true", help="仅统计不写入")
    parser.add_argument("--clear", action="store_true", help="清空 LV 相关表后重新导入")
    args = parser.parse_args()

    ensure_tables()

    db = SessionLocal()
    try:
        # 清空
        if args.clear and not args.dry_run:
            count = db.query(LvInventory).delete()
            logger.info(f"清空 LvInventory: {count} 条")
            count = db.query(SKUPrice).delete()
            logger.info(f"清空 SKUPrice: {count} 条")
            count = db.query(SKU).delete()
            logger.info(f"清空 SKU: {count} 条")
            count = db.query(SPU).filter(SPU.brand_id == "lv").delete()
            logger.info(f"清空 SPU(lv): {count} 条")
            db.flush()

        ensure_brand_category(db)

        # 加载数据
        products = load_unified()
        jp_inv = load_merged("JP")
        kr_inv = load_merged("KR")

        # 导入
        logger.info("\n" + "=" * 60)
        logger.info("开始导入")
        logger.info("=" * 60)

        spu_c, sku_c, price_c = import_products(db, products, args.dry_run)
        jp_c = import_inventory(db, jp_inv, "JP", args.dry_run)
        kr_c = import_inventory(db, kr_inv, "KR", args.dry_run)

        if not args.dry_run:
            db.commit()
            logger.info("事务已提交")

        # 汇总
        logger.info("\n" + "=" * 60)
        logger.info("导入完成")
        logger.info("=" * 60)
        logger.info(f"SPU:       {spu_c} 条")
        logger.info(f"SKU:       {sku_c} 条")
        logger.info(f"SKUPrice:  {price_c} 条")
        logger.info(f"库存(JP):  {jp_c} 条")
        logger.info(f"库存(KR):  {kr_c} 条")
        logger.info(f"库存合计:  {jp_c + kr_c} 条")

    except Exception as e:
        logger.error(f"导入失败: {e}")
        if not args.dry_run:
            db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()