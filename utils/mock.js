const PRODUCTS = [
  {
    id: 'spu001',
    brandId: 'b001',
    brandName: 'Louis Vuitton',
    name: 'CARRYALL 小号手袋',
    articleNo: 'M46203',
    category: 'c001',
    image: '',
    description: '经典CARRYALL小号手袋，Monogram帆布材质。',
    skus: [
      {
        id: 'sku001-001',
        spuId: 'spu001',
        name: 'Monogram 老花',
        color: '老花',
        size: 'MM',
        prices: {
          CN: { price: 23000, currency: 'CNY', stock: 25, store: '上海恒隆广场店' },
          JP: { price: 395000, currency: 'JPY', stock: 20, store: '东京银座店' },
          FR: { price: 2200, currency: 'EUR', stock: 42, store: '巴黎香榭丽舍店' },
          US: { price: 2600, currency: 'USD', stock: 38, store: '纽约第五大道店' },
          HK: { price: 24500, currency: 'HKD', stock: 30, store: '香港海港城店' }
        }
      }
    ]
  },
  {
    id: 'spu002',
    brandId: 'b001',
    brandName: 'Louis Vuitton',
    name: '法棍 DIANE 手袋',
    articleNo: 'M45985',
    category: 'c001',
    image: '',
    description: '法棍包，经典复古设计。',
    skus: [
      {
        id: 'sku002-001',
        spuId: 'spu002',
        name: 'Etoupe 大象灰',
        color: '大象灰',
        size: '30',
        prices: {
          CN: { price: 19600, currency: 'CNY', stock: 8, store: '上海恒隆广场店' },
          JP: { price: 337000, currency: 'JPY', stock: 15, store: '东京银座店' },
          FR: { price: 1880, currency: 'EUR', stock: 22, store: '巴黎福宝总店' },
          US: { price: 2250, currency: 'USD', stock: 18, store: '纽约麦迪逊店' }
        }
      }
    ]
  },
  {
    id: 'spu003',
    brandId: 'b001',
    brandName: 'Louis Vuitton',
    name: 'allinbb 手袋',
    articleNo: 'M12925',
    category: 'c001',
    image: '',
    description: 'ALL IN BB手袋，精致小巧。',
    skus: [
      {
        id: 'sku003-001',
        spuId: 'spu003',
        name: '黑色',
        color: '黑色',
        size: '小号',
        prices: {
          CN: { price: 19400, currency: 'CNY', stock: 12, store: '上海恒隆广场店' },
          JP: { price: 334000, currency: 'JPY', stock: 20, store: '东京银座店' },
          IT: { price: 1850, currency: 'EUR', stock: 28, store: '米兰蒙特拿破仑店' },
          US: { price: 2100, currency: 'USD', stock: 35, store: '纽约第五大道店' }
        }
      }
    ]
  },
  {
    id: 'spu004',
    brandId: 'b001',
    brandName: 'Louis Vuitton',
    name: '法棍 NANO DIANE 手袋',
    articleNo: 'M83298',
    category: 'c001',
    image: '',
    description: 'NANO DIANE迷你法棍包。',
    skus: [
      {
        id: 'sku004-001',
        spuId: 'spu004',
        name: '蓝面钢款',
        color: '蓝色表盘',
        size: '41mm',
        prices: {
          CN: { price: 15300, currency: 'CNY', stock: 10, store: '上海恒隆广场店' },
          JP: { price: 263000, currency: 'JPY', stock: 8, store: '东京银座店' },
          US: { price: 1850, currency: 'USD', stock: 12, store: '纽约第五大道店' }
        }
      }
    ]
  },
  {
    id: 'spu005',
    brandId: 'b007',
    brandName: 'Cartier',
    name: 'LOVE系列戒指',
    nameEn: 'LOVE Ring',
    category: 'c003',
    image: '',
    description: '卡地亚LOVE系列18K黄金戒指，经典螺丝设计。',
    skus: [
      {
        id: 'sku005-001',
        spuId: 'spu005',
        name: '黄金款',
        color: '黄金',
        size: '50',
        prices: {
          CN: { price: 17800, currency: 'CNY', stock: 15, store: '上海恒隆广场店' },
          FR: { price: 1950, currency: 'EUR', stock: 30, store: '巴黎旺多姆店' },
          US: { price: 2310, currency: 'USD', stock: 40, store: '纽约第五大道店' },
          JP: { price: 310000, currency: 'JPY', stock: 25, store: '东京银座店' },
          HK: { price: 18500, currency: 'HKD', stock: 20, store: '香港半岛酒店店' }
        }
      },
      {
        id: 'sku005-002',
        spuId: 'spu005',
        name: '玫瑰金款',
        color: '玫瑰金',
        size: '50',
        prices: {
          CN: { price: 19200, currency: 'CNY', stock: 12, store: '上海恒隆广场店' },
          FR: { price: 2100, currency: 'EUR', stock: 28, store: '巴黎旺多姆店' },
          US: { price: 2490, currency: 'USD', stock: 35, store: '纽约第五大道店' }
        }
      }
    ]
  },
  {
    id: 'spu006',
    brandId: 'b004',
    brandName: 'Chanel',
    name: 'Classic Flap 中号',
    nameEn: 'Classic Flap Medium',
    category: 'c001',
    image: '',
    description: '香奈儿经典口盖包，小羊皮，金扣，中号。',
    skus: [
      {
        id: 'sku006-001',
        spuId: 'spu006',
        name: '黑色金扣',
        color: '黑色',
        size: '中号',
        prices: {
          CN: { price: 62700, currency: 'CNY', stock: 0, store: '上海恒隆广场店' },
          FR: { price: 7100, currency: 'EUR', stock: 3, store: '巴黎康朋街31号' },
          US: { price: 8800, currency: 'USD', stock: 0, store: '纽约麦迪逊店' },
          JP: { price: 1230000, currency: 'JPY', stock: 2, store: '东京银座店' },
          HK: { price: 66000, currency: 'HKD', stock: 0, store: '香港置地广场店' }
        }
      }
    ]
  },
  {
    id: 'spu007',
    brandId: 'b005',
    brandName: 'Dior',
    name: 'Lady Dior 戴妃包',
    nameEn: 'Lady Dior',
    category: 'c001',
    image: '',
    description: 'Lady Dior手袋，经典藤格纹，金属字母吊饰。',
    skus: [
      {
        id: 'sku007-001',
        spuId: 'spu007',
        name: '黑色小羊皮',
        color: '黑色',
        size: '中号',
        prices: {
          CN: { price: 43000, currency: 'CNY', stock: 6, store: '上海恒隆广场店' },
          FR: { price: 4500, currency: 'EUR', stock: 15, store: '巴黎蒙田大道店' },
          US: { price: 5600, currency: 'USD', stock: 12, store: '纽约第五大道店' },
          JP: { price: 780000, currency: 'JPY', stock: 8, store: '东京银座店' },
          HK: { price: 45000, currency: 'HKD', stock: 10, store: '香港海港城店' }
        }
      }
    ]
  },
  {
    id: 'spu008',
    brandId: 'b008',
    brandName: 'Prada',
    name: 'Re-Edition 2005',
    nameEn: 'Re-Edition 2005',
    category: 'c001',
    image: '',
    description: 'Prada Re-Edition 2005 再生尼龙单肩包。',
    skus: [
      {
        id: 'sku008-001',
        spuId: 'spu008',
        name: '黑色',
        color: '黑色',
        size: '均码',
        prices: {
          CN: { price: 11800, currency: 'CNY', stock: 20, store: '上海恒隆广场店' },
          IT: { price: 1200, currency: 'EUR', stock: 45, store: '米兰蒙特拿破仑店' },
          US: { price: 1450, currency: 'USD', stock: 50, store: '纽约第五大道店' },
          KR: { price: 1850000, currency: 'KRW', stock: 30, store: '首尔现代百货店' }
        }
      }
    ]
  }
];

