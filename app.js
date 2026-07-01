const request = require('./utils/request.js');

App({
  onLaunch() {
    try {
      this.initWindowInfo();
    } catch (e) {
      console.error('初始化窗口信息失败:', e);
    }
    try {
      this.initExchangeRates();
    } catch (e) {
      console.error('初始化汇率失败:', e);
    }
    try {
      this.silentLogin();
    } catch (e) {
      console.error('静默登录失败:', e);
    }
  },

  initWindowInfo() {
    try {
      const info = wx.getWindowInfo();
      if (info && info.statusBarHeight) {
        this.globalData.statusBarHeight = info.statusBarHeight;
      }
    } catch (e) {}
  },

  silentLogin() {
    const token = wx.getStorageSync('token');
    const userInfo = wx.getStorageSync('userInfo');
    if (token && userInfo) {
      this.globalData.userInfo = userInfo;
      this.checkAndRefreshToken();
      return;
    }

    this.doWxLogin();
  },

  doWxLogin() {
    const that = this;
    wx.login({
      success: (res) => {
        if (res.code) {
          that.doLogin(res.code);
        }
      },
      fail: () => {
        console.error('wx.login 失败');
      }
    });
  },

  doLogin(code) {
    const that = this;
    request.post('/api/auth/wechat-login', { code: code })
      .then(data => {
        if (data) {
          that.saveLoginInfo(data);
        }
      })
      .catch(err => {
        console.warn('登录请求失败:', err?.message || err);
      });
  },

  saveLoginInfo(data) {
    wx.setStorageSync('token', data.access_token);
    if (data.session_key) {
      wx.setStorageSync('sessionKey', data.session_key);
    }
    this.globalData.userInfo = data.user;
    wx.setStorageSync('userInfo', data.user);
    if (typeof this.loginCallback === 'function') {
      this.loginCallback(data.user);
    }
  },

  checkAndRefreshToken() {
    const that = this;
    const token = wx.getStorageSync('token');
    if (!token) return;

    request.get('/api/auth/check')
      .then(data => {
        if (data && data.user) {
          that.globalData.userInfo = data.user;
          wx.setStorageSync('userInfo', data.user);
        }
      })
      .catch(() => {
        that.doWxLogin();
      });
  },

  refreshToken() {
    const that = this;
    const token = wx.getStorageSync('token');
    if (!token) {
      that.doWxLogin();
      return Promise.reject('无token');
    }

    return new Promise((resolve, reject) => {
      request.post('/api/auth/refresh')
        .then(data => {
          if (data) {
            that.saveLoginInfo(data);
            resolve(data.access_token);
          } else {
            that.doWxLogin();
            reject('刷新失败');
          }
        })
        .catch(err => {
          that.doWxLogin();
          reject(err);
        });
    });
  },

  initExchangeRates() {
    const that = this;
    
    const defaultRates = that.getDefaultRates();
    that.globalData.exchangeRates = defaultRates;
    try {
      const cached = wx.getStorageSync('exchangeRates');
      if (cached && cached.rates) {
        that.globalData.exchangeRates = cached;
      }
    } catch(e) {}
    
    that.fetchExchangeRates();
  },

  fetchExchangeRates() {
    const that = this;
    request.get('/api/exchange/rates')
      .then(data => {
        if (data && data.rates) {
          const ratesData = {
            updateTime: data.update_time || data.updateTime || new Date().toISOString(),
            base: data.base || 'CNY',
            rates: data.rates
          };
          try {
            wx.setStorageSync('exchangeRates', ratesData);
          } catch(e) {}
          that.globalData.exchangeRates = ratesData;
        }
      })
      .catch(() => {
        console.log('汇率获取失败，使用缓存或默认数据');
      });
  },

  getDefaultRates() {
    return {
      updateTime: new Date().toISOString(),
      base: 'CNY',
      rates: {
        CNY: 1,
        USD: 0.138,
        EUR: 0.128,
        GBP: 0.109,
        JPY: 21.58,
        KRW: 192.5,
        HKD: 1.075,
        SGD: 0.186,
        AUD: 0.215,
        CHF: 0.123,
        CAD: 0.192,
        THB: 4.95
      }
    };
  },

  saveRates(rates) {
    try {
      wx.setStorageSync('exchangeRates', rates);
    } catch (e) {}
    this.globalData.exchangeRates = rates;
  },

  updateExchangeRates() {
    const rates = this.getDefaultRates();
    this.saveRates(rates);
    return rates;
  },

  globalData: {
    userInfo: null,
    exchangeRates: null,
    statusBarHeight: 20
  }
});
