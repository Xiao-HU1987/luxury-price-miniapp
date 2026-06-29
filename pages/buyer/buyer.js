const { BUYERS, BUYER_DEMANDS, PRODUCTS } = require('../../data/mock.js');
const { BRANDS, COUNTRIES } = require('../../utils/constants.js');
const { getCountryByCode, formatTime, formatDate } = require('../../utils/util.js');

const app = getApp();

Page({
  data: {
    tab: 'buyers',
    keyword: '',
    country: '',
    buyers: [],
    allBuyers: [],
    demands: [],
    countries: COUNTRIES,
    brands: BRANDS,
    showPublish: false,
    publishForm: {
      productName: '',
      brandId: '',
      country: '',
      deadline: '',
      budget: '',
      quantity: 1,
      description: ''
    },
    minDate: '',
    userInfo: null,
    statusBarHeight: 20
  },

  onLoad() {
    this.setData({ statusBarHeight: app.globalData.statusBarHeight || 20 });
    
    this.loadBuyers();
    this.loadDemands();
    const today = new Date();
    const minDate = today.getFullYear() + '-' + 
      String(today.getMonth() + 1).padStart(2, '0') + '-' + 
      String(today.getDate()).padStart(2, '0');
    this.setData({ minDate });
  },

  onShow() {
    this.setData({ userInfo: app.globalData.userInfo });
  },

  loadBuyers() {
    const buyers = BUYERS.map(b => {
      const country = getCountryByCode(b.country);
      const specialtyNames = b.specialty.map(id => {
        const brand = BRANDS.find(br => br.id === id);
        return brand ? brand.nameCn : '';
      }).filter(Boolean);
      return {
        ...b,
        countryName: country.name,
        flag: country.flag,
        specialtyNames
      };
    });
    this.setData({
      allBuyers: buyers,
      buyers
    });
  },

  loadDemands() {
    const demands = BUYER_DEMANDS.map(d => {
      const country = getCountryByCode(d.country);
      const brand = BRANDS.find(b => b.id === d.brandId);
      return {
        ...d,
        countryName: country.name,
        flag: country.flag,
        brandName: brand ? brand.nameCn : '',
        timeAgo: formatTime(d.createTime),
        statusText: d.status === 'bidding' ? '招标中' : d.status === 'matched' ? '已匹配' : '已完成',
        statusClass: d.status === 'bidding' ? 'status-bidding' : d.status === 'matched' ? 'status-matched' : 'status-done'
      };
    });
    this.setData({ demands });
  },

  onTabTap(e) {
    this.setData({ tab: e.currentTarget.dataset.tab });
  },

  onKeywordInput(e) {
    this.setData({ keyword: e.detail.value });
    this.filterBuyers();
  },

  selectCountry(e) {
    const country = e.currentTarget.dataset.country;
    const current = this.data.country === country ? '' : country;
    this.setData({ country: current });
    this.filterBuyers();
  },

  filterBuyers() {
    const { keyword, country, allBuyers } = this.data;
    let filtered = allBuyers.filter(b => {
      if (country && b.country !== country) return false;
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
      content: buyer.intro + '\n\n服务费：' + buyer.feeRate + '%\n预计时效：' + buyer.deliveryDays + '天',
      showCancel: false
    });
  },

  onDemandTap(e) {
    const demand = e.currentTarget.dataset.demand;
    wx.showToast({
      title: '需求ID：' + demand.id,
      icon: 'none'
    });
  },

  showPublishModal() {
    this.setData({ showPublish: true });
  },

  closePublishModal() {
    this.setData({ showPublish: false });
  },

  onPublishInput(e) {
    const field = e.currentTarget.dataset.field;
    const value = e.detail.value;
    this.setData({
      [`publishForm.${field}`]: value
    });
  },

  onDateChange(e) {
    this.setData({
      'publishForm.deadline': e.detail.value
    });
  },

  selectPublishBrand(e) {
    const brandId = e.currentTarget.dataset.brandId;
    this.setData({
      'publishForm.brandId': brandId
    });
  },

  selectPublishCountry(e) {
    const country = e.currentTarget.dataset.country;
    this.setData({
      'publishForm.country': country
    });
  },

  submitPublish() {
    const form = this.data.publishForm;
    if (!form.productName) {
      wx.showToast({ title: '请填写商品名称', icon: 'none' });
      return;
    }
    if (!form.deadline) {
      wx.showToast({ title: '请选择交期时间', icon: 'none' });
      return;
    }
    wx.showToast({
      title: '发布成功',
      icon: 'success',
      duration: 2000
    });
    setTimeout(() => {
      this.setData({
        showPublish: false,
        publishForm: {
          productName: '',
          brandId: '',
          country: '',
          deadline: '',
          budget: '',
          quantity: 1,
          description: ''
        }
      });
    }, 1500);
  }
});
