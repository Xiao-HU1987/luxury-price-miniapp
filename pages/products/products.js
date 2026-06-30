const { BRANDS, COUNTRIES } = require('../../utils/constants.js');
const { convertCurrency } = require('../../utils/util.js');
const request = require('../../utils/request.js');

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
    brands: BRANDS,
    countries: COUNTRIES,
    sortOptions: [
      { value: 'price-low', label: '价格从低到高' },
      { value: 'price-high', label: '价格从高到低' },
      { value: 'country-count', label: '比价国家多' }
    ],
    currentSortLabel: '价格从低到高',
    loading: false
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
    this.searchProducts();
  },

  onShow() {
    const rates = app.globalData.exchangeRates;
    if (rates) {
      this.setData({ exchangeRates: rates });
      this.searchProducts();
    }
  },

  onKeywordInput(e) {
    this.setData({ keyword: e.detail.value });
  },

  onSearch() {
    this.searchProducts();
  },

  searchProducts() {
    const { keyword, brandId, category, country, sortBy, exchangeRates } = this.data;
    
    this.setData({ loading: true });
    const params = {
      page: 1,
      page_size: 50
    };
    if (keyword) params.keyword = keyword;
    if (brandId) params.brand_id = brandId;
    if (category) params.category_id = category;
    if (country) params.country = country;

    request.get('/api/product/search', params)
      .then((res) => {
        const list = res.list || [];
        const processed = list.map(p => {
          let lowestCny = Infinity;
          let lowestCurrency = 'CNY';
          let lowestCountry = '';
          
          if (exchangeRates && exchangeRates.rates && p.min_price) {
            if (p.countries && p.countries.length > 0) {
              for (let i = 0; i < p.countries.length; i++) {
                const c = p.countries[i];
                const rate = exchangeRates.rates[c];
                if (rate) {
                  const cny = p.min_price / rate;
                  if (cny < lowestCny) {
                    lowestCny = cny;
                    lowestCurrency = c;
                    lowestCountry = c;
                  }
                }
              }
            }
          }
          
          if (lowestCny === Infinity) lowestCny = 0;

          return {
            id: p.spu_id,
            brandId: p.brand_id,
            brandName: p.brand_name,
            name: p.name,
            nameEn: p.name_en,
            image: p.image || '',
            lowestPrice: p.min_price || 0,
            lowestCurrency: lowestCurrency,
            lowestCountry: lowestCountry,
            lowestCny: lowestCny,
            lowestCnyDisplay: Math.round(lowestCny).toString(),
            countryCount: p.countries ? p.countries.length : 0
          };
        });

        if (sortBy === 'price-low') {
          processed.sort((a, b) => a.lowestCny - b.lowestCny);
        } else if (sortBy === 'price-high') {
          processed.sort((a, b) => b.lowestCny - a.lowestCny);
        } else if (sortBy === 'country-count') {
          processed.sort((a, b) => b.countryCount - a.countryCount);
        }

        this.setData({ products: processed, loading: false });
      })
      .catch((err) => {
        console.error('搜索商品失败:', err);
        this.setData({ loading: false });
        wx.showToast({ title: '加载失败', icon: 'none' });
      });
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
  }
});