const STORES = [
  {
    id: 's001',
    name: '上海恒隆广场',
    type: 'mall',
    country: 'CN',
    city: '上海',
    address: '静安区南京西路1266号',
    brands: ['b001', 'b002', 'b003', 'b004', 'b005', 'b007', 'b008'],
    rating: 4.8,
    image: ''
  },
  {
    id: 's002',
    name: '北京SKP',
    type: 'mall',
    country: 'CN',
    city: '北京',
    address: '朝阳区建国路87号',
    brands: ['b001', 'b002', 'b003', 'b004', 'b005', 'b006', 'b007', 'b008'],
    rating: 4.9,
    image: ''
  },
  {
    id: 's003',
    name: '巴黎香榭丽舍大街',
    type: 'street',
    country: 'FR',
    city: '巴黎',
    address: 'Avenue des Champs-Élysées',
    brands: ['b001', 'b002', 'b004', 'b005'],
    rating: 4.7,
    image: ''
  },
  {
    id: 's004',
    name: '纽约第五大道',
    type: 'street',
    country: 'US',
    city: '纽约',
    address: 'Fifth Avenue, Manhattan',
    brands: ['b001', 'b002', 'b003', 'b004', 'b005', 'b006', 'b007', 'b008'],
    rating: 4.8,
    image: ''
  },
  {
    id: 's005',
    name: '东京银座',
    type: 'street',
    country: 'JP',
    city: '东京',
    address: '中央区銀座',
    brands: ['b001', 'b002', 'b003', 'b004', 'b005', 'b006', 'b007', 'b008'],
    rating: 4.9,
    image: ''
  },
  {
    id: 's006',
    name: '香港海港城',
    type: 'mall',
    country: 'HK',
    city: '香港',
    address: '九龙尖沙咀广东道3号',
    brands: ['b001', 'b002', 'b003', 'b004', 'b005', 'b007', 'b008'],
    rating: 4.7,
    image: ''
  },
  {
    id: 's007',
    name: '首尔乐天免税店',
    type: 'dutyfree',
    country: 'KR',
    city: '首尔',
    address: '中区乙支路30街83',
    brands: ['b001', 'b002', 'b003', 'b005', 'b007', 'b008'],
    rating: 4.6,
    image: ''
  },
  {
    id: 's008',
    name: '米兰蒙特拿破仑大街',
    type: 'street',
    country: 'IT',
    city: '米兰',
    address: 'Via Montenapoleone',
    brands: ['b002', 'b004', 'b005', 'b008'],
    rating: 4.8,
    image: ''
  },
  {
    id: 's009',
    name: '苏黎世班霍夫大街',
    type: 'street',
    country: 'CH',
    city: '苏黎世',
    address: 'Bahnhofstrasse',
    brands: ['b006', 'b007', 'b002', 'b003'],
    rating: 4.7,
    image: ''
  },
  {
    id: 's010',
    name: '新加坡乌节路',
    type: 'street',
    country: 'SG',
    city: '新加坡',
    address: 'Orchard Road',
    brands: ['b001', 'b002', 'b004', 'b005', 'b007'],
    rating: 4.6,
    image: ''
  }
];

