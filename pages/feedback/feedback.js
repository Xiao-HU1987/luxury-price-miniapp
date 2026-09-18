// 意见反馈页 - 提交用户反馈到云数据库
const dataService = require('../../utils/dataService.js');

Page({
  data: {
    statusBarHeight: 20,
    content: '',
    contact: '',
    submitting: false
  },

  onLoad() {
    const sysInfo = wx.getSystemInfoSync();
    this.setData({ statusBarHeight: sysInfo.statusBarHeight || 20 });
    // 尝试读取用户微信号（从用户信息里没有，仅预填联系方式占位）
    const userInfo = wx.getStorageSync('userInfo') || {};
    if (userInfo.contact) {
      this.setData({ contact: userInfo.contact });
    }
  },

  goBack() {
    wx.navigateBack({ delta: 1 });
  },

  onContentInput(e) {
    this.setData({ content: e.detail.value });
  },

  onContactInput(e) {
    this.setData({ contact: e.detail.value });
  },

  onSubmit() {
    const content = (this.data.content || '').trim();
    const contact = (this.data.contact || '').trim();

    if (!content) {
      wx.showToast({ title: '请填写反馈内容', icon: 'none' });
      return;
    }
    if (!contact) {
      wx.showToast({ title: '请填写您的微信号', icon: 'none' });
      return;
    }

    this.setData({ submitting: true });

    // 通过 userAction 云函数提交反馈（写入 user_feedback 集合）
    if (wx.cloud && wx.cloud.callFunction) {
      wx.cloud.callFunction({
        name: 'userAction',
        data: { action: 'submitFeedback', content, contact }
      }).then(res => {
        this.setData({ submitting: false });
        if (res.result && res.result.code === 0) {
          wx.showToast({ title: '提交成功，感谢反馈', icon: 'success' });
          setTimeout(() => {
            wx.navigateBack({ delta: 1 });
          }, 1200);
        } else {
          wx.showToast({ title: (res.result && res.result.message) || '提交失败，请重试', icon: 'none' });
        }
      }).catch(() => {
        this.setData({ submitting: false });
        wx.showToast({ title: '提交失败，请检查网络', icon: 'none' });
      });
    } else {
      this.setData({ submitting: false });
      wx.showToast({ title: '云服务不可用', icon: 'none' });
    }
  }
});