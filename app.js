App({
  onLaunch() {
    const userInfo = wx.getStorageSync('userInfo') || null;
    if (!userInfo) {
      const newUser = {
        userId: 'U' + Date.now(),
        nickname: '奢品用户',
        avatar: '',
        createTime: new Date().toISOString()
      };
      wx.setStorageSync('userInfo', newUser);
      this.globalData.userInfo = newUser;
    } else {
      this.globalData.userInfo = userInfo;
    }

    const exchangeRates = wx.getStorageSync('exchangeRates');
    if (!exchangeRates || !exchangeRates.updateTime || 
        (Date.now() - new Date(exchangeRates.updateTime).getTime() > 3600000)) {
      this.updateExchangeRates();
    } else {
      this.globalData.exchangeRates = exchangeRates;
    }
  },

  updateExchangeRates() {
    const rates = {
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
    wx.setStorageSync('exchangeRates', rates);
    this.globalData.exchangeRates = rates;
    return rates;
  },

  globalData: {
    userInfo: null,
    exchangeRates: null
  }
});
