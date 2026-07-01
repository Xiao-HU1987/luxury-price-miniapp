const request = require('../../utils/request.js');
const { BRANDS, CATEGORIES } = require('../../utils/constants.js');
const app = getApp();

const DEFAULT_JP_RATE = 21.58;

Page({
  data: {
    searchKeyword: '',
    products: [],
    jpRateDisplay: 22,
    brands: BRANDS,
    categories: CATEGORIES,
    showBrandFilter: false,
    showCategoryFilter: false,
    selectedBrand: '',
    selectedBrandName: '',
    selectedCategory: '',
    selectedCategoryName: '',
    sortBy: 'default',
    sortLabel: '价格',
    statusBarHeight: 20
  },

  onLoad() {
    this.setData({
      statusBarHeight: app.globalData.statusBarHeight || 20
    });
    this.loadProducts();
  },

  onShow() {
    const rates = app.globalData.exchangeRates;
    if (rates && rates.rates) {
      const jpRate = rates.rates.JPY || DEFAULT_JP_RATE;
      const jpRateDisplay = Math.round(jpRate);
      if (jpRateDisplay !== this.data.jpRateDisplay) {
        this.setData({ jpRateDisplay: jpRateDisplay });
        this.loadProducts();
      }
    }
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
    
    request.get('/api/product/search', {
      page: 1, 
      page_size: 20,
      brand_id: that.data.selectedBrand || undefined,
      category_id: that.data.selectedCategory || undefined,
      keyword: that.data.searchKeyword || undefined
    }).then((data) => {
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
            brandId: p.brand_id,
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
    }).catch(() => {
      console.log('商品加载失败');
    });
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

  toggleBrandFilter() {
    this.setData({
      showBrandFilter: !this.data.showBrandFilter,
      showCategoryFilter: false
    });
  },

  toggleCategoryFilter() {
    this.setData({
      showCategoryFilter: !this.data.showCategoryFilter,
      showBrandFilter: false
    });
  },

  closeFilter() {
    this.setData({
      showBrandFilter: false,
      showCategoryFilter: false
    });
  },

  selectBrand(e) {
    const brandId = e.currentTarget.dataset.brandId;
    const brandName = e.currentTarget.dataset.brandName;
    if (this.data.selectedBrand === brandId) {
      this.setData({ selectedBrand: '', selectedBrandName: '' });
    } else {
      this.setData({ selectedBrand: brandId, selectedBrandName: brandName });
    }
  },

  selectCategory(e) {
    const categoryId = e.currentTarget.dataset.categoryId;
    const categoryName = e.currentTarget.dataset.categoryName;
    if (this.data.selectedCategory === categoryId) {
      this.setData({ selectedCategory: '', selectedCategoryName: '' });
    } else {
      this.setData({ selectedCategory: categoryId, selectedCategoryName: categoryName });
    }
  },

  confirmBrandFilter() {
    this.setData({ showBrandFilter: false });
    this.loadProducts();
  },

  confirmCategoryFilter() {
    this.setData({ showCategoryFilter: false });
    this.loadProducts();
  },

  onSortTap() {
    const sortMap = {
      'default': { next: 'price-asc', label: '价格 ↑' },
      'price-asc': { next: 'price-desc', label: '价格 ↓' },
      'price-desc': { next: 'default', label: '价格' }
    };
    const current = sortMap[this.data.sortBy];
    if (current) {
      this.setData({
        sortBy: current.next,
        sortLabel: current.label
      });
    }
  },

  goToExchange() {
    wx.switchTab({ url: '/pages/exchange/exchange' });
  }
});
