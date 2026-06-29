const { COUPONS } = require('../../data/mock.js');
const { COUNTRIES } = require('../../utils/constants.js');
const { getCountryByCode } = require('../../utils/util.js');
const app = getApp();

Page({
  data: {
    coupons: [],
    filteredCoupons: [],
    country: '',
    countries: COUNTRIES,
    tab: 'available',
    statusBarHeight: 20
  },

  onLoad() {
    this.setData({ statusBarHeight: app.globalData.statusBarHeight || 20 });
    this.loadCoupons();
  },

  loadCoupons() {
    const coupons = COUPONS.map(c => {
      const country = getCountryByCode(c.country);
      return {
        ...c,
        countryName: country.name,
        flag: country.flag,
        currencySymbol: country.currencySymbol
      };
    });
    this.setData({ coupons });
    this.updateFilteredCoupons();
  },

  updateFilteredCoupons() {
    const { coupons, country, tab } = this.data;
    const filtered = coupons.filter(c => {
      if (country && c.country !== country) return false;
      if (tab === 'available' && c.status !== 'available') return false;
      return true;
    });
    this.setData({ filteredCoupons: filtered });
  },

  onTabTap(e) {
    const tab = e.currentTarget.dataset.tab;
    this.setData({ tab });
    this.updateFilteredCoupons();
  },

  selectCountry(e) {
    const country = e.currentTarget.dataset.country;
    const current = this.data.country === country ? '' : country;
    this.setData({ country: current });
    this.updateFilteredCoupons();
  },

  claimCoupon(e) {
    const id = e.currentTarget.dataset.id;
    wx.showToast({
      title: '领取成功',
      icon: 'success'
    });
  }
});
