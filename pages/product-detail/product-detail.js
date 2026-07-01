const request = require('../../utils/request.js');
const { BRANDS, COUNTRIES } = require('../../utils/constants.js');
const { formatPrice, convertCurrency, getCountryByCode } = require('../../utils/util.js');

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
    isFavorited: false
  },

  onLoad(options) {
    this.setData({ statusBarHeight: app.globalData.statusBarHeight || 20 });
    const id = options.id;
    if (id) {
      this.setData({ productId: id });
      this.loadProductDetail(id);
    }
  },

  onShow() {
    const rates = app.globalData.exchangeRates;
    if (rates) {
      this.setData({ exchangeRates: rates });
      this.buildPriceList();
    }
    this.checkFavorite();
  },

  loadProductDetail(spuId) {
    const that = this;
    request.get(`/api/product/product-detail/${spuId}`)
      .then(data => {
        if (data) {
          const skuList = data.skus || [];
          const currentSku = skuList.length > 0 ? skuList[0] : null;

          that.setData({
            product: data,
            currentSku: currentSku,
            skuIndex: 0
          });
          that.buildPriceList();
          that.updateNavigationTitle();
          that.addBrowseHistory(spuId, data);
        }
      })
      .catch(() => {
        console.log('商品详情加载失败');
      });
  },

  addBrowseHistory(spuId, productData) {
    const userInfo = app.globalData.userInfo || wx.getStorageSync('userInfo') || {};
    if (!userInfo.user_id) return;

    const product = productData || this.data.product;
    request.post('/api/user/history', {
      user_id: userInfo.user_id,
      target_type: 'product',
      target_id: spuId,
      target_name: product.name || product.name_cn || '',
      target_image: ''
    }).catch(() => {});
  },

  checkFavorite() {
    const userInfo = app.globalData.userInfo || wx.getStorageSync('userInfo') || {};
    if (!userInfo.user_id || !this.data.productId) return;

    const that = this;
    request.get('/api/user/favorites/check', { target_id: that.data.productId })
      .then(data => {
        if (data) {
          that.setData({ isFavorited: data.is_favorited });
        }
      })
      .catch(() => {});
  },

  toggleFavorite() {
    const userInfo = app.globalData.userInfo || wx.getStorageSync('userInfo') || {};
    if (!userInfo.user_id) {
      wx.showToast({ title: '请先登录', icon: 'none' });
      return;
    }

    const that = this;
    const isFavorited = that.data.isFavorited;
    const productId = that.data.productId;
    const product = that.data.product || {};

    if (isFavorited) {
      request.del(`/api/user/favorites/${productId}`)
        .then(() => {
          that.setData({ isFavorited: false });
          wx.showToast({ title: '已取消收藏', icon: 'success' });
        })
        .catch(() => {
          wx.showToast({ title: '操作失败', icon: 'none' });
        });
    } else {
      request.post('/api/user/favorites', {
        user_id: userInfo.user_id,
        target_type: 'product',
        target_id: productId,
        target_name: product.name || product.name_cn || '',
        target_image: ''
      })
        .then(() => {
          that.setData({ isFavorited: true });
          wx.showToast({ title: '收藏成功', icon: 'success' });
        })
        .catch(() => {
          wx.showToast({ title: '操作失败', icon: 'none' });
        });
    }
  },

  updateNavigationTitle() {
    if (this.data.product) {
      wx.setNavigationBarTitle({ title: this.data.product.name || this.data.product.name_cn || '商品详情' });
    }
  },

  buildPriceList() {
    const { product, currentSku, exchangeRates } = this.data;
    if (!product || !currentSku) return;
    
    const skuPrices = currentSku.prices || [];
    const list = skuPrices.map(p => {
      const country = getCountryByCode(p.country);
      let cnyPrice = p.price;
      if (p.country !== 'CN' && exchangeRates && exchangeRates.rates) {
        const rate = exchangeRates.rates[p.country] || 1;
        cnyPrice = p.price / rate;
      }
      
      return {
        countryCode: p.country,
        countryName: country ? country.name : p.country,
        flag: country ? country.flag : '',
        price: p.price,
        priceDisplay: String(Math.round(p.price)).replace(/\B(?=(\d{3})+(?!\d))/g, ','),
        currency: p.currency || p.country,
        currencySymbol: country ? country.currencySymbol : '',
        stock: p.stock || 0,
        store: p.store || '',
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
    const product = this.data.product;
    if (product && product.skus) {
      const sku = product.skus[index];
      this.setData({
        currentSku: sku,
        skuIndex: index
      });
      this.buildPriceList();
    }
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
