const request = require('../../utils/request.js');
const { COUNTRIES } = require('../../utils/constants.js');
const { convertCurrency } = require('../../utils/util.js');

const app = getApp();

Page({
  data: {
    statusBarHeight: 20,
    keyword: '',
    brandId: '',
    category: '',
    country: '',
    sortBy: 'price-low',
    products: [],
    exchangeRates: null,
    showFilter: false,
    brands: [],
    countries: COUNTRIES,
    sortOptions: [
      { value: 'price-low', label: '价格从低到高' },
      { value: 'price-high', label: '价格从高到低' }
    ],
    currentSortLabel: '价格从低到高'
  },

  onLoad(options) {
    this.setData({ statusBarHeight: app.globalData.statusBarHeight || 20 });
    const keyword = options.keyword || '';
    const brandId = options.brandId || '';
    const category = options.category || '';
    this.setData({
      keyword: decodeURIComponent(keyword),
      brandId,
      category
    });
    this.loadBrands();
    this.searchProducts();
  },

  loadBrands() {
    const that = this;
    request.get('/api/product/brands').then(data => {
      if (data && Array.isArray(data)) {
        const brands = data.map(b => ({
          id: b.brand_id,
          name: b.name,
          nameCn: b.name_cn,
          logo: b.logo
        }));
        that.setData({ brands });
      }
    }).catch(() => {});
  },

  onShow() {
    const rates = app.globalData.exchangeRates;
    if (rates) {
      this.setData({ exchangeRates: rates });
    }
    this.searchProducts();
  },

  onKeywordInput(e) {
    this.setData({ keyword: e.detail.value });
  },

  onSearch() {
    this.searchProducts();
  },

  searchProducts() {
    const that = this;
    const { keyword, brandId, category, country, sortBy } = this.data;

    const params = { page: 1, page_size: 50 };
    if (keyword) params.keyword = keyword;
    if (brandId) params.brand_id = brandId;
    if (category) params.category_id = category;
    if (country) params.country = country;
    request.get('/api/product/search', params).then((data) => {
      if (data && data.list) {
        const rates = that.data.exchangeRates;
        let processed = data.list.map(p => {
          const cnPrice = p.min_cn_price || 0;
          const jpPrice = p.min_jp_price || 0;
          
          let lowestCny = cnPrice > 0 ? cnPrice : Infinity;
          let lowestPrice = cnPrice;
          let lowestCurrency = 'CNY';
          let lowestCountry = 'CN';
          
          if (rates && rates.rates && jpPrice > 0) {
            const jpCny = jpPrice / (rates.rates.JPY || 1);
            if (jpCny < lowestCny) {
              lowestCny = jpCny;
              lowestPrice = jpPrice;
              lowestCurrency = 'JPY';
              lowestCountry = 'JP';
            }
          }
          
          if (lowestCny === Infinity) lowestCny = 0;
          
          return {
            id: p.spu_id,
            brandId: p.brand_id,
            brandName: p.brand_name,
            name: p.name_cn || p.name || p.name_en || '',
            nameEn: p.name,
            image: p.image || '',
            lowestPrice: lowestPrice,
            lowestCurrency: lowestCurrency,
            lowestCountry: lowestCountry,
            lowestCny: lowestCny,
            lowestCnyDisplay: Math.round(lowestCny).toString(),
            skuCount: p.sku_count || 0,
            countryCount: p.country_count || 0
          };
        });
        
        if (sortBy === 'price-low') {
          processed.sort((a, b) => a.lowestCny - b.lowestCny);
        } else if (sortBy === 'price-high') {
          processed.sort((a, b) => b.lowestCny - a.lowestCny);
        }
        
        that.setData({ products: processed });
      }
    }).catch(() => {});
  },

  onProductTap(e) {
    const id = e.currentTarget.dataset.id;
    wx.navigateTo({
      url: '/pages/product-detail/product-detail?id=' + id
    });
  },

  toggleFilter() {
    this.setData({ showFilter: !this.data.showFilter });
  },

  closeFilter() {
    this.setData({ showFilter: false });
  },

  selectBrand(e) {
    const brandId = e.currentTarget.dataset.brandId;
    const current = this.data.brandId === brandId ? '' : brandId;
    this.setData({ brandId: current });
  },

  selectCountry(e) {
    const country = e.currentTarget.dataset.country;
    const current = this.data.country === country ? '' : country;
    this.setData({ country: current });
  },

  selectSort(e) {
    const value = e.currentTarget.dataset.value;
    const option = this.data.sortOptions.find(o => o.value === value);
    this.setData({
      sortBy: value,
      currentSortLabel: option ? option.label : ''
    });
    this.searchProducts();
  },

  applyFilter() {
    this.setData({ showFilter: false });
    this.searchProducts();
  },

  resetFilter() {
    this.setData({
      brandId: '',
      country: '',
      sortBy: 'price-low',
      currentSortLabel: '价格从低到高'
    });
    this.searchProducts();
  },

  goBack() {
    wx.navigateBack({ delta: 1 });
  }
});
