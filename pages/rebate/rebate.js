const app = getApp();
const request = require('../../utils/request.js');

const DEFAULT_JP_RATE = 21.58;

Page({
  data: {
    rebates: [],
    products: [],
    exchangeRates: null,
    statusBarHeight: 20,
    navBarTotalHeight: 64,
    contentPaddingTop: 80
  },

  onLoad() {
    const sysInfo = wx.getSystemInfoSync();
    const statusBarHeight = sysInfo.statusBarHeight || 20;
    const menuButton = wx.getMenuButtonBoundingClientRect();
    const menuButtonTop = menuButton ? menuButton.top : statusBarHeight + 6;
    const menuButtonBottom = menuButton ? menuButton.bottom : statusBarHeight + 38;
    const navBarTotalHeight = menuButtonBottom + (menuButtonTop - statusBarHeight);
    const contentPaddingTop = navBarTotalHeight + 24;

    this.setData({
      statusBarHeight: statusBarHeight,
      navBarTotalHeight: navBarTotalHeight,
      contentPaddingTop: contentPaddingTop
    });
  },

  onShow() {
    if (typeof this.getTabBar === 'function' && this.getTabBar()) {
      this.getTabBar().setData({ selected: 2 });
    }
    const rates = app.globalData.exchangeRates;
    if (rates) {
      this.setData({ exchangeRates: rates });
    }
    this.loadRebates();
    this.loadProducts();
  },

  loadRebates() {
    const that = this;
    
    request.get('/api/rebate/list', { page: 1, page_size: 50 }).then((data) => {
      if (data && data.list) {
        const rebates = data.list.map(r => ({
          id: r.rebate_id,
          name: r.title,
          description: r.description || '',
          brandName: r.brand_name || '',
          storeName: r.store_name || '',
          country: r.country,
          rate: r.rate,
          status: r.status === 'available' ? 'unused' : 'used',
          statusText: r.status === 'available' ? '可领取' : '已结束',
          logo: that.getRebateLogo(r.country)
        }));
        that.setData({ rebates });
      }
    }).catch(() => {});
  },

  getRebateLogo(country) {
    const logos = {
      'JP': '🚇',
      'FR': '🗼',
      'IT': '🎭',
      'UK': '🇬🇧',
      'US': '🗽',
      'HK': '🏙️',
      'KR': '🎎',
      'CN': '🇨🇳'
    };
    return logos[country] || '🏪';
  },

  loadProducts() {
    const rates = this.data.exchangeRates;
    const jpRate = rates && rates.rates ? (rates.rates.JPY || DEFAULT_JP_RATE) : DEFAULT_JP_RATE;
    
    const that = this;
    request.get('/api/product/spus', { page: 1, page_size: 3 }).then((data) => {
      if (data && data.list) {
        const products = data.list.slice(0, 3).map(p => {
          let jpPriceCny = 0;
          if (p.min_jp_price && p.min_jp_price > 0) {
            jpPriceCny = Math.round(p.min_jp_price / jpRate);
          }
          return {
            id: p.spu_id,
            name: p.name || p.name_cn || '未知商品',
            articleNo: p.article_no || '',
            cnPrice: p.min_cn_price || 0,
            cnPriceStr: String(p.min_cn_price || 0).replace(/\B(?=(\d{3})+(?!\d))/g, ','),
            jpPriceCny: jpPriceCny,
            jpPriceCnyStr: String(jpPriceCny).replace(/\B(?=(\d{3})+(?!\d))/g, ','),
            hasJpPrice: p.min_jp_price && p.min_jp_price > 0
          };
        });
        that.setData({ products });
      }
    }).catch(() => {});
  },

  onCouponTap(e) {
    const coupon = e.currentTarget.dataset.coupon;
    if (coupon.status === 'unused') {
      wx.showToast({ title: '已领取', icon: 'success' });
    } else {
      wx.showToast({ title: '已结束', icon: 'none' });
    }
  },

  onProductTap(e) {
    const productId = e.currentTarget.dataset.productId;
    wx.navigateTo({
      url: '/pages/product-detail/product-detail?id=' + productId
    });
  },

  goToProducts() {
    wx.switchTab({ url: '/pages/index/index' });
  },

  goToMoreRebates() {
    wx.showToast({ title: '更多返点', icon: 'none' });
  },

  goToExchange() {
    wx.switchTab({ url: '/pages/exchange/exchange' });
  },

  goToProfile() {
    wx.switchTab({ url: '/pages/profile/profile' });
  }
});
