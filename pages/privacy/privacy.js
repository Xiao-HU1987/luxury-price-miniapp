const app = getApp();

Page({
  data: {
    statusBarHeight: 20
  },

  onLoad() {
    this.setData({ statusBarHeight: app.globalData.statusBarHeight || 20 });
  },

  goBack() {
    wx.navigateBack({
      delta: 1,
      fail: () => {
        wx.switchTab({ url: '/pages/profile/profile' });
      }
    });
  }
});