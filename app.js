App({
  onLaunch() {
    // 初始化云开发
    if (wx.cloud) {
      wx.cloud.init({
        env: 'cloud1-d9gvjg9fy04acef08',
        traceUser: true
      });
    }

    try {
      this.initWindowInfo();
    } catch (e) {}

    try {
      this.initExchangeRates();
    } catch (e) {}
  },

  initWindowInfo() {
    try {
      const info = wx.getWindowInfo();
      if (info && info.statusBarHeight) {
        this.globalData.statusBarHeight = info.statusBarHeight;
      }
    } catch (e) {}
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
    } catch (e) {}
    // 后续通过云函数 getExchangeRates 获取实时汇率
    that.fetchExchangeRates();
  },

  fetchExchangeRates() {
    // 汇率获取已改为前端直接请求 Frankfurter API
    // 此方法保留用于 app.globalData 初始化，不再调用云函数
    const that = this;
    const defaultRates = that.getDefaultRates();
    that.globalData.exchangeRates = defaultRates;
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
      },
      channels: []
    };
  },

  globalData: {
    userInfo: null,
    exchangeRates: null,
    statusBarHeight: 20,
    pendingProductId: null
  }
});
