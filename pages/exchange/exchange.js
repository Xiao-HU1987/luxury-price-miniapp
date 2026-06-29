const { COUNTRIES } = require('../../utils/constants.js');
const { formatPrice, convertCurrency } = require('../../utils/util.js');

const app = getApp();

Page({
  data: {
    amount: '1000',
    fromCurrency: 'CNY',
    toCurrency: 'USD',
    fromCountry: null,
    toCountry: null,
    convertedAmount: 0,
    convertedDisplay: '0.00',
    currentRateDisplay: '0.0000',
    exchangeRates: null,
    rateList: [],
    updateTime: '',
    showFromPicker: false,
    showToPicker: false,
    countries: COUNTRIES,
    statusBarHeight: 20
  },

  onLoad() {
    this.setData({ statusBarHeight: app.globalData.statusBarHeight || 20 });
    
    const fromCountry = COUNTRIES.find(c => c.currency === this.data.fromCurrency);
    const toCountry = COUNTRIES.find(c => c.currency === this.data.toCurrency);
    this.setData({
      fromCountry,
      toCountry
    });
    this.loadRates();
  },

  onShow() {
    const rates = app.globalData.exchangeRates;
    if (rates) {
      this.setData({ exchangeRates: rates });
      this.calculate();
      this.buildRateList();
    }
  },

  loadRates() {
    let rates = app.globalData.exchangeRates;
    if (!rates) {
      rates = app.updateExchangeRates();
    }
    this.setData({ exchangeRates: rates });
    this.calculate();
    this.buildRateList();
    this.updateUpdateTime();
  },

  updateUpdateTime() {
    if (this.data.exchangeRates && this.data.exchangeRates.updateTime) {
      const date = new Date(this.data.exchangeRates.updateTime);
      const timeStr = date.getFullYear() + '-' +
        String(date.getMonth() + 1).padStart(2, '0') + '-' +
        String(date.getDate()).padStart(2, '0') + ' ' +
        String(date.getHours()).padStart(2, '0') + ':' +
        String(date.getMinutes()).padStart(2, '0');
      this.setData({ updateTime: timeStr });
    }
  },

  buildRateList() {
    const rates = this.data.exchangeRates;
    if (!rates || !rates.rates) return;
    const baseCurrency = this.data.fromCurrency;
    const baseRate = rates.rates[baseCurrency] || 1;
    const list = COUNTRIES
      .filter(c => c.currency !== baseCurrency)
      .map(c => {
        const rate = rates.rates[c.currency] || 0;
        const relativeRate = rate / baseRate;
        return {
          code: c.code,
          name: c.name,
          currency: c.currency,
          currencySymbol: c.currencySymbol,
          flag: c.flag,
          rate: relativeRate,
          rateDisplay: relativeRate.toFixed(4)
        };
      });
    this.setData({ rateList: list });
  },

  onAmountInput(e) {
    const amount = e.detail.value;
    this.setData({ amount });
    this.calculate();
  },

  calculate() {
    const { amount, fromCurrency, toCurrency, exchangeRates } = this.data;
    if (!amount || !exchangeRates || !exchangeRates.rates) {
      this.setData({ 
        convertedAmount: 0,
        convertedDisplay: '0.00',
        currentRateDisplay: '0.0000'
      });
      return;
    }
    const numAmount = parseFloat(amount) || 0;
    const result = convertCurrency(numAmount, fromCurrency, toCurrency, exchangeRates);
    const rate = exchangeRates.rates[toCurrency] / exchangeRates.rates[fromCurrency];
    this.setData({ 
      convertedAmount: result,
      convertedDisplay: result.toFixed(2),
      currentRateDisplay: rate.toFixed(4)
    });
  },

  showFromCurrencyPicker() {
    this.setData({ showFromPicker: true });
  },

  showToCurrencyPicker() {
    this.setData({ showToPicker: true });
  },

  closeFromPicker() {
    this.setData({ showFromPicker: false });
  },

  closeToPicker() {
    this.setData({ showToPicker: false });
  },

  selectFromCurrency(e) {
    const currency = e.currentTarget.dataset.currency;
    const country = COUNTRIES.find(c => c.currency === currency);
    this.setData({
      fromCurrency: currency,
      fromCountry: country,
      showFromPicker: false
    });
    this.calculate();
    this.buildRateList();
  },

  selectToCurrency(e) {
    const currency = e.currentTarget.dataset.currency;
    const country = COUNTRIES.find(c => c.currency === currency);
    this.setData({
      toCurrency: currency,
      toCountry: country,
      showToPicker: false
    });
    this.calculate();
  },

  swapCurrency() {
    const { fromCurrency, toCurrency, fromCountry, toCountry } = this.data;
    this.setData({
      fromCurrency: toCurrency,
      toCurrency: fromCurrency,
      fromCountry: toCountry,
      toCountry: fromCountry
    });
    this.calculate();
    this.buildRateList();
  },

  refreshRates() {
    wx.showLoading({ title: '更新中...' });
    const rates = app.updateExchangeRates();
    this.setData({ exchangeRates: rates });
    this.calculate();
    this.buildRateList();
    this.updateUpdateTime();
    setTimeout(() => {
      wx.hideLoading();
      wx.showToast({ title: '已更新', icon: 'success' });
    }, 500);
  },

  onRateTap(e) {
    const currency = e.currentTarget.dataset.currency;
    const country = COUNTRIES.find(c => c.currency === currency);
    this.setData({
      toCurrency: currency,
      toCountry: country
    });
    this.calculate();
  }
});
