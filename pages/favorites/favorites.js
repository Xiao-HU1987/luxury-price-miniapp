const request = require('../../utils/request.js');

const app = getApp();

Page({
  data: {
    statusBarHeight: 20,
    list: [],
    empty: true,
    loading: true
  },

  onLoad() {
    this.setData({ statusBarHeight: app.globalData.statusBarHeight || 20 });
  },

  onShow() {
    this.loadFavorites();
  },

  loadFavorites() {
    const userInfo = app.globalData.userInfo || wx.getStorageSync('userInfo') || {};
    if (!userInfo.user_id) {
      wx.showToast({ title: '请先登录', icon: 'none' });
      return;
    }

    this.setData({ loading: true });
    request.get('/api/user/favorites', { user_id: userInfo.user_id })
      .then(data => {
        const list = (data.list || []).map(item => ({
          id: item.target_id,
          name: item.target_name,
          image: item.target_image,
          type: item.target_type,
          time: this.formatTime(item.created_at)
        }));
        this.setData({
          list,
          empty: list.length === 0,
          loading: false
        });
      })
      .catch(() => {
        this.setData({ loading: false });
      });
  },

  onItemTap(e) {
    const id = e.currentTarget.dataset.id;
    const type = e.currentTarget.dataset.type;
    if (type === 'product') {
      wx.navigateTo({ url: `/pages/product-detail/product-detail?id=${id}` });
    }
  },

  onRemove(e) {
    const id = e.currentTarget.dataset.id;
    const userInfo = app.globalData.userInfo || wx.getStorageSync('userInfo') || {};
    
    wx.showModal({
      title: '提示',
      content: '确定取消收藏吗？',
      success: (res) => {
        if (res.confirm) {
          request.delete(`/api/user/favorites/${id}`, { user_id: userInfo.user_id })
            .then(() => {
              wx.showToast({ title: '已取消', icon: 'success' });
              this.loadFavorites();
            })
            .catch(() => {
              wx.showToast({ title: '操作失败', icon: 'none' });
            });
        }
      }
    });
  },

  formatTime(timeStr) {
    if (!timeStr) return '';
    const date = new Date(timeStr);
    return `${date.getMonth() + 1}/${date.getDate()} ${date.getHours()}:${String(date.getMinutes()).padStart(2, '0')}`;
  }
});
