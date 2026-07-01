const app = getApp();
const request = require('../../utils/request.js');

const DEFAULT_JP_RATE = 21.58;

Page({
  data: {
    rebates: [],
    products: [],
    exchangeRates: null,
    statusBarHeight: 20,
    isVip: false
  },

  onLoad() {
    this.setData({ statusBarHeight: app.globalData.statusBarHeight || 20 });
    this.checkUserVip();
  },

  onShow() {
    const rates = app.globalData.exchangeRates;
    if (rates) {
      this.setData({ exchangeRates: rates });
    }
    this.checkUserVip();
    this.loadRebates();
  },

  checkUserVip() {
    const userInfo = app.globalData.userInfo;
    const isVip = userInfo && userInfo.role === 'vip';
    this.setData({ isVip });
  },

  loadRebates() {
    const that = this;
    const isVip = that.data.isVip;
    
    request.get('/api/rebate/list', { is_vip: isVip, page: 1, page_size: 50 }).then((data) => {
      if (data && data.list) {
        const rebates = data.list.map(r => ({
          id: r.rebate_id,
          name: r.title,
          description: r.description || '',
          brandName: r.brand_name || '',
          storeName: r.store_name || '',
          country: r.country,
          rate: r.rate,
          isVipOnly: r.is_vip_only,
          status: r.status === 'available' ? 'unused' : 'used',
          statusText: r.status === 'available' ? '领取' : '已结束',
          logo: that.getRebateLogo(r.country)
        }));
        that.setData({ rebates });
      }
    }).catch(() => {
      console.log('返点数据加载失败');
    });
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
    }).catch(() => {
      console.log('商品加载失败');
    });
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
