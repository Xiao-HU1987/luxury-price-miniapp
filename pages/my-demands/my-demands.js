const request = require('../../utils/request.js');

const app = getApp();

Page({
  data: {
    statusBarHeight: 20,
    list: [],
    empty: true,
    loading: true,
    tabs: [
      { key: 'all', name: '全部' },
      { key: 'bidding', name: '招标中' },
      { key: 'matched', name: '已匹配' },
      { key: 'completed', name: '已完成' }
    ],
    tab: 'all'
  },

  onLoad() {
    this.setData({ statusBarHeight: app.globalData.statusBarHeight || 20 });
  },

  onShow() {
    this.loadDemands();
  },

  loadDemands() {
    const userInfo = app.globalData.userInfo || wx.getStorageSync('userInfo') || {};
    if (!userInfo.user_id) {
      wx.showToast({ title: '请先登录', icon: 'none' });
      return;
    }

    this.setData({ loading: true });
    request.get('/api/demand/list', {
      page: 1,
      page_size: 100,
      user_id: userInfo.user_id
    })
      .then(data => {
        const list = (data.list || []).map(item => ({
          id: item.demand_id,
          productName: item.product_name,
          brandId: item.brand_id,
          country: item.country,
          budget: item.budget,
          quantity: item.quantity,
          deadline: item.deadline,
          status: item.status,
          buyerName: item.buyer_name || '',
          time: this.formatTime(item.created_at)
        }));
        
        let filtered = list;
        if (this.data.tab !== 'all') {
          filtered = list.filter(item => item.status === this.data.tab);
        }
        
        this.setData({
          list: filtered,
          empty: filtered.length === 0,
          loading: false
        });
      })
      .catch(() => {
        this.setData({ loading: false });
      });
  },

  onTabTap(e) {
    const tab = e.currentTarget.dataset.tab;
    this.setData({ tab });
    this.loadDemands();
  },

  formatTime(timeStr) {
    if (!timeStr) return '';
    const date = new Date(timeStr);
    return `${date.getMonth() + 1}/${date.getDate()} ${date.getHours()}:${String(date.getMinutes()).padStart(2, '0')}`;
  },

  getStatusText(status) {
    const map = {
      bidding: '招标中',
      matched: '已匹配买手',
      completed: '已完成'
    };
    return map[status] || status;
  },

  getStatusColor(status) {
    const map = {
      bidding: '#ff9800',
      matched: '#4caf50',
      completed: '#9e9e9e'
    };
    return map[status] || '#999';
  }
});
