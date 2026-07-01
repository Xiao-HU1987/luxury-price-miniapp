"""初始化测试数据"""
from database import get_db
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
from datetime import datetime, timedelta

def init_test_data():
    db = next(get_db())

    print("开始初始化测试数据...")

    if db.query(ExchangeRate).count() == 0:
        rates = [
            ExchangeRate(base='CNY', target_currency='JPY', rate=21.58, source='mock'),
            ExchangeRate(base='CNY', target_currency='USD', rate=0.14),
            ExchangeRate(base='CNY', target_currency='EUR', rate=0.13),
            ExchangeRate(base='CNY', target_currency='GBP', rate=0.11),
            ExchangeRate(base='CNY', target_currency='HKD', rate=1.08),
            ExchangeRate(base='CNY', target_currency='KRW', rate=190.5),
        ]
        db.add_all(rates)
        db.commit()
        print("  ✓ 汇率数据已添加")

    if db.query(Brand).count() == 0:
        brands = [
            Brand(brand_id='GUCCI', name='Gucci', name_cn='古驰', logo='G', category='luxury'),
            Brand(brand_id='LV', name='Louis Vuitton', name_cn='路易威登', logo='LV', category='luxury'),
            Brand(brand_id='CHANEL', name='Chanel', name_cn='香奈儿', logo='C', category='luxury'),
            Brand(brand_id='DIOR', name='Dior', name_cn='迪奥', logo='D', category='luxury'),
            Brand(brand_id='HERMES', name='Hermes', name_cn='爱马仕', logo='H', category='luxury'),
        ]
        db.add_all(brands)
        db.commit()
        print("  ✓ 品牌数据已添加")

    if db.query(Category).count() == 0:
        categories = [
            Category(category_id='BAG', name='包包', icon='👜'),
            Category(category_id='WALLET', name='钱包', icon='👛'),
            Category(category_id='SHOES', name='鞋子', icon='👟'),
            Category(category_id='WATCH', name='手表', icon='⌚'),
            Category(category_id='ACCESSORY', name='配饰', icon='💍'),
        ]
        db.add_all(categories)
        db.commit()
        print("  ✓ 品类数据已添加")

    if db.query(SPU).count() == 0:
        spus = [
            SPU(spu_id='SPU001', brand_id='GUCCI', brand_name='古驰', category_id='BAG', 
                name='GG Marmont 小号手袋', name_en='GG Marmont Small Bag', article_no='443497'),
            SPU(spu_id='SPU002', brand_id='LV', brand_name='路易威登', category_id='BAG', 
                name='Neverfull 中号手袋', name_en='Neverfull MM', article_no='M41177'),
            SPU(spu_id='SPU003', brand_id='CHANEL', brand_name='香奈儿', category_id='BAG', 
                name='经典口盖包', name_en='Classic Flap Bag', article_no='A01112'),
            SPU(spu_id='SPU004', brand_id='DIOR', brand_name='迪奥', category_id='BAG', 
                name='戴妃包', name_en='Lady Dior', article_no='M0500'),
            SPU(spu_id='SPU005', brand_id='HERMES', brand_name='爱马仕', category_id='BAG', 
                name='铂金包 25', name_en='Birkin 25', article_no='B25'),
        ]
        db.add_all(spus)
        db.commit()
        print("  ✓ SPU数据已添加")

    if db.query(SKU).count() == 0:
        skus = [
            SKU(sku_id='SKU001', spu_id='SPU001', name='黑色小号', color='黑色', size='小号'),
            SKU(sku_id='SKU002', spu_id='SPU002', name='中号老花', color='老花', size='中号'),
            SKU(sku_id='SKU003', spu_id='SPU003', name='小号黑色', color='黑色', size='小号'),
            SKU(sku_id='SKU004', spu_id='SPU004', name='中号红色', color='红色', size='中号'),
            SKU(sku_id='SKU005', spu_id='SPU005', name='25金棕', color='金棕', size='25cm'),
        ]
        db.add_all(skus)
        db.commit()
        print("  ✓ SKU数据已添加")

    if db.query(SKUPrice).count() == 0:
        prices = [
            SKUPrice(sku_id='SKU001', country='CN', currency='CNY', price=25800, stock=10, store='上海国金中心'),
            SKUPrice(sku_id='SKU001', country='JP', currency='JPY', price=548900, stock=5, store='东京银座'),
            SKUPrice(sku_id='SKU001', country='FR', currency='EUR', price=2890, stock=3, store='巴黎香榭丽舍'),
            SKUPrice(sku_id='SKU002', country='CN', currency='CNY', price=15300, stock=20, store='上海恒隆广场'),
            SKUPrice(sku_id='SKU002', country='JP', currency='JPY', price=320000, stock=15, store='大阪心斋桥'),
            SKUPrice(sku_id='SKU002', country='FR', currency='EUR', price=1640, stock=10, store='巴黎春天百货'),
            SKUPrice(sku_id='SKU003', country='CN', currency='CNY', price=61500, stock=2, store='北京SKP'),
            SKUPrice(sku_id='SKU003', country='JP', currency='JPY', price=1320000, stock=1, store='东京表参道'),
            SKUPrice(sku_id='SKU004', country='CN', currency='CNY', price=42000, stock=8, store='上海恒隆广场'),
            SKUPrice(sku_id='SKU004', country='FR', currency='EUR', price=4900, stock=6, store='巴黎蒙田大道'),
            SKUPrice(sku_id='SKU005', country='CN', currency='CNY', price=280000, stock=0, store='北京SKP'),
            SKUPrice(sku_id='SKU005', country='FR', currency='EUR', price=35000, stock=0, store='巴黎福宝大道'),
        ]
        db.add_all(prices)
        db.commit()
        print("  ✓ SKU价格数据已添加")

    if db.query(Coupon).count() == 0:
        coupons = [
            Coupon(coupon_id='CP001', title='近铁百货返点', type='rebate', discount=3.0, 
                   country='JP', store_name='近铁百货', status='available'),
            Coupon(coupon_id='CP002', title='Bic Camera 优惠券', type='discount', discount=17.0, 
                   country='JP', store_name='Bic Camera', status='available'),
            Coupon(coupon_id='CP003', title='银座三越95折', type='discount', discount=5.0, 
                   threshold=10000, country='JP', store_name='银座三越', status='available'),
            Coupon(coupon_id='CP004', title='老佛爷百货优惠券', type='discount', discount=10.0, 
                   country='FR', store_name='老佛爷百货', status='available'),
            Coupon(coupon_id='CP005', title='DFS免税店折扣', type='discount', discount=20.0, 
                   country='HK', store_name='DFS免税店', status='available'),
        ]
        db.add_all(coupons)
        db.commit()
        print("  ✓ 优惠券数据已添加")

    if db.query(Store).count() == 0:
        stores = [
            Store(store_id='ST001', name='近铁百货 难波店', type='mall', country='JP', 
                  city='大阪', address='大阪市中央区難波5-1-18', rating=4.8),
            Store(store_id='ST002', name='银座三越', type='mall', country='JP', 
                  city='东京', address='东京都中央区银座4-6-16', rating=4.9),
            Store(store_id='ST003', name='巴黎老佛爷百货', type='mall', country='FR', 
                  city='巴黎', address='40 Boulevard Haussmann', rating=4.7),
            Store(store_id='ST004', name='巴黎春天百货', type='mall', country='FR', 
                  city='巴黎', address='64 Boulevard Haussmann', rating=4.6),
            Store(store_id='ST005', name='DFS 铜锣湾店', type='dutyfree', country='HK', 
                  city='香港', address='香港铜锣湾轩尼诗道500号', rating=4.5),
            Store(store_id='ST006', name='东京表参道', type='street', country='JP', 
                  city='东京', address='东京都涩谷区神宫前', rating=4.8),
        ]
        db.add_all(stores)
        db.commit()
        print("  ✓ 店铺数据已添加")

    if db.query(Rebate).count() == 0:
        rebates = [
            Rebate(rebate_id='RB001', title='近铁百货返点优惠券', country='JP', rate=3.1, 
                   is_vip_only=False, status='available', 
                   description='免税+当天返3.1%(LV卡地亚等可用)', 
                   start_date='2026-06-10', end_date='2026-06-28'),
            Rebate(rebate_id='RB002', title='Bic Camera 最大返点', country='JP', rate=17.0, 
                   is_vip_only=False, status='available', 
                   description='最大17%折扣+免税', 
                   start_date='2026-01-01', end_date='2026-12-31'),
            Rebate(rebate_id='RB003', title='日本威士忌LINXAS 大阪', country='JP', rate=5.0, 
                   is_vip_only=True, status='available', 
                   description='VIP专属：当天返现5%+免税', 
                   start_date='2026-01-01', end_date='2026-12-31'),
            Rebate(rebate_id='RB004', title='巴黎春天百货VIP返点', country='FR', rate=10.0, 
                   is_vip_only=True, status='available', 
                   description='VIP专属：10%返点', 
                   start_date='2026-01-01', end_date='2026-12-31'),
        ]
        db.add_all(rebates)
        db.commit()
        print("  ✓ 返点数据已添加")

    if db.query(Buyer).count() == 0:
        buyers = [
            Buyer(buyer_id='BY001', name='东京买手小美', country='JP', fee_rate=8.0, 
                  delivery_days=7, rating=4.9, orders=156, intro='常驻东京5年，奢侈品专业买手'),
            Buyer(buyer_id='BY002', name='巴黎老佛爷达人', country='FR', fee_rate=10.0, 
                  delivery_days=10, rating=4.8, orders=203, intro='巴黎本地买手，熟悉各大品牌VIP'),
            Buyer(buyer_id='BY003', name='香港代购小王子', country='HK', fee_rate=5.0, 
                  delivery_days=3, rating=4.7, orders=312, intro='香港人肉代购，当天发货'),
            Buyer(buyer_id='BY004', name='韩国免税店代购', country='KR', fee_rate=6.0, 
                  delivery_days=5, rating=4.6, orders=89, intro='韩国免税店正品代购'),
        ]
        db.add_all(buyers)
        db.commit()
        print("  ✓ 买手数据已添加")

    if db.query(Demand).count() == 0:
        demands = [
            Demand(demand_id='DM001', user_id='test_user1', product_name='Gucci Marmont小号',
                        brand_id='GUCCI', country='JP', deadline='2026-07-15',
                        budget=18000, quantity=1, status='bidding'),
            Demand(demand_id='DM002', user_id='test_user2', product_name='LV Neverfull中号',
                        brand_id='LV', country='FR', deadline='2026-07-20',
                        budget=10000, quantity=1, status='matched'),
        ]
        db.add_all(demands)
        db.commit()
        print("  ✓ 需求数据已添加")

    if db.query(Order).count() == 0:
        orders = [
            Order(order_id='ORD202606300001', user_id='test_user1', buyer_id='BY001',
                  buyer_name='东京买手小美', spu_id='SPU001', sku_id='SKU001',
                  product_name='GG Marmont 小号手袋', sku_spec='黑色小号',
                  quantity=1, original_price=548900, original_currency='JPY',
                  cny_price=25400, fee_rate=8.0, fee_amount=2032,
                  shipping_fee=50, total_amount=27482,
                  status='completed', country='JP', store='东京银座',
                  remark='请小心包装', tracking_no='SF1234567890',
                  tracking_company='顺丰', receiver_name='张三',
                  receiver_phone='13800138000', receiver_address='上海市浦东新区XX路XX号',
                  paid_at=datetime.now() - timedelta(days=10),
                  shipped_at=datetime.now() - timedelta(days=8),
                  completed_at=datetime.now() - timedelta(days=3)),
            Order(order_id='ORD202606300002', user_id='test_user2', buyer_id='BY002',
                  buyer_name='巴黎老佛爷达人', spu_id='SPU002', sku_id='SKU002',
                  product_name='Neverfull 中号手袋', sku_spec='中号老花',
                  quantity=1, original_price=1640, original_currency='EUR',
                  cny_price=12600, fee_rate=10.0, fee_amount=1260,
                  shipping_fee=80, total_amount=13940,
                  status='shipped', country='FR', store='巴黎春天百货',
                  tracking_no='DHL9876543210', tracking_company='DHL',
                  receiver_name='李四', receiver_phone='13900139000',
                  receiver_address='北京市朝阳区XX路XX号',
                  paid_at=datetime.now() - timedelta(days=5),
                  shipped_at=datetime.now() - timedelta(days=2)),
            Order(order_id='ORD202606300003', user_id='test_user1', buyer_id='BY003',
                  buyer_name='香港代购小王子', spu_id='SPU003', sku_id='SKU003',
                  product_name='经典口盖包', sku_spec='小号黑色',
                  quantity=1, original_price=61500, original_currency='CNY',
                  cny_price=61500, fee_rate=5.0, fee_amount=3075,
                  shipping_fee=0, total_amount=64575,
                  status='paid', country='HK', store='DFS免税店',
                  receiver_name='张三', receiver_phone='13800138000',
                  receiver_address='上海市浦东新区XX路XX号',
                  paid_at=datetime.now() - timedelta(days=1)),
            Order(order_id='ORD202606300004', user_id='test_user2', buyer_id='BY001',
                  buyer_name='东京买手小美', spu_id='SPU004', sku_id='SKU004',
                  product_name='戴妃包', sku_spec='中号红色',
                  quantity=1, original_price=42000, original_currency='CNY',
                  cny_price=42000, fee_rate=8.0, fee_amount=3360,
                  shipping_fee=30, total_amount=45390,
                  status='pending', country='JP', store='东京表参道',
                  remark='生日礼物，请包装精美',
                  receiver_name='王五', receiver_phone='13700137000',
                  receiver_address='广州市天河区XX路XX号'),
        ]
        db.add_all(orders)
        db.commit()
        print("  ✓ 订单数据已添加")

    if db.query(AccessLog).count() == 0:
        access_logs = []
        today = datetime.now()
        for i in range(50):
            day_offset = i % 7
            log_time = today - timedelta(days=day_offset, hours=i % 12)
            access_logs.append(AccessLog(
                user_id=f'test_user{(i % 3) + 1}',
                session_id=f'sess_{i}',
                page=['/pages/index/index', '/pages/product-detail/product-detail', '/pages/buyer/buyer', '/pages/exchange/exchange'][i % 4],
                action=['view', 'click', 'search'][i % 3],
                target_id=f'SPU00{(i % 5) + 1}' if i % 2 == 0 else '',
                target_type='spu' if i % 2 == 0 else '',
                ip=f'192.168.1.{i % 255}',
                user_agent='Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X)',
                created_at=log_time
            ))
        db.add_all(access_logs)
        db.commit()
        print("  ✓ 访问日志数据已添加")

    if db.query(OperationLog).count() == 0:
        op_logs = []
        today = datetime.now()
        ops = [
            ('商品管理', '添加', 'GUCCI', '古驰'),
            ('商品管理', '编辑', 'SPU001', 'GG Marmont'),
            ('用户管理', '审核通过', 'BY001', '东京买手小美'),
            ('订单管理', '发货', 'ORD202606300001', 'Gucci Marmont小号'),
            ('营销管理', '添加', 'CP001', '近铁百货返点'),
            ('汇率管理', '更新', 'JPY', '日元汇率'),
            ('门店管理', '添加', 'ST001', '近铁百货 难波店'),
        ]
        for i, (module, action, target_id, target_name) in enumerate(ops):
            op_logs.append(OperationLog(
                admin_id='admin001',
                admin_name='超级管理员',
                module=module,
                action=action,
                target_id=target_id,
                target_name=target_name,
                ip='127.0.0.1',
                user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)',
                remark='后台管理操作',
                created_at=today - timedelta(days=i, hours=i)
            ))
        db.add_all(op_logs)
        db.commit()
        print("  ✓ 运营日志数据已添加")

    if db.query(SplashAd).count() == 0:
        splash_ads = [
            SplashAd(
                title='全球奢侈品比价 新人专享',
                image_url='https://images.unsplash.com/photo-1553062407-98eeb64c6a62?w=800',
                ad_type='image',
                duration=5,
                skip_enabled=True,
                link_type='page',
                link_page='/pages/coupons/coupons',
                is_active=True,
                sort_order=10,
                daily_limit=3,
                show_count=128,
                click_count=32
            ),
            SplashAd(
                title='VIP会员 限时特惠',
                image_url='https://images.unsplash.com/photo-1631986911933-3ea9ad092c74?w=800',
                ad_type='image',
                duration=3,
                skip_enabled=True,
                link_type='none',
                is_active=False,
                sort_order=5,
                daily_limit=1,
                show_count=56,
                click_count=12
            ),
        ]
        db.add_all(splash_ads)
        db.commit()
        print("  ✓ 开屏广告数据已添加")

    if db.query(VipPlan).count() == 0:
        vip_plans = [
            VipPlan(
                plan_id='VIP_MONTH',
                name='月度会员',
                description='尊享30天VIP特权',
                duration_days=30,
                price=29.9,
                original_price=39.9,
                is_popular=False,
                is_active=True,
                sort_order=10
            ),
            VipPlan(
                plan_id='VIP_QUARTER',
                name='季度会员',
                description='尊享90天VIP特权，立省30元',
                duration_days=90,
                price=79.9,
                original_price=119.7,
                is_popular=True,
                is_active=True,
                sort_order=20
            ),
            VipPlan(
                plan_id='VIP_YEAR',
                name='年度会员',
                description='尊享365天VIP特权，立省200元',
                duration_days=365,
                price=199.0,
                original_price=478.8,
                is_popular=False,
                is_active=True,
                sort_order=30
            ),
        ]
        db.add_all(vip_plans)
        db.commit()
        print("  ✓ VIP套餐数据已添加")

    print("\n✓ 所有测试数据初始化完成！")
    print("  - 品牌: 5个")
    print("  - 品类: 5个")
    print("  - SPU: 5个")
    print("  - SKU: 5个")
    print("  - SKU价格: 12条")
    print("  - 优惠券: 5张")
    print("  - 店铺: 6家")
    print("  - 返点: 4个")
    print("  - 买手: 4人")
    print("  - 需求: 2条")
    print("  - 汇率: 6个")
    print("  - 订单: 4条")
    print("  - 访问日志: 50条")
    print("  - 运营日志: 7条")


if __name__ == '__main__':
    init_test_data()