const COUPONS = [
  {
    id: 'cp001',
    title: '新用户首单立减200元',
    type: 'discount',
    discount: 200,
    threshold: 2000,
    country: 'CN',
    storeId: 's001',
    storeName: '上海恒隆广场',
    expireDate: '2026-12-31',
    status: 'available'
  },
  {
    id: 'cp002',
    title: '满1000欧享9折',
    type: 'percent',
    discount: 10,
    threshold: 1000,
    country: 'FR',
    storeId: 's003',
    storeName: '巴黎香榭丽舍',
    expireDate: '2026-08-31',
    status: 'available'
  },
  {
    id: 'cp003',
    title: '腕表品类95折',
    type: 'percent',
    discount: 5,
    threshold: 0,
    country: 'JP',
    storeId: 's005',
    storeName: '东京银座',
    expireDate: '2026-07-31',
    status: 'available'
  },
  {
    id: 'cp004',
    title: '免税店额外返现5%',
    type: 'cashback',
    discount: 5,
    threshold: 0,
    country: 'KR',
    storeId: 's007',
    storeName: '首尔乐天免税店',
    expireDate: '2026-09-30',
    status: 'available'
  },
  {
    id: 'cp005',
    title: '会员专享满5000减500',
    type: 'discount',
    discount: 500,
    threshold: 5000,
    country: 'HK',
    storeId: 's006',
    storeName: '香港海港城',
    expireDate: '2026-10-31',
    status: 'available'
  },
  {
    id: 'cp006',
    title: '夏季特惠 全场85折',
    type: 'percent',
    discount: 15,
    threshold: 0,
    country: 'IT',
    storeId: 's008',
    storeName: '米兰蒙特拿破仑',
    expireDate: '2026-07-15',
    status: 'available'
  }
];

