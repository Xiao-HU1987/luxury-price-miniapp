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
                Brand(brand_id='lv', name='LV', name_cn='路易威登'),
                Brand(brand_id='chanel', name='CHANEL', name_cn='香奈儿'),
                Brand(brand_id='gucci', name='GUCCI', name_cn='古驰'),
                Brand(brand_id='prada', name='PRADA', name_cn='普拉达'),
                Brand(brand_id='hermes', name='HERMES', name_cn='爱马仕'),
            ]
            db.add_all(brands)
            db.commit()
            print("  ✓ 品牌数据已添加")

        if db.query(Category).count() == 0:
            categories = [
                Category(category_id='handbags', name='手袋'),
                Category(category_id='luggage', name='箱包'),
                Category(category_id='accessories', name='配饰'),
                Category(category_id='shoes', name='鞋履'),
                Category(category_id='clothing', name='服饰'),
            ]
            db.add_all(categories)
            db.commit()
            print("  ✓ 品类数据已添加")

        if db.query(SPU).count() == 0:
            spus = [
                SPU(
                    spu_id='spu-neverfull-mm',
                    brand_id='lv',
                    brand_name='路易威登',
                    name='Neverfull MM',
                    name_en='Neverfull MM',
                    article_no='M40156',
                    category_id='handbags',
                    image='',
                    description='经典老花图案，大容量购物袋'
                ),
                SPU(
                    spu_id='spu-dionysus',
                    brand_id='gucci',
                    brand_name='古驰',
                    name='Dionysus',
                    name_en='Dionysus',
                    article_no='421970',
                    category_id='handbags',
                    image='',
                    description='经典虎头扣设计，链条斜挎包'
                ),
                SPU(
                    spu_id='spu-classic-flap',
                    brand_id='chanel',
                    brand_name='香奈儿',
                    name='Classic Flap',
                    name_en='Classic Flap',
                    article_no='A01112',
                    category_id='handbags',
                    image='',
                    description='经典菱格纹设计，黑金配色'
                ),
                SPU(
                    spu_id='spu-speedy-25',
                    brand_id='lv',
                    brand_name='路易威登',
                    name='Speedy 25',
                    name_en='Speedy 25',
                    article_no='M41109',
                    category_id='handbags',
                    image='',
                    description='经典波士顿包造型，老花图案'
                ),
                SPU(
                    spu_id='spu-jackie-1961',
                    brand_id='gucci',
                    brand_name='古驰',
                    name='Jackie 1961',
                    name_en='Jackie 1961',
                    article_no='636708',
                    category_id='handbags',
                    image='',
                    description='复古半月形设计，马衔扣装饰'
                ),
            ]
            db.add_all(spus)
            db.commit()
            print("  ✓ SPU数据已添加")

        if db.query(SKU).count() == 0:
            spus = db.query(SPU).all()
            skus = []
            for spu in spus:
                skus.append(SKU(sku_id=f"sku-{spu.spu_id}-black", spu_id=spu.spu_id, name='黑色常规', color='黑色', size='常规'))
                skus.append(SKU(sku_id=f"sku-{spu.spu_id}-brown", spu_id=spu.spu_id, name='棕色常规', color='棕色', size='常规'))
            db.add_all(skus)
            db.commit()
            print("  ✓ SKU数据已添加")

        if db.query(SKUPrice).count() == 0:
            skus = db.query(SKU).all()
            prices = []
            for i, sku in enumerate(skus):
                prices.append(SKUPrice(sku_id=sku.sku_id, country='CN', price=13800 + i*2000, currency='CNY'))
                prices.append(SKUPrice(sku_id=sku.sku_id, country='JP', price=288000 + i*40000, currency='JPY'))
            db.add_all(prices)
            db.commit()
            print("  ✓ SKU价格数据已添加")

        if db.query(Coupon).count() == 0:
            expire_30 = (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d')
            expire_15 = (datetime.now() + timedelta(days=15)).strftime('%Y-%m-%d')
            expire_7 = (datetime.now() + timedelta(days=7)).strftime('%Y-%m-%d')
            coupons = [
                Coupon(coupon_id='c-new-user', title='新人专享券', type='fixed', discount=100, threshold=1000, country='CN', store_id='', store_name='', expire_date=expire_30, status='available'),
                Coupon(coupon_id='c-vip', title='VIP专属券', type='percent', discount=5, threshold=5000, country='CN', store_id='', store_name='', expire_date=expire_30, status='available'),
                Coupon(coupon_id='c-full-reduction', title='满减券', type='fixed', discount=300, threshold=5000, country='CN', store_id='', store_name='', expire_date=expire_15, status='available'),
                Coupon(coupon_id='c-limited', title='限量抢购券', type='fixed', discount=500, threshold=10000, country='CN', store_id='', store_name='', expire_date=expire_7, status='available'),
                Coupon(coupon_id='c-birthday', title='生日特权券', type='percent', discount=8, threshold=3000, country='CN', store_id='', store_name='', expire_date=expire_30, status='available'),
            ]
            db.add_all(coupons)
            db.commit()
            print("  ✓ 优惠券数据已添加")

        if db.query(Store).count() == 0:
            stores = [
                Store(store_id='rakuten-jp', name='日本乐天旗舰店', type='mall', country='JP', city='东京', address='', rating=4.8, image=''),
                Store(store_id='amazon-jp', name='日本亚马逊', type='mall', country='JP', city='东京', address='', rating=4.7, image=''),
                Store(store_id='lv-fr', name='法国官网', type='official', country='FR', city='巴黎', address='', rating=4.9, image=''),
                Store(store_id='gucci-it', name='意大利官网', type='official', country='IT', city='佛罗伦萨', address='', rating=4.8, image=''),
                Store(store_id='lv-hk', name='香港专柜', type='offline', country='HK', city='香港', address='', rating=4.8, image=''),
                Store(store_id='lv-cn', name='国内官网', type='official', country='CN', city='上海', address='', rating=4.9, image=''),
            ]
            db.add_all(stores)
            db.commit()
            print("  ✓ 店铺数据已添加")

        if db.query(Rebate).count() == 0:
            start_date = datetime.now().strftime('%Y-%m-%d')
            end_date = (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d')
            rebates = [
                Rebate(rebate_id='r-rakuten', title='日本乐天返点', brand_id='', brand_name='乐天', store_id='rakuten-jp', store_name='日本乐天旗舰店', country='JP', rate=5.0, is_vip_only=False, status='available', start_date=start_date, end_date=end_date, description='乐天会员专享返点优惠'),
                Rebate(rebate_id='r-lv-fr', title='法国官网返点', brand_id='lv', brand_name='LV', store_id='lv-fr', store_name='法国官网', country='FR', rate=3.0, is_vip_only=False, status='available', start_date=start_date, end_date=end_date, description='法国官网购物返点'),
                Rebate(rebate_id='r-chanel-hk', title='香港专柜返点', brand_id='chanel', brand_name='CHANEL', store_id='lv-hk', store_name='香港专柜', country='HK', rate=2.0, is_vip_only=False, status='available', start_date=start_date, end_date=end_date, description='香港专柜购物返点'),
                Rebate(rebate_id='r-gucci-it', title='意大利官网返点', brand_id='gucci', brand_name='GUCCI', store_id='gucci-it', store_name='意大利官网', country='IT', rate=4.0, is_vip_only=False, status='available', start_date=start_date, end_date=end_date, description='意大利官网购物返点'),
            ]
            db.add_all(rebates)
            db.commit()
            print("  ✓ 返点数据已添加")

        if db.query(Buyer).count() == 0:
            buyers = [
                Buyer(buyer_id='buyer-xiaolin', name='小林', avatar='', country='JP', city='东京', rating=4.9, orders=128, fee_rate=8.0, delivery_days=10, intro=''),
                Buyer(buyer_id='buyer-zuoteng', name='佐藤', avatar='', country='JP', city='大阪', rating=4.8, orders=96, fee_rate=8.5, delivery_days=12, intro=''),
                Buyer(buyer_id='buyer-lili', name='李小姐', avatar='', country='FR', city='巴黎', rating=4.9, orders=68, fee_rate=9.0, delivery_days=14, intro=''),
                Buyer(buyer_id='buyer-wang', name='王小姐', avatar='', country='IT', city='米兰', rating=4.7, orders=45, fee_rate=9.5, delivery_days=15, intro=''),
            ]
            db.add_all(buyers)
            db.commit()
            print("  ✓ 买手数据已添加")

        if db.query(Demand).count() == 0:
            deadline = (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d')
            demands = [
                Demand(demand_id='d-001', user_id='1', product_name='LV Neverfull GM', brand_id='lv', country='', deadline=deadline, budget=15000, budget_currency='CNY', quantity=1, status='bidding', bids=0, matched_buyer_id='', description='求购大号Neverfull'),
                Demand(demand_id='d-002', user_id='1', product_name='CHANEL Classic Flap', brand_id='chanel', country='', deadline=deadline, budget=35000, budget_currency='CNY', quantity=1, status='bidding', bids=0, matched_buyer_id='', description='求购黑金中号'),
            ]
            db.add_all(demands)
            db.commit()
            print("  ✓ 求购需求数据已添加")

        if db.query(VipPlan).count() == 0:
            plans = [
                VipPlan(plan_id='vip-month', name='月度VIP', description='一个月VIP会员', duration_days=30, price=99, original_price=99, is_popular=False, is_active=True, sort_order=1),
                VipPlan(plan_id='vip-quarter', name='季度VIP', description='三个月VIP会员', duration_days=90, price=258, original_price=297, is_popular=True, is_active=True, sort_order=2),
                VipPlan(plan_id='vip-year', name='年度VIP', description='一年VIP会员', duration_days=365, price=888, original_price=1188, is_popular=False, is_active=True, sort_order=3),
            ]
            db.add_all(plans)
            db.commit()
            print("  ✓ VIP套餐数据已添加")

        if db.query(Order).count() == 0:
            spu = db.query(SPU).filter_by(spu_id='spu-neverfull-mm').first()
            sku = db.query(SKU).filter_by(sku_id='sku-spu-neverfull-mm-black').first()
            if spu and sku:
                orders = [
                    Order(order_id='BD' + datetime.now().strftime('%Y%m%d') + '0001', user_id='1', buyer_id='', buyer_name='', spu_id=spu.spu_id, sku_id=sku.sku_id, product_name=spu.name, product_image='', sku_spec='黑色/常规', quantity=1, original_price=13800, original_currency='CNY', cny_price=13800, fee_rate=0, fee_amount=0, shipping_fee=0, total_amount=13800, status='pending', country='CN', store='', remark='', tracking_no='', tracking_company='', receiver_name='', receiver_phone='', receiver_address='测试地址'),
                    Order(order_id='BD' + datetime.now().strftime('%Y%m%d') + '0002', user_id='1', buyer_id='', buyer_name='', spu_id=spu.spu_id, sku_id=sku.sku_id, product_name=spu.name, product_image='', sku_spec='黑色/常规', quantity=1, original_price=13800, original_currency='CNY', cny_price=13800, fee_rate=0, fee_amount=0, shipping_fee=0, total_amount=13800, status='completed', country='CN', store='', remark='', tracking_no='', tracking_company='', receiver_name='', receiver_phone='', receiver_address='测试地址'),
                    Order(order_id='BD' + datetime.now().strftime('%Y%m%d') + '0003', user_id='1', buyer_id='', buyer_name='', spu_id=spu.spu_id, sku_id=sku.sku_id, product_name=spu.name, product_image='', sku_spec='黑色/常规', quantity=1, original_price=13800, original_currency='CNY', cny_price=13800, fee_rate=0, fee_amount=0, shipping_fee=0, total_amount=13800, status='shipped', country='CN', store='', remark='', tracking_no='', tracking_company='', receiver_name='', receiver_phone='', receiver_address='测试地址'),
                    Order(order_id='BD' + datetime.now().strftime('%Y%m%d') + '0004', user_id='1', buyer_id='', buyer_name='', spu_id=spu.spu_id, sku_id=sku.sku_id, product_name=spu.name, product_image='', sku_spec='黑色/常规', quantity=1, original_price=13800, original_currency='CNY', cny_price=13800, fee_rate=0, fee_amount=0, shipping_fee=0, total_amount=13800, status='cancelled', country='CN', store='', remark='', tracking_no='', tracking_company='', receiver_name='', receiver_phone='', receiver_address='测试地址'),
                ]
                db.add_all(orders)
                db.commit()
                print("  ✓ 订单数据已添加")
            else:
                print("  ⚠️ 未找到SPU/SKU，跳过订单数据初始化")

        if db.query(AccessLog).count() == 0:
            logs = []
            for i in range(50):
                logs.append(AccessLog(user_id='1', session_id='', page='/api/product/spus', action='view', target_id='', target_type='', ip='', user_agent='', referer=''))
            db.add_all(logs)
            db.commit()
            print("  ✓ 访问日志已添加")

        if db.query(OperationLog).count() == 0:
            logs = [
                OperationLog(admin_id='1', admin_name='管理员', module='product', action='create', target_id='1', target_name='商品', before_data='', after_data='', ip='', user_agent='', remark='创建商品'),
                OperationLog(admin_id='1', admin_name='管理员', module='product', action='update', target_id='1', target_name='商品', before_data='', after_data='', ip='', user_agent='', remark='更新商品信息'),
                OperationLog(admin_id='1', admin_name='管理员', module='coupon', action='delete', target_id='1', target_name='优惠券', before_data='', after_data='', ip='', user_agent='', remark='删除优惠券'),
                OperationLog(admin_id='1', admin_name='管理员', module='order', action='create', target_id='1', target_name='订单', before_data='', after_data='', ip='', user_agent='', remark='创建订单'),
                OperationLog(admin_id='1', admin_name='管理员', module='order', action='update', target_id='1', target_name='订单', before_data='', after_data='', ip='', user_agent='', remark='支付订单'),
                OperationLog(admin_id='1', admin_name='管理员', module='order', action='update', target_id='1', target_name='订单', before_data='', after_data='', ip='', user_agent='', remark='发货'),
                OperationLog(admin_id='1', admin_name='管理员', module='order', action='update', target_id='1', target_name='订单', before_data='', after_data='', ip='', user_agent='', remark='退款'),
            ]
            db.add_all(logs)
            db.commit()
            print("  ✓ 运营日志已添加")

        if db.query(SplashAd).count() == 0:
            ads = [
                SplashAd(title='新人专享', image_url='', video_url='', ad_type='image', duration=5, skip_enabled=True, link_type='none', link_url='', link_page='', is_active=True, sort_order=1),
            ]
            db.add_all(ads)
            db.commit()
            print("  ✓ 开屏广告数据已添加")

        db.close()
        print("✅ 测试数据初始化完成")
        return True

    except Exception as e:
        print(f"\n❌ 初始化测试数据失败: {str(e)}")
        print(f"详细错误:\n{traceback.format_exc()}\n")
        print("提示: 请检查以下项:")
        print("  1. MySQL数据库 'luxury_price' 是否已创建")
        print("  2. DATABASE_URL 中的用户名和密码是否正确")
        print("  3. MySQL用户是否有远程访问权限（主机为 %）")
        print("  4. MySQL服务是否正常运行")
        return False


if __name__ == '__main__':
    success = init_test_data()
    exit(0 if success else 1)
