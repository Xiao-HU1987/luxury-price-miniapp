// 启动页 - 展示Logo或广告后跳转首页
Page({
  data: {
    statusBarHeight: 20
  },

  onLoad() {
    const sysInfo = wx.getSystemInfoSync();
    this.setData({ statusBarHeight: sysInfo.statusBarHeight || 20 });
    // 2秒后跳转首页
    setTimeout(() => {
      wx.switchTab({ url: '/pages/index/index' });
    }, 2000);
  }
});
