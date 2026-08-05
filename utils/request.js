/**
 * 云开发API封装
 * 将所有HTTP请求映射到云函数调用
 */

const CLOUD_MAP = {
  '/api/product/search': { name: 'getProductList', _method: 'list' },
  '/api/product/brands': { name: 'getProductList', _method: 'brands' },
  '/api/product/product-detail/': { name: 'getProductDetail' },
  '/api/product/detail/': { name: 'getProductDetail' },
  '/api/favorite/list': { name: 'userAction', action: 'getFavorites' },
  '/api/favorite/toggle': { name: 'userAction', action: 'toggleFavorite' },
  '/api/favorite/': { name: 'userAction', action: 'checkFavorite' },
  '/api/history/list': { name: 'userAction', action: 'getHistory' },
  '/api/history/add': { name: 'userAction', action: 'addHistory' },
  '/api/user/history': { name: 'userAction', action: 'addHistory' },
  '/api/user/favorite': { name: 'userAction', action: 'toggleFavorite' },
  '/api/user/profile': { name: 'userAction', action: 'getProfile' },
  '/api/user/settings': { name: 'userAction', action: 'updateSettings' },
  '/api/exchange/rates': { name: 'getExchangeRates' },
  '/api/calc/final': { name: 'calculateFinalPrice' }
};

function matchRoute(url) {
  for (const pattern in CLOUD_MAP) {
    if (url.indexOf(pattern) === 0) {
      return CLOUD_MAP[pattern];
    }
  }
  return null;
}

function callCloudFunction(name, data) {
  return new Promise((resolve, reject) => {
    if (!wx.cloud) {
      reject(new Error('请在微信开发者工具中开启云开发'));
      return;
    }
    wx.cloud.callFunction({
      name,
      data,
      success: (res) => {
        if (res.result && res.result.code === 0) {
          resolve(res.result.data !== undefined ? res.result.data : res.result);
        } else if (res.result && res.result.code === -1) {
          reject(new Error(res.result.message || '请求失败'));
        } else {
          resolve(res.result);
        }
      },
      fail: (err) => {
        reject(new Error(err.errMsg || '云函数调用失败'));
      }
    });
  });
}

function request(options) {
  const { url, method, data } = options;
  const route = matchRoute(url);

  if (!route) {
    console.warn('[cloud] 未匹配到路由:', url);
    return Promise.reject(new Error('未匹配的API路径: ' + url));
  }

  const cloudData = { ...(data || {}) };

  if (route.action) {
    cloudData.action = route.action;
  }
  if (route._method) {
    cloudData._method = route._method;
  }
  // 处理商品详情路径：/api/product/product-detail/{id} 或 /api/product/detail/{id}
  if (url.indexOf('/api/product/product-detail/') === 0) {
    const productId = url.replace('/api/product/product-detail/', '');
    cloudData.productId = productId;
  } else if (url.indexOf('/api/product/detail/') === 0) {
    const productId = url.replace('/api/product/detail/', '');
    cloudData.productId = productId;
  } else if (url.indexOf('/api/favorite/') === 0 && url.replace('/api/favorite/', '').length > 0) {
    const productId = url.replace('/api/favorite/', '');
    cloudData.productId = productId;
  } else if (url.indexOf('/api/user/favorite/') === 0) {
    const productId = url.replace('/api/user/favorite/', '');
    cloudData.productId = productId;
  }

  return callCloudFunction(route.name, cloudData);
}

module.exports = {
  get: (url, data) => request({ url, method: 'GET', data }),
  post: (url, data) => request({ url, method: 'POST', data }),
  put: (url, data) => request({ url, method: 'PUT', data }),
  del: (url, data) => request({ url, method: 'DELETE', data }),
  callCloud: callCloudFunction
};
