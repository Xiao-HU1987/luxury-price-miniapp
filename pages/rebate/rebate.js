const { PRODUCTS } = require('../../data/mock.js');
const app = getApp();

const DEFAULT_JP_RATE = 21.58;

Page({
  data: {
    jpCoupons: [
      {
        id: 'jp001',
        name: '近铁百货返点二维码(6/10-28)',
        description: '免税+当天返3.1%(LV卡地亚等可用)',
        logo: '🚇',
        status: 'used',
        statusText: '使用'
      },
      {
        id: 'jp002',
        name: '近铁百货9折黑卡(白金卡)',
        description: '',
        logo: '🃏',
        status: 'unused',
        statusText: '领取'
      },
      {
        id: 'jp003',
        name: 'Bic Camera',
        description: '最大17%折扣+免税',
        logo: '📷',
        status: 'used',
        statusText: '使用'
      },
      {
        id: 'jp004',
        name: '日本威士忌LINXAS 大阪',
        description: '当天返现5%+免税',
        logo: '🥃',
        status: 'used',
        statusText: '使用'
      }
    ],
    cnCoupons: [
      {
        id: 'cn001',
        name: 'Gucci返现(广州K11店)',
        description: '当天返现2%',
        logo: 'G',
        status: 'used',
        statusText: '使用'
      }
    ],
    products: [],
    exchangeRates: null,
    statusBarHeight: 20
  },

  onLoad() {
    this.setData({ statusBarHeight: app.globalData.statusBarHeight || 20 });
    this.loadProducts();
  },

  onShow() {
    const rates = app.globalData.exchangeRates;
    if (rates) {
      this.setData({ exchangeRates: rates });
      this.loadProducts();
    }
  },

  loadProducts() {
    const rates = this.data.exchangeRates;
    const jpRate = rates && rates.rates ? (rates.rates.JPY || DEFAULT_JP_RATE) : DEFAULT_JP_RATE;

    const products = PRODUCTS.slice(0, 3).map(p => {
      const firstSku = p.skus[0];
      const prices = firstSku.prices;
      const cnPrice = prices.CN ? prices.CN.price : 0;
      const jpPriceYen = prices.JP ? prices.JP.price : 0;
      let jpPriceCny = 0;
      if (jpPriceYen > 0) {
        jpPriceCny = Math.round(jpPriceYen / jpRate);
      }

      return {
        id: p.id,
        name: p.name,
        articleNo: p.articleNo || '',
        cnPrice: cnPrice,
        cnPriceStr: String(cnPrice).replace(/\B(?=(\d{3})+(?!\d))/g, ','),
        jpPriceCny: jpPriceCny,
        jpPriceCnyStr: String(jpPriceCny).replace(/\B(?=(\d{3})+(?!\d))/g, ','),
        hasJpPrice: jpPriceYen > 0
      };
    });

    this.setData({ products });
  },

  onCouponTap(e) {
    const coupon = e.currentTarget.dataset.coupon;
    if (coupon.status === 'unused') {
      wx.showToast({ title: '已领取', icon: 'success' });
    } else {
      wx.showToast({ title: '使用中', icon: 'none' });
    }
  },

  onProductTap(e) {
    const productId = e.currentTarget.dataset.productId;
    wx.navigateTo({
      url: '/pages/product-detail/product-detail?id=' + productId
    });
  },

  goToMoreProducts() {
    wx.switchTab({ url: '/pages/index/index' });
  },

  goToExchange() {
    wx.switchTab({ url: '/pages/exchange/exchange' });
  },

  goToBuyer() {
    wx.switchTab({ url: '/pages/buyer/buyer' });
  },

  goToProfile() {
    wx.switchTab({ url: '/pages/profile/profile' });
  }
});
