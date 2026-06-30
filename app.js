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
    wx.request({
      url: 'http://localhost:8000/api/auth/wechat-login',
      method: 'POST',
      data: { code: code },
      header: { 'Content-Type': 'application/json' },
      success: (res) => {
        if (res.data && res.data.code === 0 && res.data.data) {
          const data = res.data.data;
          wx.setStorageSync('token', data.access_token);
          wx.setStorageSync('sessionKey', data.session_key);
          that.globalData.userInfo = data.user;
          wx.setStorageSync('userInfo', data.user);
        }
      },
      fail: (err) => {
        console.error('登录请求失败:', err);
      }
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
      return;
    }

    try {
      const diff = Date.now() - new Date(cachedRates.updateTime).getTime();
      if (diff > 3600000 || isNaN(diff)) {
        this.saveRates(defaultRates);
      } else {
        this.globalData.exchangeRates = cachedRates;
      }
    } catch (e) {
      this.saveRates(defaultRates);
    }
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
