const request = require('../../utils/request.js');
const { BRANDS, COUNTRIES } = require('../../utils/constants.js');
const { getCountryByCode } = require('../../utils/util.js');

const app = getApp();

Page({
  data: {
    keyword: '',
    country: '',
    buyers: [],
    allBuyers: [],
    countries: COUNTRIES,
    brands: BRANDS,
    minDate: '',
    userInfo: null,
    statusBarHeight: 20
  },

  onLoad() {
    const today = new Date();
    const minDate = today.getFullYear() + '-' + 
      String(today.getMonth() + 1).padStart(2, '0') + '-' + 
      String(today.getDate()).padStart(2, '0');
    
    this.setData({
      statusBarHeight: app.globalData.statusBarHeight || 20,
      minDate
    });
    
    this.loadBuyers();
  },

  onShow() {
    this.setData({ userInfo: app.globalData.userInfo });
    this.loadBuyers();
  },

  loadBuyers() {
    const that = this;
    const params = { page: 1, page_size: 50 };
    if (that.data.country) params.country = that.data.country;
    request.get('/api/buyer/list', params)
      .then((data) => {
        if (data && data.list) {
          const buyers = data.list.map(b => {
            const country = getCountryByCode(b.country);
            return {
              id: b.buyer_id,
              ...b,
              countryName: country ? country.name : b.country,
              flag: country ? country.flag : '',
              specialtyNames: []
            };
          });
          that.setData({
            allBuyers: buyers,
            buyers
          });
          that.filterBuyers();
        }
      })
      .catch(() => {});
  },

  onKeywordInput(e) {
    this.setData({ keyword: e.detail.value });
    this.filterBuyers();
  },

  selectCountry(e) {
    const country = e.currentTarget.dataset.country;
    const current = this.data.country === country ? '' : country;
    this.setData({ country: current });
    this.loadBuyers();
  },

  filterBuyers() {
    const { keyword, allBuyers } = this.data;
    let filtered = allBuyers.filter(b => {
      if (keyword) {
        const kw = keyword.toLowerCase();
        if (!b.name.toLowerCase().includes(kw)) return false;
      }
      return true;
    });
    this.setData({ buyers: filtered });
  },

  onBuyerTap(e) {
    const buyer = e.currentTarget.dataset.buyer;
    wx.showModal({
      title: buyer.name,
      content: buyer.intro + '\n\n预计时效：' + buyer.delivery_days + '天',
      showCancel: false
    });
  }
});
