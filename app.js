App({
  onLaunch() {
    this.initUser();
    this.initExchangeRates();
    this.initWindowInfo();
  },

  initWindowInfo() {
    try {
      const info = wx.getWindowInfo();
      if (info && info.statusBarHeight) {
        this.globalData.statusBarHeight = info.statusBarHeight;
      }
    } catch (e) {}
  },

  initUser() {
    try {
      const userInfo = wx.getStorageSync('userInfo');
      if (userInfo) {
        this.globalData.userInfo = userInfo;
        return;
      }
    } catch (e) {}

    const newUser = {
      userId: 'U' + Date.now(),
      nickname: '奢品用户',
      avatar: '',
      createTime: new Date().toISOString()
    };
    try {
      wx.setStorageSync('userInfo', newUser);
    } catch (e) {}
    this.globalData.userInfo = newUser;
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
