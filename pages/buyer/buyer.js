const request = require('../../utils/request.js');
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
    if (this.data.tab === 'buyers') {
      this.loadBuyers();
    } else {
      this.loadDemands();
    }
  },

  loadBuyers() {
    const that = this;
    request.get('/api/buyer/list', { 
      page: 1, 
      page_size: 50,
      country: that.data.country || undefined
    })
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
      .catch(() => {
        console.log('买手加载失败');
      });
  },

  loadDemands() {
    const that = this;
    
    request.get('/api/demand/list', { page: 1, page_size: 20 })
      .then((data) => {
        if (data && data.list) {
          const demands = data.list.map(d => {
            const country = getCountryByCode(d.country);
            const brand = BRANDS.find(b => b.id === d.brand_id);
            const statusText = d.status === 'bidding' ? '招标中' : d.status === 'matched' ? '已匹配' : '已完成';
            const statusClass = d.status === 'bidding' ? 'status-bidding' : d.status === 'matched' ? 'status-matched' : 'status-done';
            return {
              id: d.demand_id,
              ...d,
              countryName: country ? country.name : d.country,
              flag: country ? country.flag : '',
              brandName: brand ? brand.nameCn : (d.brand_id || ''),
              timeAgo: d.created_at ? formatTime(new Date(d.created_at).getTime()) : '',
              statusText,
              statusClass
            };
          });
          that.setData({ demands });
        }
      })
      .catch(() => {
        console.log('需求加载失败');
      });
  },

  onTabTap(e) {
    const tab = e.currentTarget.dataset.tab;
    this.setData({ tab });
    if (tab === 'buyers') {
      this.loadBuyers();
    } else {
      this.loadDemands();
    }
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
      content: buyer.intro + '\n\n服务费：' + buyer.fee_rate + '%\n预计时效：' + buyer.delivery_days + '天',
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
    const that = this;
    const form = that.data.publishForm;
    const userInfo = app.globalData.userInfo || wx.getStorageSync('userInfo') || {};

    if (!userInfo.user_id) {
      wx.showToast({ title: '请先登录', icon: 'none' });
      return;
    }
    if (!form.productName) {
      wx.showToast({ title: '请填写商品名称', icon: 'none' });
      return;
    }
    if (!form.deadline) {
      wx.showToast({ title: '请选择交期时间', icon: 'none' });
      return;
    }

    const demandId = 'DEM' + Date.now();

    request.post('/api/demand', {
      demand_id: demandId,
      user_id: userInfo.user_id,
      product_name: form.productName,
      brand_id: form.brandId || '',
      country: form.country || '',
      deadline: form.deadline,
      budget: parseFloat(form.budget) || 0,
      budget_currency: 'CNY',
      quantity: form.quantity,
      description: form.description || ''
    })
      .then(() => {
        wx.showToast({
          title: '发布成功',
          icon: 'success',
          duration: 2000
        });
        setTimeout(() => {
          that.setData({
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
          that.loadDemands();
        }, 1500);
      })
      .catch((err) => {
        wx.showToast({ title: err?.message || '发布失败', icon: 'none' });
      });
  }
});
