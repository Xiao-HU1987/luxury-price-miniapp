/**
 * 数据服务层 - 统一数据访问
 * 优先使用云数据库，fallback 到 mock 数据
 */

const mock = require('./mock.js');

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

// 获取汇率 - 优先通过云函数获取实时汇率（云端不受域名白名单限制）
// 云函数不可用时，降级为本地请求 Frankfurter API；仍失败则用兜底汇率
async function getExchangeRates() {
  const fallbackRates = { CNY: 1, JPY: 21.58, KRW: 192.5 };

  // 1. 优先走云函数（生产环境唯一合法途径）
  if (wx.cloud) {
    try {
      const res = await wx.cloud.callFunction({ name: 'getExchangeRates' });
      const r = res && res.result;
      if (r && r.code === 0 && r.data && r.data.rates) {
        return {
          rates: { CNY: 1, JPY: r.data.rates.JPY || fallbackRates.JPY, KRW: r.data.rates.KRW || fallbackRates.KRW },
          updateTime: r.data.updateTime || new Date().toISOString()
        };
      }
    } catch (e) {
      // 云函数失败，继续尝试本地请求
    }
  }

  // 2. 降级：本地请求 Frankfurter API（仅限开发者工具中可用，线上会被域名校验拦截）
  return new Promise((resolve) => {
    wx.request({
      url: 'https://api.frankfurter.app/latest?from=CNY&to=JPY,KRW',
      method: 'GET',
      timeout: 8000,
      success(res) {
        if (res.statusCode === 200 && res.data && res.data.rates) {
          resolve({
            rates: {
              CNY: 1,
              JPY: res.data.rates.JPY || fallbackRates.JPY,
              KRW: res.data.rates.KRW || fallbackRates.KRW
            },
            updateTime: new Date().toISOString()
          });
        } else {
          resolve({ rates: fallbackRates, updateTime: new Date().toISOString() });
        }
      },
      fail() {
        resolve({ rates: fallbackRates, updateTime: new Date().toISOString() });
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
