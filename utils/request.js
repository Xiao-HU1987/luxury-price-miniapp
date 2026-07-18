const config = require('./config.js');

const BASE_URL = config.BASE_URL;

let isRefreshing = false;
let refreshPromise = null;

const MAX_RETRY_COUNT = 2;
const RETRY_DELAY = 1000;
const TIMEOUT_MS = 10000;

function isNetworkError(err) {
  if (!err) return false;
  const errMsg = err.errMsg || err.message || '';
  return errMsg.indexOf('timeout') > -1 ||
         errMsg.indexOf('network') > -1 ||
         errMsg.indexOf('request:fail') > -1;
}

function requestWithRetry(options, retryCount = 0) {
  return new Promise((resolve, reject) => {
    const token = wx.getStorageSync('token') || '';
    const header = {
      'Content-Type': 'application/json',
      ...options.header || {}
    };
    if (token) {
      header['Authorization'] = 'Bearer ' + token;
    }

    const requestTask = wx.request({
      url: BASE_URL + options.url,
      method: options.method || 'GET',
      data: options.data || {},
      header: header,
      timeout: TIMEOUT_MS,
      success: async (res) => {
        if (res.statusCode === 401) {
          if (!isRefreshing) {
            isRefreshing = true;
            const app = getApp();
            wx.removeStorageSync('token');
            wx.removeStorageSync('userInfo');
            if (app) {
              app.globalData.userInfo = null;
            }
            refreshPromise = new Promise((resolve, reject) => {
              wx.login({
                success: (loginRes) => {
                  if (loginRes.code) {
                    wx.request({
                      url: BASE_URL + '/api/auth/wechat-login',
                      method: 'POST',
                      data: { code: loginRes.code },
                      header: { 'Content-Type': 'application/json' },
                      success: (loginRes2) => {
                        if (loginRes2.data && loginRes2.data.code === 0 && loginRes2.data.data) {
                          const loginData = loginRes2.data.data;
                          wx.setStorageSync('token', loginData.access_token);
                          if (loginData.session_key) {
                            wx.setStorageSync('sessionKey', loginData.session_key);
                          }
                          if (app && loginData.user) {
                            app.globalData.userInfo = loginData.user;
                            wx.setStorageSync('userInfo', loginData.user);
                          }
                          isRefreshing = false;
                          resolve(loginData.access_token);
                        } else {
                          isRefreshing = false;
                          reject(new Error('登录失败'));
                        }
                      },
                      fail: () => {
                        isRefreshing = false;
                        reject(new Error('登录失败'));
                      }
                    });
                  } else {
                    isRefreshing = false;
                    reject(new Error('获取登录码失败'));
                  }
                },
                fail: () => {
                  isRefreshing = false;
                  reject(new Error('登录失败'));
                }
              });
            });
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
              timeout: TIMEOUT_MS,
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
        if (isNetworkError(err) && retryCount < MAX_RETRY_COUNT) {
          setTimeout(() => {
            requestWithRetry(options, retryCount + 1)
              .then(resolve)
              .catch(reject);
          }, RETRY_DELAY);
        } else {
          const networkErr = new Error('网络连接失败，请检查网络后重试');
          networkErr.originalError = err;
          reject(networkErr);
        }
      }
    });
  });
}

function request(options) {
  return requestWithRetry(options, 0);
}

module.exports = {
  get: (url, data) => request({ url, method: 'GET', data }),
  post: (url, data) => request({ url, method: 'POST', data }),
  put: (url, data) => request({ url, method: 'PUT', data }),
  del: (url, data) => request({ url, method: 'DELETE', data }),
  BASE_URL,
  isNetworkError
};
