const BASE_URL = 'http://localhost:8000';

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

    wx.request({
      url: BASE_URL + options.url,
      method: options.method || 'GET',
      data: options.data || {},
      header: header,
      success: (res) => {
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
  BASE_URL
};
