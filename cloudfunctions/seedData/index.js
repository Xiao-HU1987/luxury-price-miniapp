// seedData - 初始化云数据库
// 一次性将 mock 数据写入云数据库的 products 和 price_stock 集合

const cloud = require('wx-server-sdk');
cloud.init({ env: cloud.DYNAMIC_CURRENT_ENV });

const db = cloud.database();
const _ = db.command;

// 初始化数据
const PRODUCTS = [
  {
    productId: 'M46203',
    nameCn: 'CARRYALL 小号手袋',
    nameEn: 'CARRYALL Small Bag',
    mainImage: '',
    cnOfficialPrice: 23000,
    category: 'handbag',
    brandId: 'b001',
    brandName: 'Louis Vuitton',
    createTime: db.serverDate()
  },
  {
    productId: 'M45985',
    nameCn: '法棍 DIANE 手袋',
    nameEn: 'DIANE Bag',
    mainImage: '',
    cnOfficialPrice: 19600,
    category: 'handbag',
    brandId: 'b001',
    brandName: 'Louis Vuitton',
    createTime: db.serverDate()
  },
  {
    productId: 'M12925',
    nameCn: 'ALL IN BB 手袋',
    nameEn: 'ALL IN BB Bag',
    mainImage: '',
    cnOfficialPrice: 19400,
    category: 'handbag',
    brandId: 'b001',
    brandName: 'Louis Vuitton',
    createTime: db.serverDate()
  },
  {
    productId: 'M83298',
    nameCn: 'NANO DIANE 手袋',
    nameEn: 'NANO DIANE Bag',
    mainImage: '',
    cnOfficialPrice: 15300,
    category: 'handbag',
    brandId: 'b001',
    brandName: 'Louis Vuitton',
    createTime: db.serverDate()
  },
  {
    productId: 'CA001',
    nameCn: 'LOVE 系列戒指',
    nameEn: 'LOVE Ring',
    mainImage: '',
    cnOfficialPrice: 17800,
    category: 'jewelry',
    brandId: 'b007',
    brandName: 'Cartier',
    createTime: db.serverDate()
  },
  {
    productId: 'CH001',
    nameCn: 'Classic Flap 中号',
    nameEn: 'Classic Flap Medium',
    mainImage: '',
    cnOfficialPrice: 62700,
    category: 'handbag',
    brandId: 'b004',
    brandName: 'Chanel',
    createTime: db.serverDate()
  },
  {
    productId: 'DR001',
    nameCn: 'Lady Dior 戴妃包',
    nameEn: 'Lady Dior',
    mainImage: '',
    cnOfficialPrice: 43000,
    category: 'handbag',
    brandId: 'b005',
    brandName: 'Dior',
    createTime: db.serverDate()
  },
  {
    productId: 'PR001',
    nameCn: 'Re-Edition 2005',
    nameEn: 'Re-Edition 2005',
    mainImage: '',
    cnOfficialPrice: 11800,
    category: 'handbag',
    brandId: 'b008',
    brandName: 'Prada',
    createTime: db.serverDate()
  }
];

