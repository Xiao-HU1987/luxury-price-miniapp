const BASE_URL = 'http://localhost:8000';

const ENV = {
  development: {
    baseUrl: 'http://localhost:8000',
    debug: true
  },
  production: {
    baseUrl: 'https://your-api-domain.com',
    debug: false
  }
};

const currentEnv = 'development';
const config = ENV[currentEnv];

function request(options) {
  return new Promise((resolve, reject) => {
    const token = wx.getStorageSync('token') || '';
    const header = {
      'Content-Type': 'application/json',
      ...options.header || {}
    };
    if (token) {
      header['Authorization'] = 'Bearer ' + token;
    }

    const url = (options.baseUrl || config.baseUrl) + options.url;

    if (config.debug) {
      console.log('[Request]', options.method || 'GET', url, options.data || {});
    }

    wx.request({
      url: url,
      method: options.method || 'GET',
      data: options.data || {},
      header: header,
      success: (res) => {
        if (config.debug) {
          console.log('[Response]', res.statusCode, res.data);
        }
        if (res.statusCode === 401) {
          wx.removeStorageSync('token');
          wx.removeStorageSync('userInfo');
          const app = getApp();
          if (app) {
            app.globalData.userInfo = null;
          }
          reject(new Error('未登录'));
          return;
        }
        if (res.data && res.data.code === 0) {
          resolve(res.data.data);
        } else {
          reject(new Error(res.data?.message || '请求失败'));
        }
      },
      fail: (err) => {
        if (config.debug) {
          console.error('[Request Error]', err);
        }
        reject(err);
      }
    });
  });
}

module.exports = {
  get: (url, data) => request({ url, method: 'GET', data }),
  post: (url, data) => request({ url, method: 'POST', data }),
  put: (url, data) => request({ url, method: 'PUT', data }),
  del: (url, data) => request({ url, method: 'DELETE', data }),
  BASE_URL: config.baseUrl,
  config,
  setBaseUrl: (url) => { config.baseUrl = url; }
};
