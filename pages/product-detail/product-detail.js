const { PRODUCTS } = require('../../data/mock.js');
const { BRANDS, COUNTRIES } = require('../../utils/constants.js');
const { formatPrice, convertCurrency, getCountryByCode } = require('../../utils/util.js');

const app = getApp();

Page({
  data: {
    product: null,
    currentSku: null,
    priceList: [],
    exchangeRates: null,
    displayCurrency: 'CNY',
    skuIndex: 0
  },

  onLoad(options) {
    const id = options.id;
    const product = PRODUCTS.find(p => p.id === id);
    if (product) {
      const currentSku = product.skus[0];
      this.setData({
        product,
        currentSku
      });
      this.buildPriceList();
      this.updateNavigationTitle();
    }
  },

  onShow() {
    const rates = app.globalData.exchangeRates;
    if (rates) {
      this.setData({ exchangeRates: rates });
      this.buildPriceList();
    }
  },

  updateNavigationTitle() {
    if (this.data.product) {
      wx.setNavigationBarTitle({ title: this.data.product.name });
    }
  },

  buildPriceList() {
    const { currentSku, exchangeRates } = this.data;
    if (!currentSku) return;
    const prices = currentSku.prices;
    const list = Object.keys(prices).map(code => {
      const priceInfo = prices[code];
      const country = getCountryByCode(code);
      let cnyPrice = 0;
      if (exchangeRates && exchangeRates.rates) {
        cnyPrice = convertCurrency(priceInfo.price, priceInfo.currency, 'CNY', exchangeRates);
      }
      return {
        countryCode: code,
        countryName: country.name,
        flag: country.flag,
        price: priceInfo.price,
        currency: priceInfo.currency,
        currencySymbol: country.currencySymbol,
        stock: priceInfo.stock,
        store: priceInfo.store,
        cnyPrice: cnyPrice,
        inStock: priceInfo.stock > 0
      };
    });
    list.sort((a, b) => a.cnyPrice - b.cnyPrice);
    if (list.length > 0) {
      list[0].isLowest = true;
    }
    this.setData({ priceList: list });
  },

  onSkuTap(e) {
    const index = e.currentTarget.dataset.index;
    const sku = this.data.product.skus[index];
    this.setData({
      currentSku: sku,
      skuIndex: index
    });
    this.buildPriceList();
  },

  goToExchange() {
    wx.switchTab({ url: '/pages/exchange/exchange' });
  },

  findBuyer() {
    wx.switchTab({ url: '/pages/buyer/buyer' });
  },

  goToStores() {
    wx.navigateTo({ url: '/pages/stores/stores' });
  }
});