const PRICE_STOCK = [
  // M46203 - CARRYALL
  { productId: 'M46203', countryCode: 'CN', localPrice: 23000, currency: 'CNY', cnyPrice: 23000, stockStatus: 'available', storeInfo: { city: '上海', storeName: '上海恒隆广场店', address: '静安区南京西路1266号' }, priceUpdateTime: db.serverDate() },
  { productId: 'M46203', countryCode: 'JP', localPrice: 395000, currency: 'JPY', cnyPrice: 18304, stockStatus: 'available', storeInfo: { city: '东京', storeName: '东京银座店', address: '中央区銀座' }, priceUpdateTime: db.serverDate() },

  // M45985 - DIANE
  { productId: 'M45985', countryCode: 'CN', localPrice: 19600, currency: 'CNY', cnyPrice: 19600, stockStatus: 'available', storeInfo: { city: '上海', storeName: '上海恒隆广场店', address: '静安区南京西路1266号' }, priceUpdateTime: db.serverDate() },
  { productId: 'M45985', countryCode: 'JP', localPrice: 337000, currency: 'JPY', cnyPrice: 15616, stockStatus: 'available', storeInfo: { city: '东京', storeName: '东京银座店', address: '中央区銀座' }, priceUpdateTime: db.serverDate() },

  // M12925 - ALL IN BB
  { productId: 'M12925', countryCode: 'CN', localPrice: 19400, currency: 'CNY', cnyPrice: 19400, stockStatus: 'available', storeInfo: { city: '上海', storeName: '上海恒隆广场店', address: '静安区南京西路1266号' }, priceUpdateTime: db.serverDate() },
  { productId: 'M12925', countryCode: 'JP', localPrice: 334000, currency: 'JPY', cnyPrice: 15477, stockStatus: 'available', storeInfo: { city: '东京', storeName: '东京银座店', address: '中央区銀座' }, priceUpdateTime: db.serverDate() },

  // M83298 - NANO DIANE
  { productId: 'M83298', countryCode: 'CN', localPrice: 15300, currency: 'CNY', cnyPrice: 15300, stockStatus: 'available', storeInfo: { city: '上海', storeName: '上海恒隆广场店', address: '静安区南京西路1266号' }, priceUpdateTime: db.serverDate() },
  { productId: 'M83298', countryCode: 'JP', localPrice: 263000, currency: 'JPY', cnyPrice: 12187, stockStatus: 'available', storeInfo: { city: '东京', storeName: '东京银座店', address: '中央区銀座' }, priceUpdateTime: db.serverDate() },

  // CA001 - LOVE Ring
  { productId: 'CA001', countryCode: 'CN', localPrice: 17800, currency: 'CNY', cnyPrice: 17800, stockStatus: 'available', storeInfo: { city: '上海', storeName: '上海恒隆广场店', address: '静安区南京西路1266号' }, priceUpdateTime: db.serverDate() },
  { productId: 'CA001', countryCode: 'JP', localPrice: 310000, currency: 'JPY', cnyPrice: 14365, stockStatus: 'available', storeInfo: { city: '东京', storeName: '东京银座店', address: '中央区銀座' }, priceUpdateTime: db.serverDate() },
  { productId: 'CA001', countryCode: 'KR', localPrice: 3350000, currency: 'KRW', cnyPrice: 17403, stockStatus: 'available', storeInfo: { city: '首尔', storeName: '首尔现代百货店', address: '中区乙支路30街83' }, priceUpdateTime: db.serverDate() },

  // CH001 - Classic Flap
  { productId: 'CH001', countryCode: 'CN', localPrice: 62700, currency: 'CNY', cnyPrice: 62700, stockStatus: 'out_of_stock', storeInfo: { city: '上海', storeName: '上海恒隆广场店', address: '静安区南京西路1266号' }, priceUpdateTime: db.serverDate() },
  { productId: 'CH001', countryCode: 'JP', localPrice: 1230000, currency: 'JPY', cnyPrice: 57000, stockStatus: 'available', storeInfo: { city: '东京', storeName: '东京银座店', address: '中央区銀座' }, priceUpdateTime: db.serverDate() },

  // DR001 - Lady Dior
  { productId: 'DR001', countryCode: 'CN', localPrice: 43000, currency: 'CNY', cnyPrice: 43000, stockStatus: 'available', storeInfo: { city: '上海', storeName: '上海恒隆广场店', address: '静安区南京西路1266号' }, priceUpdateTime: db.serverDate() },
  { productId: 'DR001', countryCode: 'JP', localPrice: 780000, currency: 'JPY', cnyPrice: 36144, stockStatus: 'available', storeInfo: { city: '东京', storeName: '东京银座店', address: '中央区銀座' }, priceUpdateTime: db.serverDate() },

  // PR001 - Re-Edition 2005
  { productId: 'PR001', countryCode: 'CN', localPrice: 11800, currency: 'CNY', cnyPrice: 11800, stockStatus: 'available', storeInfo: { city: '上海', storeName: '上海恒隆广场店', address: '静安区南京西路1266号' }, priceUpdateTime: db.serverDate() },
  { productId: 'PR001', countryCode: 'KR', localPrice: 1850000, currency: 'KRW', cnyPrice: 9610, stockStatus: 'available', storeInfo: { city: '首尔', storeName: '首尔现代百货店', address: '中区乙支路30街83' }, priceUpdateTime: db.serverDate() }
];

