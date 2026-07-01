const { COUNTRIES } = require('../../utils/constants.js');
const { getCountryByCode } = require('../../utils/util.js');
const request = require('../../utils/request.js');
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

  onShow() {
    this.loadCoupons();
  },

  loadCoupons() {
    const that = this;
    request.get('/api/coupon/list', { page: 1, page_size: 100 })
      .then((data) => {
        if (data && data.list) {
          const coupons = data.list.map(c => {
            const country = getCountryByCode(c.country);
            return {
              ...c,
              id: c.coupon_id,
              countryName: country ? country.name : c.country,
              flag: country ? country.flag : '',
              currencySymbol: country ? country.currencySymbol : ''
            };
          });
          that.setData({ coupons });
          that.updateFilteredCoupons();
        }
      })
      .catch(() => {
        wx.showToast({ title: '加载失败', icon: 'error' });
      });
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
    const couponId = e.currentTarget.dataset.id;
    const userInfo = app.globalData.userInfo || wx.getStorageSync('userInfo') || {};
    if (!userInfo.user_id) {
      wx.showToast({ title: '请先登录', icon: 'none' });
      return;
    }

    const that = this;
    request.post('/api/user/my-coupons/claim', { coupon_id: couponId })
      .then(() => {
        wx.showToast({ title: '领取成功', icon: 'success' });
        that.loadCoupons();
      })
      .catch(err => {
        wx.showToast({
          title: err?.message || '领取失败',
          icon: 'none'
        });
      });
  }
});