const BUYERS = [
  {
    id: 'by001',
    name: '巴黎代购Lily',
    avatar: '',
    country: 'FR',
    city: '巴黎',
    rating: 4.9,
    orders: 1286,
    specialty: ['b001', 'b003', 'b004', 'b005'],
    deliveryDays: 15,
    feeRate: 8,
    intro: '常驻巴黎8年，专注一线奢侈品代购，支持专柜验货。'
  },
  {
    id: 'by002',
    name: '东京买手Kenji',
    avatar: '',
    country: 'JP',
    city: '东京',
    rating: 4.8,
    orders: 956,
    specialty: ['b006', 'b007', 'b002'],
    deliveryDays: 10,
    feeRate: 10,
    intro: '日本东京资深买手，精通腕表珠宝，速度快价格优。'
  },
  {
    id: 'by003',
    name: '首尔欧尼小铺',
    avatar: '',
    country: 'KR',
    city: '首尔',
    rating: 4.7,
    orders: 2034,
    specialty: ['b001', 'b002', 'b007', 'b008'],
    deliveryDays: 7,
    feeRate: 6,
    intro: '韩国免税店代购，价格全网最低，量大优惠更多。'
  },
  {
    id: 'by004',
    name: '米兰时尚买手',
    avatar: '',
    country: 'IT',
    city: '米兰',
    rating: 4.9,
    orders: 678,
    specialty: ['b002', 'b004', 'b005', 'b008'],
    deliveryDays: 18,
    feeRate: 9,
    intro: '意大利时尚之都买手，品牌合作直供，正品保障。'
  },
  {
    id: 'by005',
    name: '香港代购小王',
    avatar: '',
    country: 'HK',
    city: '香港',
    rating: 4.6,
    orders: 3200,
    specialty: ['b001', 'b002', 'b003', 'b007'],
    deliveryDays: 5,
    feeRate: 5,
    intro: '香港本地代购，当天发货，最快次日达。'
  },
  {
    id: 'by006',
    name: '纽约奢侈品顾问',
    avatar: '',
    country: 'US',
    city: '纽约',
    rating: 4.8,
    orders: 890,
    specialty: ['b003', 'b004', 'b006'],
    deliveryDays: 20,
    feeRate: 12,
    intro: '纽约资深奢侈品顾问，稀有款定制，专业靠谱。'
  }
];

const BUYER_DEMANDS = [
  {
    id: 'd001',
    userId: 'U001',
    productName: 'Hermès Birkin 30 大象灰',
    brandId: 'b003',
    country: 'FR',
    deadline: '2026-07-15',
    budget: 160000,
    budgetCurrency: 'CNY',
    quantity: 1,
    status: 'bidding',
    bids: 3,
    createTime: '2026-06-20T10:30:00Z',
    description: '要银扣，全新全套，支持鉴定。'
  },
  {
    id: 'd002',
    userId: 'U002',
    productName: 'Chanel Classic Flap 中号黑金牛',
    brandId: 'b004',
    country: 'JP',
    deadline: '2026-07-05',
    budget: 70000,
    budgetCurrency: 'CNY',
    quantity: 1,
    status: 'bidding',
    bids: 5,
    createTime: '2026-06-22T15:20:00Z',
    description: '全新未使用，全套包装。'
  },
  {
    id: 'd003',
    userId: 'U003',
    productName: 'Rolex Datejust 41 蓝面',
    brandId: 'b006',
    country: 'CH',
    deadline: '2026-08-01',
    budget: 85000,
    budgetCurrency: 'CNY',
    quantity: 1,
    status: 'matched',
    bids: 8,
    matchedBuyer: 'by002',
    createTime: '2026-06-15T09:00:00Z',
    description: '全新全套，全球联保。'
  }
];

module.exports = {
  PRODUCTS,
  STORES,
  COUPONS,
  BUYERS,
  BUYER_DEMANDS
};
