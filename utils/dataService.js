/**
 * 数据服务层 - 统一数据访问
 * 优先使用云数据库，fallback 到 mock 数据
 */

const mock = require('../data/mock.js');

// 检测是否在云开发环境
function isCloudAvailable() {
  return typeof wx !== 'undefined' && wx.cloud;
}

// 获取商品列表
async function getProductList(params = {}) {
  const { keyword = '', brandId = '', page = 1, pageSize = 50 } = params;

  // 尝试云函数
  if (isCloudAvailable()) {
    try {
      console.log('[dataService] 调用 getProductList 云函数...');
      const res = await wx.cloud.callFunction({
        name: 'getProductList',
        data: { _method: 'list', keyword, brandId, page, pageSize }
      });
      console.log('[dataService] 云函数返回:', JSON.stringify(res.result).substring(0, 500));
      
      if (res.result && res.result.code === 0 && res.result.data) {
        const count = res.result.data.list ? res.result.data.list.length : 0;
        console.log('[dataService] 成功获取', count, '条商品');
        return res.result.data;
      } else {
        console.warn('[dataService] 云函数返回错误:', res.result);
      }
    } catch (e) {
      console.error('[dataService] 云函数调用异常:', e.message, e.stack);
    }
  } else {
    console.warn('[dataService] 云开发不可用，使用 mock 数据');
  }

  // Fallback 到 mock 数据
  console.log('[dataService] 使用 mock 数据');
  return mock.getProductList({ keyword, brandId, page, pageSize });
}

// 获取品牌列表
async function getBrandList() {
  if (isCloudAvailable()) {
    try {
      const res = await wx.cloud.callFunction({
        name: 'getProductList',
        data: { _method: 'brands' }
      });
      if (res.result && res.result.code === 0) {
        return res.result.data || [];
      }
    } catch (e) {
      console.warn('云函数调用失败，使用 mock 数据:', e.message);
    }
  }

  // Fallback 到 mock 数据
  const brandsMap = {};
  mock.PRODUCTS.forEach(p => {
    if (!brandsMap[p.brandId]) {
      brandsMap[p.brandId] = { brandId: p.brandId, brandName: p.brandName };
    }
  });
  return Object.values(brandsMap);
}

// 获取商品详情
async function getProductDetail(productId) {
  if (isCloudAvailable()) {
    try {
      const res = await wx.cloud.callFunction({
        name: 'getProductDetail',
        data: { productId }
      });
      if (res.result && res.result.code === 0 && res.result.data) {
        return res.result.data;
      }
    } catch (e) {
      console.warn('云函数调用失败，使用 mock 数据:', e.message);
    }
  }

  // Fallback 到 mock 数据
  const product = mock.PRODUCTS.find(p => p.productId === productId);
  if (!product) return null;

  const priceStocks = mock.PRICE_STOCK.filter(ps => ps.productId === productId);
  
  return { product, priceStocks };
}

// 搜索商品
async function searchProducts(keyword, page = 1, pageSize = 20) {
  return getProductList({ keyword, page, pageSize });
}

// 获取最优价格
function getBestPrice(productId) {
  return mock.getBestPrice(productId);
}

// 获取价格对比
function getPriceComparison(productId) {
  return mock.getPriceComparison(productId);
}

// 获取汇率 - 直接从 Frankfurter API 获取实时汇率
async function getExchangeRates() {
  return new Promise((resolve) => {
    wx.request({
      url: 'https://api.frankfurter.app/latest?from=CNY&to=JPY,KRW',
      method: 'GET',
      timeout: 8000,
      success(res) {
        if (res.statusCode === 200 && res.data && res.data.rates) {
          const rates = {
            CNY: 1,
            JPY: res.data.rates.JPY || 21.58,
            KRW: res.data.rates.KRW || 192.5
          };
          resolve({
            rates,
            updateTime: new Date().toISOString()
          });
        } else {
          resolve({
            rates: { CNY: 1, JPY: 21.58, KRW: 192.5 },
            updateTime: new Date().toISOString()
          });
        }
      },
      fail() {
        resolve({
          rates: { CNY: 1, JPY: 21.58, KRW: 192.5 },
          updateTime: new Date().toISOString()
        });
      }
    });
  });
}

module.exports = {
  getProductList,
  getBrandList,
  getProductDetail,
  searchProducts,
  getBestPrice,
  getPriceComparison,
  getExchangeRates,
  // 用户操作
  toggleFavorite,
  getFavorites,
  addHistory,
  getHistory,
  addPriceAlert,
  removePriceAlert,
  getPriceAlerts,
  addToCompare,
  removeFromCompare,
  clearCompare,
  getCompareList
};

// ===== 用户操作：统一调用 userAction 云函数 =====
async function callUserAction(action, data = {}) {
  if (isCloudAvailable()) {
    try {
      const res = await wx.cloud.callFunction({
        name: 'userAction',
        data: { action, ...data }
      });
      if (res.result && res.result.code === 0) {
        return res.result.data !== undefined ? res.result : { code: 0, data: res.result };
      }
      return res.result || { code: -1 };
    } catch (e) {
      console.warn('[userAction] 云函数调用失败', action, e.message);
    }
  }
  return { code: -1, message: '云服务不可用' };
}

async function toggleFavorite(productId) {
  return callUserAction('toggleFavorite', { productId });
}

async function getFavorites() {
  return callUserAction('getFavorites');
}

async function addHistory(productId) {
  return callUserAction('addHistory', { productId });
}

async function getHistory() {
  return callUserAction('getHistory');
}

async function addPriceAlert(productId, targetPrice) {
  return callUserAction('addPriceAlert', { productId, targetPrice });
}

async function removePriceAlert(productId) {
  return callUserAction('removePriceAlert', { productId });
}

async function getPriceAlerts() {
  return callUserAction('getPriceAlerts');
}

async function addToCompare(productId) {
  return callUserAction('addToCompare', { productId });
}

async function removeFromCompare(productId) {
  return callUserAction('removeFromCompare', { productId });
}

async function clearCompare() {
  return callUserAction('clearCompare');
}

async function getCompareList() {
  return callUserAction('getCompareList');
}
