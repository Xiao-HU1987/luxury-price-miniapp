const { PRODUCTS } = require('../../data/mock.js');
const { BRANDS, COUNTRIES } = require('../../utils/constants.js');
const { formatPrice, convertCurrency } = require('../../utils/util.js');

const app = getApp();

Page({
  data: {
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
    currentSortLabel: '价格从低到高'
  },

  onLoad(options) {
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
    let results = PRODUCTS.filter(p => {
      if (brandId && p.brandId !== brandId) return false;
      if (category && p.category !== category) return false;
      if (keyword) {
        const kw = keyword.toLowerCase();
        const matchName = p.name.toLowerCase().includes(kw) ||
          (p.nameEn && p.nameEn.toLowerCase().includes(kw));
        const matchBrand = p.brandName.toLowerCase().includes(kw);
        if (!matchName && !matchBrand) return false;
      }
      if (country) {
        const hasCountry = p.skus.some(sku => sku.prices[country]);
        if (!hasCountry) return false;
      }
      return true;
    });

    const processed = results.map(p => {
      const allPrices = [];
      p.skus.forEach(sku => {
        Object.keys(sku.prices).forEach(code => {
          const priceInfo = sku.prices[code];
          allPrices.push({
            ...priceInfo,
            country: code,
            skuId: sku.id,
            skuName: sku.name
          });
        });
      });

      let lowest = null;
      let lowestCny = Infinity;
      if (exchangeRates && exchangeRates.rates) {
        allPrices.forEach(p => {
          const cny = convertCurrency(p.price, p.currency, 'CNY', exchangeRates);
          if (cny < lowestCny) {
            lowestCny = cny;
            lowest = { ...p, cnyPrice: cny };
          }
        });
      } else {
        lowest = allPrices[0] || null;
      }

      const countrySet = new Set();
      allPrices.forEach(p => countrySet.add(p.country));

      return {
        id: p.id,
        brandId: p.brandId,
        brandName: p.brandName,
        name: p.name,
        nameEn: p.nameEn,
        image: '',
        lowestPrice: lowest ? lowest.price : 0,
        lowestCurrency: lowest ? lowest.currency : 'CNY',
        lowestCountry: lowest ? lowest.country : '',
        lowestCny: lowestCny,
        skuCount: p.skus.length,
        countryCount: countrySet.size
      };
    });

    if (sortBy === 'price-low') {
      processed.sort((a, b) => a.lowestCny - b.lowestCny);
    } else if (sortBy === 'price-high') {
      processed.sort((a, b) => b.lowestCny - a.lowestCny);
    } else if (sortBy === 'country-count') {
      processed.sort((a, b) => b.countryCount - a.countryCount);
    }

    this.setData({ products: processed });
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
