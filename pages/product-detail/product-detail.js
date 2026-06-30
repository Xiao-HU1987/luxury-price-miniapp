const { BRANDS, COUNTRIES } = require('../../utils/constants.js');
const { convertCurrency, getCountryByCode } = require('../../utils/util.js');
const request = require('../../utils/request.js');

const app = getApp();

Page({
  data: {
    statusBarHeight: 20,
    product: null,
    currentSku: null,
    priceList: [],
    exchangeRates: null,
    displayCurrency: 'CNY',
    skuIndex: 0,
    loading: false,
    skus: []
  },

  onLoad(options) {
    this.setData({ statusBarHeight: app.globalData.statusBarHeight || 20 });
    const id = options.id;
    this.loadProductDetail(id);
  },

  onShow() {
    const rates = app.globalData.exchangeRates;
    if (rates) {
      this.setData({ exchangeRates: rates });
      if (this.data.currentSku) {
        this.buildPriceList();
      }
    }
  },

  updateNavigationTitle() {
    if (this.data.product) {
      wx.setNavigationBarTitle({ title: this.data.product.name });
    }
  },

  loadProductDetail(spuId) {
    this.setData({ loading: true });
    request.get('/api/product/product-detail/' + spuId)
      .then((res) => {
        const spu = res.spu;
        const skus = res.skus || [];
        const product = {
          id: spu.spu_id,
          brandId: spu.brand_id,
          brandName: spu.brand_name,
          name: spu.name,
          nameEn: spu.name_en,
          articleNo: spu.article_no,
          category: spu.category_id,
          image: spu.image || '',
          description: spu.description,
          skus: skus
        };

        const currentSku = skus[0] || null;
        this.setData({
          product,
          skus,
          currentSku,
          loading: false
        });
        this.buildPriceList();
        this.updateNavigationTitle();
      })
      .catch((err) => {
        console.error('加载商品详情失败:', err);
        this.setData({ loading: false });
        wx.showToast({ title: '加载失败', icon: 'none' });
      });
  },

  buildPriceList() {
    const { currentSku, exchangeRates } = this.data;
    if (!currentSku || !currentSku.prices) return;
    const prices = currentSku.prices;
    const list = prices.map(p => {
      const code = p.country;
      const country = getCountryByCode(code);
      let cnyPrice = 0;
      if (exchangeRates && exchangeRates.rates) {
        cnyPrice = convertCurrency(p.price, p.currency, 'CNY', exchangeRates);
      }
      return {
        countryCode: code,
        countryName: country.name,
        flag: country.flag,
        price: p.price,
        priceDisplay: String(Math.round(p.price)).replace(/\B(?=(\d{3})+(?!\d))/g, ','),
        currency: p.currency,
        currencySymbol: country.currencySymbol,
        stock: p.stock,
        store: p.store,
        cnyPrice: cnyPrice,
        cnyPriceDisplay: Math.round(cnyPrice).toString(),
        inStock: p.stock > 0
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
    const sku = this.data.skus[index];
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
