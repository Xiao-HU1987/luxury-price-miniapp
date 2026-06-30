const { BRANDS, COUNTRIES } = require('../../utils/constants.js');
const { getCountryByCode, formatTime, formatDate } = require('../../utils/util.js');
const request = require('../../utils/request.js');

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
    statusBarHeight: 20,
    loading: false
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
    this.setData({ loading: true });
    request.get('/api/buyer/list', { page: 1, page_size: 50 })
      .then((res) => {
        const list = res.list || [];
        const buyers = list.map(b => {
          const country = getCountryByCode(b.country);
          return {
            id: b.buyer_id,
            buyer_id: b.buyer_id,
            name: b.name,
            avatar: b.avatar,
            country: b.country,
            city: b.city,
            rating: b.rating,
            orders: b.orders,
            feeRate: b.fee_rate,
            deliveryDays: b.delivery_days,
            intro: b.intro,
            specialty: [],
            countryName: country.name,
            flag: country.flag,
            specialtyNames: []
          };
        });
        this.setData({
          allBuyers: buyers,
          buyers,
          loading: false
        });
      })
      .catch((err) => {
        console.error('加载买手列表失败:', err);
        this.setData({ loading: false });
      });
  },

  loadDemands() {
    request.get('/api/demand/list', { page: 1, page_size: 50 })
      .then((res) => {
        const list = res.list || [];
        const demands = list.map(d => {
          const country = getCountryByCode(d.country);
          const brand = BRANDS.find(b => b.id === d.brand_id);
          return {
            id: d.demand_id,
            demand_id: d.demand_id,
            userId: d.user_id,
            productName: d.product_name,
            brandId: d.brand_id,
            country: d.country,
            deadline: d.deadline,
            budget: d.budget,
            budgetCurrency: d.budget_currency,
            quantity: d.quantity,
            status: d.status,
            bids: d.bids,
            matchedBuyer: d.matched_buyer_id,
            createTime: d.created_at,
            description: d.description,
            countryName: country.name,
            flag: country.flag,
            brandName: brand ? brand.nameCn : '',
            timeAgo: d.created_at ? formatTime(d.created_at) : '',
            statusText: d.status === 'bidding' ? '招标中' : d.status === 'matched' ? '已匹配' : '已完成',
            statusClass: d.status === 'bidding' ? 'status-bidding' : d.status === 'matched' ? 'status-matched' : 'status-done'
          };
        });
        this.setData({ demands });
      })
      .catch((err) => {
        console.error('加载需求列表失败:', err);
      });
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

    const that = this;
    const demandId = 'demand_' + Date.now();
    const userId = app.globalData.userInfo && app.globalData.userInfo.userId ? app.globalData.userInfo.userId : 'user_default';

    wx.showLoading({ title: '发布中...' });
    request.post('/api/demand', {
      demand_id: demandId,
      user_id: userId,
      product_name: form.productName,
      brand_id: form.brandId,
      country: form.country,
      deadline: form.deadline,
      budget: parseFloat(form.budget) || 0,
      budget_currency: 'CNY',
      quantity: form.quantity || 1,
      description: form.description
    })
      .then(() => {
        wx.hideLoading();
        wx.showToast({
          title: '发布成功',
          icon: 'success',
          duration: 2000
        });
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
      })
      .catch((err) => {
        wx.hideLoading();
        console.error('发布需求失败:', err);
        wx.showToast({ title: '发布失败', icon: 'none' });
      });
  }
});
