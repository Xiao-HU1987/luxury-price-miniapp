const request = require('../../utils/request.js');
const { BRANDS, COUNTRIES } = require('../../utils/constants.js');
const { getCountryByCode } = require('../../utils/util.js');
const app = getApp();

Page({
  data: {
    tab: 'mall',
    statusBarHeight: 20,
    keyword: '',
    country: '',
    stores: [],
    allStores: [],
    countries: COUNTRIES,
    typeLabels: {
      mall: '商场',
      store: '专卖店',
      dutyfree: '免税店'
    }
  },

  onLoad() {
    this.setData({ statusBarHeight: app.globalData.statusBarHeight || 20 });
    this.loadStores();
  },

  onShow() {
    this.loadStores();
  },

  loadStores() {
    const that = this;
    const typeMap = { mall: 'mall', street: 'store', dutyfree: 'dutyfree' };
    const type = typeMap[that.data.tab] || '';
    
    request.get('/api/store/list', { 
      page: 1, 
      page_size: 100,
      country: that.data.country || undefined,
      type: type || undefined
    }).then((data) => {
      if (data && data.list) {
        const stores = data.list.map(s => {
          const country = getCountryByCode(s.country);
          return {
            id: s.store_id,
            ...s,
            countryName: country ? country.name : s.country,
            flag: country ? country.flag : '',
            typeLabel: that.data.typeLabels[s.type] || s.type,
            brandCount: 0
          };
        });
        that.setData({
          allStores: stores,
          stores
        });
        that.filterStores();
      }
    }).catch(() => {
      console.log('店铺加载失败');
    });
  },

  onTabTap(e) {
    const tab = e.currentTarget.dataset.tab;
    this.setData({ tab });
    this.loadStores();
  },

  onKeywordInput(e) {
    this.setData({ keyword: e.detail.value });
    this.filterStores();
  },

  selectCountry(e) {
    const country = e.currentTarget.dataset.country;
    const current = this.data.country === country ? '' : country;
    this.setData({ country: current });
    this.loadStores();
  },

  filterStores() {
    const { keyword, allStores } = this.data;
    let filtered = allStores.filter(s => {
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
