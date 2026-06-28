const { STORES } = require('../../data/mock.js');
const { BRANDS, COUNTRIES } = require('../../utils/constants.js');
const { getCountryByCode } = require('../../utils/util.js');

Page({
  data: {
    tab: 'mall',
    keyword: '',
    country: '',
    stores: [],
    allStores: [],
    countries: COUNTRIES,
    typeLabels: {
      mall: '商场',
      street: '专卖店街',
      dutyfree: '免税店'
    }
  },

  onLoad() {
    this.loadStores();
  },

  loadStores() {
    const stores = STORES.map(s => {
      const country = getCountryByCode(s.country);
      return {
        ...s,
        countryName: country.name,
        flag: country.flag,
        typeLabel: this.data.typeLabels[s.type] || s.type,
        brandCount: s.brands.length
      };
    });
    this.setData({
      allStores: stores,
      stores
    });
    this.filterStores();
  },

  onTabTap(e) {
    const tab = e.currentTarget.dataset.tab;
    this.setData({ tab });
    this.filterStores();
  },

  onKeywordInput(e) {
    this.setData({ keyword: e.detail.value });
    this.filterStores();
  },

  selectCountry(e) {
    const country = e.currentTarget.dataset.country;
    const current = this.data.country === country ? '' : country;
    this.setData({ country: current });
    this.filterStores();
  },

  filterStores() {
    const { tab, keyword, country, allStores } = this.data;
    let filtered = allStores.filter(s => {
      if (tab === 'mall' && s.type !== 'mall') return false;
      if (tab === 'street' && s.type !== 'street') return false;
      if (tab === 'dutyfree' && s.type !== 'dutyfree') return false;
      if (country && s.country !== country) return false;
      if (keyword) {
        const kw = keyword.toLowerCase();
        if (!s.name.toLowerCase().includes(kw) && !s.city.toLowerCase().includes(kw)) {
          return false;
        }
      }
      return true;
    });
    this.setData({ stores: filtered });
  },

  onStoreTap(e) {
    const store = e.currentTarget.dataset.store;
    wx.showToast({
      title: '查看' + store.name,
      icon: 'none'
    });
  },

  goToCoupons() {
    wx.navigateTo({ url: '/pages/coupons/coupons' });
  }
});
