const request = require('../../utils/request.js');
const app = getApp();

const DEFAULT_JP_RATE = 21.58;

Page({
  data: {
    searchKeyword: '',
    products: [],
    statusBarHeight: 20,
    menuButtonRight: 0,
    menuButtonWidth: 0
  },

  onLoad() {
    const sysInfo = wx.getSystemInfoSync();
    const statusBarHeight = sysInfo.statusBarHeight || 20;
    
    const menuButton = wx.getMenuButtonBoundingClientRect();
    const menuButtonRight = menuButton ? (sysInfo.windowWidth - menuButton.right) : 0;
    const menuButtonWidth = menuButton ? menuButton.width : 0;
    
    this.setData({
      statusBarHeight: statusBarHeight,
      menuButtonRight: menuButtonRight,
      menuButtonWidth: menuButtonWidth
    });
    this.loadProducts();
  },

  onShow() {
    if (typeof this.getTabBar === 'function' && this.getTabBar()) {
      this.getTabBar().setData({ selected: 0 });
    }
    this.loadProducts();
  },

  getJpRate() {
    const rates = app.globalData.exchangeRates;
    if (rates && rates.rates && rates.rates.JPY) {
      return rates.rates.JPY;
    }
    return DEFAULT_JP_RATE;
  },

  loadProducts() {
    const that = this;
    const jpRate = this.getJpRate();

    request.get('/api/product/search', { page: 1, page_size: 20 }).then((data) => {
      if (data && data.list) {
        const products = data.list.map(p => {
          const cnPrice = p.min_cn_price || 0;
          const jpPriceYen = p.min_jp_price || 0;
          let jpPriceCny = 0;
          if (jpPriceYen > 0) {
            jpPriceCny = Math.round(jpPriceYen / jpRate);
          }
          return {
            id: p.spu_id,
            brandName: p.brand_name,
            name: p.name || p.name_cn,
            articleNo: p.article_no || '',
            cnPriceStr: String(cnPrice).replace(/\B(?=(\d{3})+(?!\d))/g, ','),
            jpPriceCnyStr: String(jpPriceCny).replace(/\B(?=(\d{3})+(?!\d))/g, ','),
            hasJpPrice: jpPriceYen > 0
          };
        });
        that.setData({ products });
      }
    }).catch(() => {});
  },

  onSearchInput(e) {
    this.setData({ searchKeyword: e.detail.value });
  },

  onSearch() {
    const keyword = this.data.searchKeyword.trim();
    if (!keyword) return;
    wx.navigateTo({
      url: '/pages/products/products?keyword=' + encodeURIComponent(keyword)
    });
  },

  onProductTap(e) {
    const productId = e.currentTarget.dataset.productId;
    wx.navigateTo({
      url: '/pages/product-detail/product-detail?id=' + productId
    });
  },

  goToProducts() {
    wx.navigateTo({ url: '/pages/products/products' });
  }
});
