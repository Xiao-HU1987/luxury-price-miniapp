// 意见反馈页 - 提交用户反馈到云数据库
Page({
  data: {
    statusBarHeight: 20,
    content: '',
    submitting: false
  },

  onLoad() {
    const sysInfo = wx.getSystemInfoSync();
    this.setData({ statusBarHeight: sysInfo.statusBarHeight || 20 });
  },

  goBack() {
    wx.navigateBack({ delta: 1 });
  },

  onContentInput(e) {
    this.setData({ content: e.detail.value });
  },

  onSubmit() {
    const content = (this.data.content || '').trim();

    if (!content) {
      wx.showToast({ title: '请填写反馈内容', icon: 'none' });
      return;
    }

    this.setData({ submitting: true });

    // 通过 userAction 云函数提交反馈（写入 user_feedback 集合）
    if (wx.cloud && wx.cloud.callFunction) {
      wx.cloud.callFunction({
        name: 'userAction',
        data: { action: 'submitFeedback', content }
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