const EXCHANGE_RATES = [
  {
    currency: 'JPY',
    baseRate: 21.58,
    channels: [
      { channel: '直接汇款', tieredRules: [{ minAmount: 0, discountRate: 0, description: '基础汇率' }] },
      { channel: 'PayPal', tieredRules: [{ minAmount: 10000, discountRate: 0.01, description: '满1万日元优惠1%' }] }
    ],
    updateTime: db.serverDate()
  },
  {
    currency: 'KRW',
    baseRate: 192.5,
    channels: [
      { channel: '直接汇款', tieredRules: [{ minAmount: 0, discountRate: 0, description: '基础汇率' }] }
    ],
    updateTime: db.serverDate()
  }
];

exports.main = async (event, context) => {
  const { action = 'seed' } = event;

  try {
    // 清空旧数据并重新初始化
    if (action === 'clear-only') {
      const productsCol = db.collection('products');
      const priceStockCol = db.collection('price_stock');
      const ratesCol = db.collection('exchange_rates');

      // 清空集合
      const productsRes = await productsCol.limit(1000).get();
      for (const doc of productsRes.data) {
        await productsCol.doc(doc._id).remove();
      }

      const priceRes = await priceStockCol.limit(1000).get();
      for (const doc of priceRes.data) {
        await priceStockCol.doc(doc._id).remove();
      }

      const ratesRes = await ratesCol.limit(1000).get();
      for (const doc of ratesRes.data) {
        await ratesCol.doc(doc._id).remove();
      }

      return { code: 0, message: '数据已清空', products: productsRes.data.length, priceStocks: priceRes.data.length };
    }

    // 先清空
    const productsCol = db.collection('products');
    const priceStockCol = db.collection('price_stock');
    const ratesCol = db.collection('exchange_rates');

    const productsRes = await productsCol.limit(1000).get();
    for (const doc of productsRes.data) {
      await productsCol.doc(doc._id).remove();
    }

    const priceRes = await priceStockCol.limit(1000).get();
    for (const doc of priceRes.data) {
      await priceStockCol.doc(doc._id).remove();
    }

    const ratesRes = await ratesCol.limit(1000).get();
    for (const doc of ratesRes.data) {
      await ratesCol.doc(doc._id).remove();
    }

    // 批量写入 products
    const productsResult = [];
    for (const product of PRODUCTS) {
      const res = await productsCol.add({ data: product });
      productsResult.push(res._id);
    }

    // 批量写入 price_stock
    const priceStockResult = [];
    for (const ps of PRICE_STOCK) {
      const res = await priceStockCol.add({ data: ps });
      priceStockResult.push(res._id);
    }

    // 批量写入 exchange_rates
    const ratesResult = [];
    for (const rate of EXCHANGE_RATES) {
      const res = await ratesCol.add({ data: rate });
      ratesResult.push(res._id);
    }

    return {
      code: 0,
      message: '数据初始化完成',
      products: productsResult.length,
      priceStocks: priceStockResult.length,
      exchangeRates: ratesResult.length
    };
  } catch (err) {
    console.error('seedData error:', err);
    return { code: -1, message: '初始化失败: ' + err.message };
  }
};
