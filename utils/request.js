const config = require('./config.js');

const BASE_URL = config.BASE_URL;

let isRefreshing = false;
let refreshPromise = null;

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
      success: async (res) => {
        if (res.statusCode === 401) {
          if (!isRefreshing) {
            isRefreshing = true;
            const app = getApp();
            if (app && app.refreshToken) {
              refreshPromise = app.refreshToken()
                .then((newToken) => {
                  isRefreshing = false;
                  return newToken;
                })
                .catch((err) => {
                  isRefreshing = false;
                  wx.removeStorageSync('token');
                  wx.removeStorageSync('userInfo');
                  if (app) {
                    app.globalData.userInfo = null;
                  }
                  throw err;
                });
            } else {
              isRefreshing = false;
              wx.removeStorageSync('token');
              wx.removeStorageSync('userInfo');
              reject(new Error('未登录'));
              return;
            }
          }

          try {
            const newToken = await refreshPromise;
            const newHeader = {
              'Content-Type': 'application/json',
              ...options.header || {}
            };
            if (newToken) {
              newHeader['Authorization'] = 'Bearer ' + newToken;
            }
            wx.request({
              url: BASE_URL + options.url,
              method: options.method || 'GET',
              data: options.data || {},
              header: newHeader,
              success: (res2) => {
                if (res2.data && res2.data.code === 0) {
                  resolve(res2.data.data);
                } else {
                  reject(new Error(res2.data?.message || '请求失败'));
                }
              },
              fail: (err) => {
                reject(err);
              }
            });
          } catch (err) {
            reject(new Error('未登录'));
          }
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
