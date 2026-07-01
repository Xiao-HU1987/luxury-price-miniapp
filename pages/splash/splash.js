const request = require('../../utils/request.js');

Page({
  data: {
    adData: null,
    countdown: 5,
    timer: null,
    hasShown: false,
    adRecorded: false
  },

  onLoad() {
    this.loadSplashAd();
  },

  onUnload() {
    this.clearTimer();
  },

  getUserId() {
    try {
      const userInfo = wx.getStorageSync('userInfo');
      if (userInfo && userInfo.id) {
        return String(userInfo.id);
      }
    } catch (e) {}
    return '';
  },

  getTodayKey() {
    const now = new Date();
    const year = now.getFullYear();
    const month = String(now.getMonth() + 1).padStart(2, '0');
    const day = String(now.getDate()).padStart(2, '0');
    return `${year}${month}${day}`;
  },

  checkDailyLimit(adId) {
    try {
      const todayKey = this.getTodayKey();
      const cacheKey = `splash_ad_${adId}_${todayKey}`;
      const count = wx.getStorageSync(cacheKey) || 0;
      const dailyLimit = this.data.adData?.daily_limit || 1;
      if (dailyLimit > 0 && count >= dailyLimit) {
        return false;
      }
      return true;
    } catch (e) {
      return true;
    }
  },

  incrementShowCount(adId) {
    try {
      const todayKey = this.getTodayKey();
      const cacheKey = `splash_ad_${adId}_${todayKey}`;
      const count = wx.getStorageSync(cacheKey) || 0;
      wx.setStorageSync(cacheKey, count + 1);
    } catch (e) {}
  },

  loadSplashAd() {
    const userId = this.getUserId();
    const params = {};
    if (userId) {
      params.user_id = userId;
    }

    request.get('/api/splash-ad/current', params)
      .then(data => {
        if (data && data.id && data.is_active) {
          const canShow = this.checkDailyLimit(data.id);
          if (canShow) {
            this.setData({
              adData: data,
              countdown: data.duration || 5
            });
            this.startCountdown();
          } else {
            this.goToHome();
          }
        } else {
          this.goToHome();
        }
      })
      .catch(err => {
        console.warn('获取开屏广告失败:', err?.message || err);
        this.goToHome();
      });
  },

  startCountdown() {
    this.clearTimer();
    
    if (this.data.adData && !this.data.adRecorded) {
      this.recordShow();
      this.incrementShowCount(this.data.adData.id);
      this.setData({ adRecorded: true });
    }

    this.data.timer = setInterval(() => {
      let countdown = this.data.countdown - 1;
      if (countdown <= 0) {
        this.clearTimer();
        this.goToHome();
      } else {
        this.setData({ countdown });
      }
    }, 1000);
  },

  clearTimer() {
    if (this.data.timer) {
      clearInterval(this.data.timer);
      this.data.timer = null;
    }
  },

  recordShow() {
    if (!this.data.adData) return;
    
    const adId = this.data.adData.id;
    const userId = this.getUserId();
    let url = `/api/splash-ad/${adId}/show`;
    if (userId) {
      url += `?user_id=${encodeURIComponent(userId)}`;
    }

    request.post(url, {})
      .catch(err => {
        console.error('记录广告展示失败:', err);
      });
  },

  recordClick() {
    if (!this.data.adData) return;
    
    const adId = this.data.adData.id;
    const userId = this.getUserId();
    let url = `/api/splash-ad/${adId}/click`;
    if (userId) {
      url += `?user_id=${encodeURIComponent(userId)}`;
    }

    request.post(url, {})
      .catch(err => {
        console.error('记录广告点击失败:', err);
      });
  },

  onSkip() {
    this.clearTimer();
    this.goToHome();
  },

  onAdClick() {
    if (!this.data.adData) return;
    
    const linkType = this.data.adData.link_type;
    if (!linkType || linkType === 'none') {
      return;
    }

    this.recordClick();

    if (linkType === 'page') {
      const linkPage = this.data.adData.link_page;
      if (linkPage) {
        this.clearTimer();
        wx.navigateTo({
          url: linkPage,
          fail: () => {
            wx.switchTab({
              url: linkPage,
              fail: () => {
                this.goToHome();
              }
            });
          }
        });
      }
    } else if (linkType === 'url') {
      const linkUrl = this.data.adData.link_url;
      if (linkUrl) {
        wx.setClipboardData({
          data: linkUrl,
          success: () => {
            wx.showToast({
              title: '链接已复制',
              icon: 'success'
            });
          }
        });
      }
    }
  },

  goToHome() {
    this.clearTimer();
    wx.switchTab({
      url: '/pages/index/index',
      fail: () => {
        wx.reLaunch({
          url: '/pages/index/index'
        });
      }
    });
  }
});
