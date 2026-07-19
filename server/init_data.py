"""初始化测试数据"""
import traceback
from datetime import datetime, timedelta

from models.product import Brand, Category
from models.sku import SPU, SKU, SKUPrice
from models.coupon import Coupon
from models.store import Store
from models.rebate import Rebate
from models.buyer import Buyer
from models.demand import Demand
from models.exchange import ExchangeRate
from models.order import Order
from models.log import AccessLog, OperationLog
from models.splash_ad import SplashAd
from models.vip import VipPlan
import models

def init_test_data():
    try:
        from database import get_db, engine, Base

        print("开始初始化测试数据...")

        try:
            Base.metadata.create_all(bind=engine)
            print("  ✓ 数据表创建完成")
        except Exception as e:
            print(f"  ⚠️ 建表失败，可能已存在: {str(e)[:100]}")

        db = next(get_db())

        if db.query(ExchangeRate).count() == 0:
            rate = ExchangeRate(
                base='CNY',
                rates={
                    'CNY': 1.0,
                    'JPY': 21.58,
                    'USD': 0.138,
                    'EUR': 0.128,
                    'GBP': 0.109,
                    'HKD': 1.075,
                    'KRW': 192.5,
                    'SGD': 0.186,
                    'AUD': 0.215,
                    'CHF': 0.123,
                    'CAD': 0.192,
                    'THB': 4.95,
                }
            )
            db.add(rate)
            db.commit()
            print("  ✓ 汇率数据已添加")

        if db.query(Brand).count() == 0:
            brands = [
                Brand(name='LV', name_cn='路易威登'),
                Brand(name='CHANEL', name_cn='香奈儿'),
                Brand(name='GUCCI', name_cn='古驰'),
                Brand(name='PRADA', name_cn='普拉达'),
                Brand(name='HERMES', name_cn='爱马仕'),
            ]
            db.add_all(brands)
            db.commit()
            print("  ✓ 品牌数据已添加")

        if db.query(Category).count() == 0:
            categories = [
                Category(name='手袋', name_en='Handbags'),
                Category(name='箱包', name_en='Luggage'),
                Category(name='配饰', name_en='Accessories'),
                Category(name='鞋履', name_en='Shoes'),
                Category(name='服饰', name_en='Clothing'),
            ]
            db.add_all(categories)
            db.commit()
            print("  ✓ 品类数据已添加")

        if db.query(SPU).count() == 0:
            lv = db.query(Brand).filter_by(name='LV').first()
            gucci = db.query(Brand).filter_by(name='GUCCI').first()
            chanel = db.query(Brand).filter_by(name='CHANEL').first()
            handbag_cat = db.query(Category).filter_by(name='手袋').first()

            spus = [
                SPU(
                    brand_id=lv.id,
                    category_id=handbag_cat.id,
                    name='Neverfull MM',
                    name_cn='Neverfull 中号手袋',
                    article_no='M40156',
                    description='经典老花图案，大容量购物袋',
                    material='帆布配牛皮',
                    origin='法国',
                    image_url='',
                    created_at=datetime.now(),
                    updated_at=datetime.now()
                ),
                SPU(
                    brand_id=gucci.id,
                    category_id=handbag_cat.id,
                    name='Dionysus',
                    name_cn='酒神包',
                    article_no='421970',
                    description='经典虎头扣设计，链条斜挎包',
                    material='牛皮',
                    origin='意大利',
                    image_url='',
                    created_at=datetime.now(),
                    updated_at=datetime.now()
                ),
                SPU(
                    brand_id=chanel.id,
                    category_id=handbag_cat.id,
                    name='Classic Flap',
                    name_cn='经典口盖包',
                    article_no='A01112',
                    description='经典菱格纹设计，黑金配色',
                    material='羊皮',
                    origin='法国',
                    image_url='',
                    created_at=datetime.now(),
                    updated_at=datetime.now()
                ),
                SPU(
                    brand_id=lv.id,
                    category_id=handbag_cat.id,
                    name='Speedy 25',
                    name_cn='Speedy 25手袋',
                    article_no='M41109',
                    description='经典波士顿包造型，老花图案',
                    material='帆布配牛皮',
                    origin='法国',
                    image_url='',
                    created_at=datetime.now(),
                    updated_at=datetime.now()
                ),
                SPU(
                    brand_id=gucci.id,
                    category_id=handbag_cat.id,
                    name='Jackie 1961',
                    name_cn='Jackie 1961系列手袋',
                    article_no='636708',
                    description='复古半月形设计，马衔扣装饰',
                    material='牛皮',
                    origin='意大利',
                    image_url='',
                    created_at=datetime.now(),
                    updated_at=datetime.now()
                ),
            ]
            db.add_all(spus)
            db.commit()
            print("  ✓ SPU数据已添加")

        if db.query(SKU).count() == 0:
            spus = db.query(SPU).all()
            skus = []
            for spu in spus:
                skus.append(SKU(spu_id=spu.id, color='黑色', size='常规'))
                skus.append(SKU(spu_id=spu.id, color='棕色', size='常规'))
            db.add_all(skus)
            db.commit()
            print("  ✓ SKU数据已添加")

        if db.query(SKUPrice).count() == 0:
            skus = db.query(SKU).all()
            prices = []
            for i, sku in enumerate(skus):
                prices.append(SKUPrice(sku_id=sku.id, country='CN', price=13800 + i*2000, currency='CNY'))
                prices.append(SKUPrice(sku_id=sku.id, country='JP', price=288000 + i*40000, currency='JPY'))
            db.add_all(prices)
            db.commit()
            print("  ✓ SKU价格数据已添加")

        if db.query(Coupon).count() == 0:
            coupons = [
                Coupon(name='新人专享券', description='新用户首单立减', discount_type='fixed', discount_value=100, min_amount=1000, total_quantity=1000, used_quantity=0, status='available', start_time=datetime.now(), end_time=datetime.now() + timedelta(days=30), is_vip_only=False),
                Coupon(name='VIP专属券', description='VIP会员专享折扣', discount_type='percent', discount_value=5, min_amount=5000, total_quantity=500, used_quantity=0, status='available', start_time=datetime.now(), end_time=datetime.now() + timedelta(days=30), is_vip_only=True),
                Coupon(name='满减券', description='满5000减300', discount_type='fixed', discount_value=300, min_amount=5000, total_quantity=2000, used_quantity=0, status='available', start_time=datetime.now(), end_time=datetime.now() + timedelta(days=15), is_vip_only=False),
                Coupon(name='限量抢购券', description='限量发放', discount_type='fixed', discount_value=500, min_amount=10000, total_quantity=100, used_quantity=0, status='available', start_time=datetime.now(), end_time=datetime.now() + timedelta(days=7), is_vip_only=False),
                Coupon(name='生日特权券', description='生日当月专享', discount_type='percent', discount_value=8, min_amount=3000, total_quantity=1000, used_quantity=0, status='available', start_time=datetime.now(), end_time=datetime.now() + timedelta(days=30), is_vip_only=True),
            ]
            db.add_all(coupons)
            db.commit()
            print("  ✓ 优惠券数据已添加")

        if db.query(Store).count() == 0:
            stores = [
                Store(name='日本乐天旗舰店', name_en='Rakuten JP', country='JP', url='https://www.rakuten.co.jp'),
                Store(name='日本亚马逊', name_en='Amazon JP', country='JP', url='https://www.amazon.co.jp'),
                Store(name='法国官网', name_en='France Official', country='FR', url='https://www.louisvuitton.com'),
                Store(name='意大利官网', name_en='Italy Official', country='IT', url='https://www.gucci.com'),
                Store(name='香港专柜', name_en='Hong Kong Store', country='HK', url='https://www.louisvuitton.com/hk'),
                Store(name='国内官网', name_en='China Official', country='CN', url='https://www.louisvuitton.com/cn'),
            ]
            db.add_all(stores)
            db.commit()
            print("  ✓ 店铺数据已添加")

        if db.query(Rebate).count() == 0:
            rebates = [
                Rebate(title='日本乐天返点', description='乐天会员专享返点优惠', brand_name='乐天', store_name='日本乐天旗舰店', country='JP', rate=5.0, status='available', start_time=datetime.now(), end_time=datetime.now() + timedelta(days=30)),
                Rebate(title='法国官网返点', description='法国官网购物返点', brand_name='LV', store_name='法国官网', country='FR', rate=3.0, status='available', start_time=datetime.now(), end_time=datetime.now() + timedelta(days=30)),
                Rebate(title='香港专柜返点', description='香港专柜购物返点', brand_name='CHANEL', store_name='香港专柜', country='HK', rate=2.0, status='available', start_time=datetime.now(), end_time=datetime.now() + timedelta(days=30)),
                Rebate(title='意大利官网返点', description='意大利官网购物返点', brand_name='GUCCI', store_name='意大利官网', country='IT', rate=4.0, status='available', start_time=datetime.now(), end_time=datetime.now() + timedelta(days=30)),
            ]
            db.add_all(rebates)
            db.commit()
            print("  ✓ 返点数据已添加")

        if db.query(Buyer).count() == 0:
            buyers = [
                Buyer(name='小林', country='JP', rating=4.9, completed_orders=128),
                Buyer(name='佐藤', country='JP', rating=4.8, completed_orders=96),
                Buyer(name='李小姐', country='FR', rating=4.9, completed_orders=68),
                Buyer(name='王小姐', country='IT', rating=4.7, completed_orders=45),
            ]
            db.add_all(buyers)
            db.commit()
            print("  ✓ 买手数据已添加")

        if db.query(Demand).count() == 0:
            demands = [
                Demand(user_id=1, product_name='LV Neverfull GM', brand='LV', description='求购大号Neverfull', budget=15000, status='pending'),
                Demand(user_id=1, product_name='CHANEL Classic Flap', brand='CHANEL', description='求购黑金中号', budget=35000, status='pending'),
            ]
            db.add_all(demands)
            db.commit()
            print("  ✓ 求购需求数据已添加")

        if db.query(VipPlan).count() == 0:
            plans = [
                VipPlan(name='月度VIP', description='一个月VIP会员', price=99, duration_days=30),
                VipPlan(name='季度VIP', description='三个月VIP会员', price=258, duration_days=90),
                VipPlan(name='年度VIP', description='一年VIP会员', price=888, duration_days=365),
            ]
            db.add_all(plans)
            db.commit()
            print("  ✓ VIP套餐数据已添加")

        if db.query(Order).count() == 0:
            spu = db.query(SPU).first()
            sku = db.query(SKU).first()
            orders = [
                Order(order_no='BD' + datetime.now().strftime('%Y%m%d') + '0001', user_id=1, spu_id=spu.id, sku_id=sku.id, quantity=1, total_amount=13800, status='pending', pay_status='unpaid', shipping_address='测试地址'),
                Order(order_no='BD' + datetime.now().strftime('%Y%m%d') + '0002', user_id=1, spu_id=spu.id, sku_id=sku.id, quantity=1, total_amount=13800, status='completed', pay_status='paid', shipping_address='测试地址'),
                Order(order_no='BD' + datetime.now().strftime('%Y%m%d') + '0003', user_id=1, spu_id=spu.id, sku_id=sku.id, quantity=1, total_amount=13800, status='shipped', pay_status='paid', shipping_address='测试地址'),
                Order(order_no='BD' + datetime.now().strftime('%Y%m%d') + '0004', user_id=1, spu_id=spu.id, sku_id=sku.id, quantity=1, total_amount=13800, status='refunded', pay_status='refunded', shipping_address='测试地址'),
            ]
            db.add_all(orders)
            db.commit()
            print("  ✓ 订单数据已添加")

        if db.query(AccessLog).count() == 0:
            logs = []
            for i in range(50):
                logs.append(AccessLog(user_id=1, path='/api/product/spus', method='GET', status_code=200, response_time=123 + i*10))
            db.add_all(logs)
            db.commit()
            print("  ✓ 访问日志已添加")

        if db.query(OperationLog).count() == 0:
            logs = [
                OperationLog(user_id=1, action='create', target='product', target_id=1, detail='创建商品'),
                OperationLog(user_id=1, action='update', target='product', target_id=1, detail='更新商品信息'),
                OperationLog(user_id=1, action='delete', target='coupon', target_id=1, detail='删除优惠券'),
                OperationLog(user_id=1, action='create', target='order', target_id=1, detail='创建订单'),
                OperationLog(user_id=1, action='pay', target='order', target_id=1, detail='支付订单'),
                OperationLog(user_id=1, action='ship', target='order', target_id=1, detail='发货'),
                OperationLog(user_id=1, action='refund', target='order', target_id=1, detail='退款'),
            ]
            db.add_all(logs)
            db.commit()
            print("  ✓ 运营日志已添加")

        db.close()
        print("✅ 测试数据初始化完成")

    except Exception as e:
        print(f"\n❌ 初始化测试数据失败: {str(e)}")
        print(f"详细错误:\n{traceback.format_exc()}\n")
        print("提示: 请检查以下项:")
        print("  1. MySQL数据库 'luxury_price' 是否已创建")
        print("  2. DATABASE_URL 中的用户名和密码是否正确")
        print("  3. MySQL用户是否有远程访问权限（主机为 %）")
        print("  4. MySQL服务是否正常运行")

if __name__ == '__main__':
    init_test_data()
