const app = getApp();
const request = require('../../utils/request.js');

Page({
  data: {
    userInfo: {},
    vipExpireDate: '',
    menuItems: [
      { id: 'orders', icon: '📦', name: '我的订单', badge: 0 },
      { id: 'favorites', icon: '❤️', name: '我的收藏', badge: 0 },
      { id: 'history', icon: '🕐', name: '浏览历史', badge: 0 },
      { id: 'demands', icon: '📋', name: '我的需求', badge: 0 },
      { id: 'coupons', icon: '🎫', name: '我的优惠券', badge: 0 }
    ],
    settings: [
      { id: 'notification', icon: '🔔', name: '消息通知' },
      { id: 'currency', icon: '💱', name: '默认货币' },
      { id: 'privacy', icon: '🔒', name: '隐私政策' },
      { id: 'about', icon: 'ℹ️', name: '关于我们' },
      { id: 'feedback', icon: '📝', name: '意见反馈' }
    ],
    statusBarHeight: 20
  },

  onLoad() {
    this.setData({ statusBarHeight: app.globalData.statusBarHeight || 20 });
  },

  onShow() {
    const userInfo = app.globalData.userInfo || wx.getStorageSync('userInfo') || {};
    let vipExpireDate = '';
    if (userInfo.vip_expire_time) {
      vipExpireDate = this.formatVipDate(userInfo.vip_expire_time);
    }
    this.setData({ userInfo, vipExpireDate });
    this.loadUserData();
  },

  formatVipDate(dateStr) {
    if (!dateStr) return '';
    const date = new Date(dateStr);
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    return `${year}.${month}.${day}`;
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

  onChooseAvatar(e) {
    if (!e.detail || !e.detail.avatarUrl) return;
    const avatar = e.detail.avatarUrl;
    this.updateProfile({ avatar });
  },

  onNicknameConfirm(e) {
    const nickname = e.detail.value && e.detail.value.trim();
    if (!nickname) return;
    this.updateProfile({ nickname });
  },

  updateProfile(data) {
    const token = wx.getStorageSync('token');
    const userInfo = { ...this.data.userInfo, ...data };

    app.globalData.userInfo = userInfo;
    wx.setStorageSync('userInfo', userInfo);
    this.setData({ userInfo });

    if (!token) {
      wx.showToast({ title: '保存成功', icon: 'success' });
      return;
    }

    wx.showLoading({ title: '保存中...' });
    request.put('/api/user/profile', data)
      .then((res) => {
        wx.hideLoading();
        wx.showToast({ title: '保存成功', icon: 'success' });
      })
      .catch((err) => {
        wx.hideLoading();
        wx.showToast({ title: '保存失败', icon: 'none' });
      });
  },

  onGetPhone(e) {
    if (e.detail.errMsg !== 'getPhoneNumber:ok') {
      return;
    }

    const token = wx.getStorageSync('token');
    const sessionKey = wx.getStorageSync('sessionKey') || '';

    if (!token) {
      wx.showToast({ title: '请先登录', icon: 'none' });
      return;
    }

    request.put('/api/user/phone', {
      encrypted_data: e.detail.encryptedData,
      iv: e.detail.iv,
      session_key: sessionKey
    })
      .then((data) => {
        const userInfo = { ...this.data.userInfo, phone: data.phone };
        app.globalData.userInfo = userInfo;
        wx.setStorageSync('userInfo', userInfo);
        this.setData({ userInfo });
        wx.showToast({ title: '手机号绑定成功', icon: 'success' });
      })
      .catch((err) => {
        wx.showToast({ title: '手机号绑定失败', icon: 'none' });
      });
  },

  goToVip() {
    wx.navigateTo({ url: '/pages/vip/vip' });
  },

  onMenuTap(e) {
    const id = e.currentTarget.dataset.id;
    const userInfo = app.globalData.userInfo || wx.getStorageSync('userInfo') || {};
    
    if (!userInfo.user_id) {
      wx.showToast({ title: '请先登录', icon: 'none' });
      return;
    }
    
    const urlMap = {
      orders: '/pages/orders/orders',
      favorites: '/pages/favorites/favorites',
      history: '/pages/history/history',
      demands: '/pages/my-demands/my-demands',
      coupons: '/pages/my-coupons/my-coupons'
    };
    
    const url = urlMap[id];
    if (url) {
      wx.navigateTo({ url });
    }
  },

  onSettingTap(e) {
    const id = e.currentTarget.dataset.id;
    if (id === 'privacy') {
      wx.navigateTo({ url: '/pages/privacy/privacy' });
      return;
    }
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
    if (this.data.userInfo && this.data.userInfo.user_id) {
      wx.setClipboardData({
        data: this.data.userInfo.user_id,
        success: () => {
          wx.showToast({ title: 'ID已复制', icon: 'success' });
        }
      });
    }
  }
});