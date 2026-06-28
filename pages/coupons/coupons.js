const { COUPONS, STORES } = require('../../data/mock.js');
const { COUNTRIES } = require('../../utils/constants.js');
const { getCountryByCode } = require('../../utils/util.js');

Page({
  data: {
    coupons: [],
    country: '',
    countries: COUNTRIES,
    tab: 'available'
  },

  onLoad() {
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
  },

  onTabTap(e) {
    const tab = e.currentTarget.dataset.tab;
    this.setData({ tab });
  },

  selectCountry(e) {
    const country = e.currentTarget.dataset.country;
    const current = this.data.country === country ? '' : country;
    this.setData({ country: current });
  },

  claimCoupon(e) {
    const id = e.currentTarget.dataset.id;
    wx.showToast({
      title: '领取成功',
      icon: 'success'
    });
  },

  getFilteredCoupons() {
    const { coupons, country, tab } = this.data;
    return coupons.filter(c => {
      if (country && c.country !== country) return false;
      if (tab === 'available' && c.status !== 'available') return false;
      return true;
    });
  }
});
