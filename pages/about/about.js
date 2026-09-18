// 关于比惠 - 应用信息页
const app = getApp();

Page({
  data: {
    statusBarHeight: 20,
    version: '1.1.1',
    contactWeChat: 'Uncledollar',
    contactEmail: 'huxiao870823@163.com',
    appName: '比惠'
  },

  onLoad() {
    const sysInfo = wx.getSystemInfoSync();
    this.setData({ statusBarHeight: sysInfo.statusBarHeight || 20 });
    const version = (wx.getAccountInfoSync && wx.getAccountInfoSync().miniProgram && wx.getAccountInfoSync().miniProgram.version) || '1.1.1';
    this.setData({ version: version || '1.1.1' });
  },

  goBack() {
    wx.navigateBack({ delta: 1 });
  },

  onCopyWeChat() {
    const wechat = this.data.contactWeChat;
    if (wechat && wechat.indexOf('待补充') === -1) {
      wx.setClipboardData({
        data: wechat,
        success: () => wx.showToast({ title: '微信号已复制', icon: 'success' })
      });
    }
  },

  onCopyEmail() {
    wx.setClipboardData({
      data: this.data.contactEmail,
      success: () => wx.showToast({ title: '邮箱已复制', icon: 'success' })
    });
  },

  onOpenPrivacy() {
    wx.navigateTo({ url: '/pages/privacy/privacy' });
  },

  onContactTap() {
    wx.showToast({ title: '客服微信号调整中', icon: 'none' });
  }
});