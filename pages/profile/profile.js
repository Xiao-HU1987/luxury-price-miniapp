const app = getApp();

Page({
  data: {
    userInfo: null,
    menuItems: [
      { id: 'favorites', icon: '❤️', name: '我的收藏', badge: 0 },
      { id: 'history', icon: '🕐', name: '浏览历史', badge: 0 },
      { id: 'demands', icon: '📋', name: '我的需求', badge: 0 },
      { id: 'coupons', icon: '🎫', name: '我的优惠券', badge: 0 }
    ],
    settings: [
      { id: 'notification', icon: '🔔', name: '消息通知' },
      { id: 'currency', icon: '💱', name: '默认货币' },
      { id: 'about', icon: 'ℹ️', name: '关于我们' },
      { id: 'feedback', icon: '📝', name: '意见反馈' }
    ]
  },

  onShow() {
    const userInfo = app.globalData.userInfo || wx.getStorageSync('userInfo');
    this.setData({ userInfo });
    this.loadUserData();
  },

  loadUserData() {
    const favorites = wx.getStorageSync('favorites') || [];
    const history = wx.getStorageSync('browseHistory') || [];
    const demands = wx.getStorageSync('myDemands') || [];
    const myCoupons = wx.getStorageSync('myCoupons') || [];
    const menuItems = this.data.menuItems.map(item => {
      if (item.id === 'favorites') return { ...item, badge: favorites.length };
      if (item.id === 'history') return { ...item, badge: history.length };
      if (item.id === 'demands') return { ...item, badge: demands.length };
      if (item.id === 'coupons') return { ...item, badge: myCoupons.length };
      return item;
    });
    this.setData({ menuItems });
  },

  onEditProfile() {
    wx.showToast({ title: '编辑资料', icon: 'none' });
  },

  onMenuTap(e) {
    const id = e.currentTarget.dataset.id;
    const map = {
      favorites: '我的收藏',
      history: '浏览历史',
      demands: '我的需求',
      coupons: '我的优惠券'
    };
    wx.showToast({
      title: map[id] || id,
      icon: 'none'
    });
  },

  onSettingTap(e) {
    const id = e.currentTarget.dataset.id;
    const map = {
      notification: '消息通知',
      currency: '默认货币',
      about: '关于我们',
      feedback: '意见反馈'
    };
    wx.showToast({
      title: map[id] || id,
      icon: 'none'
    });
  },

  copyUserId() {
    if (this.data.userInfo && this.data.userInfo.userId) {
      wx.setClipboardData({
        data: this.data.userInfo.userId,
        success: () => {
          wx.showToast({ title: 'ID已复制', icon: 'success' });
        }
      });
    }
  }
});
