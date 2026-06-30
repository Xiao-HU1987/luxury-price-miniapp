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
      return;
    }

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
      .then((data) => {
        if (data && data.access_token) {
          wx.setStorageSync('token', data.access_token);
          wx.setStorageSync('sessionKey', data.session_key);
          that.globalData.userInfo = data.user;
          wx.setStorageSync('userInfo', data.user);
        }
      })
      .catch((err) => {
        console.error('登录请求失败:', err);
      });
  },

  initExchangeRates() {
    let cachedRates = null;
    try {
      cachedRates = wx.getStorageSync('exchangeRates');
    } catch (e) {}

    const defaultRates = this.getDefaultRates();

    if (!cachedRates || !cachedRates.updateTime) {
      this.saveRates(defaultRates);
      this.fetchExchangeRatesFromServer();
      return;
    }

    try {
      const diff = Date.now() - new Date(cachedRates.updateTime).getTime();
      if (diff > 3600000 || isNaN(diff)) {
        this.saveRates(defaultRates);
        this.fetchExchangeRatesFromServer();
      } else {
        this.globalData.exchangeRates = cachedRates;
      }
    } catch (e) {
      this.saveRates(defaultRates);
      this.fetchExchangeRatesFromServer();
    }
  },

  fetchExchangeRatesFromServer() {
    const that = this;
    request.get('/api/exchange/rates')
      .then((data) => {
        if (data && data.rates) {
          const rates = {
            updateTime: data.update_time || new Date().toISOString(),
            base: data.base || 'CNY',
            rates: data.rates
          };
          that.saveRates(rates);
        }
      })
      .catch((err) => {
        console.error('从服务器获取汇率失败:', err);
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
    return new Promise((resolve, reject) => {
      const that = this;
      request.get('/api/exchange/rates')
        .then((data) => {
          if (data && data.rates) {
            const rates = {
              updateTime: data.update_time || new Date().toISOString(),
              base: data.base || 'CNY',
              rates: data.rates
            };
            that.saveRates(rates);
            resolve(rates);
          } else {
            const defaultRates = that.getDefaultRates();
            that.saveRates(defaultRates);
            resolve(defaultRates);
          }
        })
        .catch((err) => {
          console.error('刷新汇率失败:', err);
          const defaultRates = that.getDefaultRates();
          that.saveRates(defaultRates);
          resolve(defaultRates);
        });
    });
  },

  globalData: {
    userInfo: null,
    exchangeRates: null,
    statusBarHeight: 20
  }
});
