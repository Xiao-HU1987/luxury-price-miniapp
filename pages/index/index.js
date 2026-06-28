const { PRODUCTS } = require('../../data/mock.js');
const { BRANDS, CATEGORIES, COUNTRIES } = require('../../utils/constants.js');
const { convertCurrency } = require('../../utils/util.js');

const app = getApp();

Page({
  data: {
    searchKeyword: '',
    products: [],
    exchangeRates: null,
    jpRate: 21.58,
    brands: BRANDS,
    categories: CATEGORIES,
    showBrandFilter: false,
    showCategoryFilter: false,
    selectedBrand: '',
    selectedBrandName: '',
    selectedCategory: '',
    selectedCategoryName: '',
    sortBy: 'default',
    sortLabel: '价格'
  },

  onLoad() {
    this.loadData();
  },

  onShow() {
    const rates = app.globalData.exchangeRates;
    if (rates) {
      this.setData({
        exchangeRates: rates,
        jpRate: rates.rates.JPY || 21.58
      });
      this.loadData();
    }
  },

  loadData() {
    const rates = this.data.exchangeRates;
    const jpRate = rates && rates.rates ? (rates.rates.JPY || 21.58) : 21.58;
    const jpRateDisplay = Math.round(jpRate);

    const products = PRODUCTS.map(p => {
      const firstSku = p.skus[0];
      const prices = firstSku.prices;
      const cnPrice = prices.CN ? prices.CN.price : 0;
      const jpPriceYen = prices.JP ? prices.JP.price : 0;
      let jpPriceCny = 0;
      if (jpPriceYen > 0 && rates && rates.rates) {
        jpPriceCny = convertCurrency(jpPriceYen, 'JPY', 'CNY', rates);
      } else if (jpPriceYen > 0) {
        jpPriceCny = Math.round(jpPriceYen / jpRate);
      }

      return {
        id: p.id,
        brandId: p.brandId,
        brandName: p.brandName,
        name: p.name,
        articleNo: p.articleNo || '',
        image: '',
        cnPrice: cnPrice,
        cnPriceStr: cnPrice.toLocaleString(),
        jpPriceCny: jpPriceCny,
        jpPriceCnyStr: jpPriceCny.toLocaleString(),
        hasJpPrice: jpPriceYen > 0
      };
    });

    this.setData({ products, jpRateDisplay });
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
  },

  confirmCategoryFilter() {
    this.setData({ showCategoryFilter: false });
  },

  onSortTap() {
    const sortMap = {
      'default': { next: 'price-asc', label: '价格 ↑' },
      'price-asc': { next: 'price-desc', label: '价格 ↓' },
      'price-desc': { next: 'default', label: '价格' }
    };
    const current = sortMap[this.data.sortBy];
    this.setData({
      sortBy: current.next,
      sortLabel: current.label
    });
  },

  goToExchange() {
    wx.switchTab({ url: '/pages/exchange/exchange' });
  }
});
