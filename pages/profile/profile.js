const app = getApp();
const dataService = require('../../utils/dataService.js');
const versionInfo = require('../../utils/version.js');

Page({
  data: {
    userInfo: {},
    statusBarHeight: 20,
    appName: versionInfo.appName,
    version: versionInfo.version,
    history: [],
    favoritesCount: 0,
    historyCount: 0,
    alertsCount: 0,
    compareCount: 0,
    isLoggedIn: false,
    loading: false
  },

  onLoad() {
    this.setData({ statusBarHeight: app.globalData.statusBarHeight || 20 });

    // 计算头部安全下移量：状态栏高度 + 胶囊高度 + 间距（避开右上角胶囊）
    let headerPaddingTop = 32;
    try {
      const menuBtn = wx.getMenuButtonBoundingClientRect();
      const statusBarHeight = app.globalData.statusBarHeight || 20;
      if (menuBtn && menuBtn.height) {
        // 胶囊底部 + 外边距，作为内容区起始点
        headerPaddingTop = Math.ceil(menuBtn.bottom + 8);
      } else {
        headerPaddingTop = statusBarHeight + 32;
      }
    } catch (e) {
      headerPaddingTop = 32;
    }
    this.setData({ headerPaddingTop });

    this.checkLoginStatus();
  },

  onShow() {
    if (typeof this.getTabBar === 'function' && this.getTabBar()) {
      this.getTabBar().setData({ selected: 3 });
    }
    this.checkLoginStatus();
  },

  checkLoginStatus() {
    const userInfo = wx.getStorageSync('userInfo') || {};
    const isLoggedIn = !!(userInfo.user_id && userInfo.user_id.length > 0);
    this.setData({ userInfo, isLoggedIn });
    if (isLoggedIn) {
      this.loadUserData();
    } else {
      // 未登录也展示本地缓存的收藏（本地收藏不依赖登录）
      this.loadLocalFavorites();
    }
  },

  // 未登录时读取本地收藏数量
  loadLocalFavorites() {
    const localFavs = wx.getStorageSync('favorites') || [];
    this.setData({ favoritesCount: localFavs.length });
  },

  // 登录成功后：把游客期间的本地浏览历史迁移到当前账号 key，避免数据丢失
  _migrateGuestHistory(userId) {
    try {
      const guestKey = 'viewHistoryLocal:guest';
      const guestHistory = wx.getStorageSync(guestKey) || [];
      const guestMetaKey = guestKey + ':meta';
      const guestMeta = wx.getStorageSync(guestMetaKey) || {};
      if (guestHistory.length === 0) return;

      const userKey = 'viewHistoryLocal:' + userId;
      const userHistory = wx.getStorageSync(userKey) || [];
      const merged = [...new Set([...guestHistory, ...userHistory])].slice(0, 50);
      wx.setStorageSync(userKey, merged);

      // 合并商品简要信息
      const userMetaKey = userKey + ':meta';
      const userMeta = wx.getStorageSync(userMetaKey) || {};
      wx.setStorageSync(userMetaKey, { ...guestMeta, ...userMeta });

      // 迁移后仍保留 guest 缓存（切换到游客态时还能看），但优先放账号 key
    } catch (e) {
      console.warn('[profile] 迁移游客历史失败', e);
    }
  },

  onLoginTap() {
    wx.showLoading({ title: '登录中...', mask: true });
    wx.login({
      success: (res) => {
        if (res.code) {
          wx.cloud.callFunction({
            name: 'userAction',
            data: { action: 'getProfile' }
          }).then(result => {
            wx.hideLoading();
            if (result.result && result.result.code === 0) {
              const openId = result.result._openid || '';
              const userInfo = {
                user_id: 'BH' + openId.slice(-8).toUpperCase(),
                nickname: '',
                avatarUrl: '',
                loginTime: Date.now()
              };
              // 迁移游客期的本地浏览历史到新账号（保证重登录不丢失）
              this._migrateGuestHistory(userInfo.user_id);
              wx.setStorageSync('userInfo', userInfo);
              app.globalData.userInfo = userInfo;
              this.setData({ userInfo, isLoggedIn: true });
              wx.showToast({ title: '登录成功', icon: 'success' });
              this.loadUserData();
            } else {
              wx.showToast({ title: '登录失败', icon: 'none' });
            }
          }).catch(() => {
            wx.hideLoading();
            wx.showToast({ title: '登录失败', icon: 'none' });
          });
        } else {
          wx.hideLoading();
          wx.showToast({ title: '登录失败', icon: 'none' });
        }
      },
      fail: () => {
        wx.hideLoading();
        wx.showToast({ title: '登录失败', icon: 'none' });
      }
    });
  },

  onChooseAvatar(e) {
    // 防抖：避免连点导致 chooseAvatar 并发冲突
    if (this._isChoosingAvatar) return;
    this._isChoosingAvatar = true;
    setTimeout(() => { this._isChoosingAvatar = false; }, 1500);

    const avatarUrl = e.detail && e.detail.avatarUrl;
    if (!avatarUrl) {
      // 用户取消选择，静默处理（不弹错误提示）
      return;
    }
    const userInfo = { ...this.data.userInfo, avatarUrl };
    wx.setStorageSync('userInfo', userInfo);
    app.globalData.userInfo = userInfo;
    this.setData({ userInfo });
    this.saveUserProfile();
  },

  onNicknameConfirm(e) {
    const nickname = (e.detail.value || '').trim();
    if (!nickname) return;
    const userInfo = { ...this.data.userInfo, nickname };
    wx.setStorageSync('userInfo', userInfo);
    app.globalData.userInfo = userInfo;
    this.setData({ userInfo });
    this.saveUserProfile();
  },

  saveUserProfile() {
    if (!this.data.userInfo.user_id) return;
    wx.cloud.callFunction({
      name: 'userAction',
      data: {
        action: 'updateSettings',
        settings: {
          nickname: this.data.userInfo.nickname,
          avatarUrl: this.data.userInfo.avatarUrl
        }
      }
    }).catch(() => {});
  },

  loadUserData() {
    this.setData({ loading: true });
    const that = this;

    Promise.all([
      dataService.getFavorites(),
      dataService.getHistory(),
      dataService.getPriceAlerts(),
      dataService.getCompareList()
    ]).then(([favRes, hisRes, alertRes, compRes]) => {
      // getFavorites 现在直接返回商品数据列表
      const favProducts = (favRes && (favRes.data || favRes.list || favRes)) || [];
      const isArray = Array.isArray(favProducts);
      const cloudFavIds = isArray ? (favProducts.length > 0 && typeof favProducts[0] === 'string' ? favProducts : favProducts.map(p => p.productId)) : [];
      const cloudHistory = (hisRes && (hisRes.data || hisRes.list || hisRes)) || [];
      const hisProducts = Array.isArray(cloudHistory) ? cloudHistory : [];
      const cloudHistoryIds = hisProducts.length > 0 && typeof hisProducts[0] === 'string' ? hisProducts : hisProducts.map(p => p.productId);

      const alertsList = (alertRes && (alertRes.data || alertRes.list || alertRes)) || [];
      const alertsCount = Array.isArray(alertsList) ? alertsList.length : (alertRes.count || 0);

      const compList = (compRes && (compRes.data || compRes.list || compRes)) || [];
      const compareCount = Array.isArray(compList) ? compList.length : (compRes.count || 0);

      const localFavs = wx.getStorageSync('favorites') || [];
      const mergedFavIds = [...new Set([...localFavs, ...cloudFavIds])];
      wx.setStorageSync('favorites', mergedFavIds);

      // 浏览历史：合并本地缓存（游客期间记录的）与云端，保证重登录不丢失
      const userInfo = wx.getStorageSync('userInfo') || {};
      const historyKey = 'viewHistoryLocal:' + (userInfo.user_id || 'guest');
      const localHistory = wx.getStorageSync(historyKey) || [];
      const mergedHistoryIds = [...new Set([...localHistory, ...cloudHistoryIds])];
      wx.setStorageSync(historyKey, mergedHistoryIds);

      // 登录后把本地（含游客期）数据批量合并到云端，保证重登录数据留存
      if (wx.cloud && wx.cloud.callFunction) {
        if (mergedHistoryIds.length > 0 && localHistory.length > 0) {
          wx.cloud.callFunction({
            name: 'userAction',
            data: { action: 'syncHistory', productIds: localHistory }
          }).catch(() => {});
        }
        if (mergedFavIds.length > 0 && localFavs.length > 0) {
          wx.cloud.callFunction({
            name: 'userAction',
            data: { action: 'syncFavorites', productIds: localFavs }
          }).catch(() => {});
        }
      }

      that.setData({
        favoritesCount: mergedFavIds.length,
        historyCount: mergedHistoryIds.length,
        alertsCount,
        compareCount,
        history: mergedHistoryIds.slice(0, 10)
      });
    }).catch((err) => {
      console.warn('[profile] 加载用户数据失败', err && err.message);
      const localFavs = wx.getStorageSync('favorites') || [];
      this.setData({
        favoritesCount: localFavs.length,
        historyCount: 0,
        alertsCount: 0,
        compareCount: 0,
        history: []
      });
    }).finally(() => {
      this.setData({ loading: false });
    });
  },

  onMenuTap(e) {
    const menu = e.currentTarget.dataset.menu;
    if (menu === 'favorites') {
      this.goToFavorites();
    } else if (menu === 'history') {
      wx.navigateTo({ url: '/pages/history/history' });
    } else if (menu === 'compare') {
      wx.navigateTo({ url: '/pages/compare/compare' });
    } else if (menu === 'price-alerts') {
      wx.navigateTo({ url: '/pages/price-alerts/price-alerts' });
    }
  },

  // 跳转独立收藏页
  goToFavorites() {
    wx.navigateTo({ url: '/pages/favorites/favorites' });
  },

  scrollToHistory() {
    wx.showToast({ title: '即将上线', icon: 'none' });
  },

  onSettingTap(e) {
    const id = e.currentTarget.dataset.id;
    if (id === 'about') {
      wx.navigateTo({ url: '/pages/about/about' });
    } else if (id === 'feedback') {
      wx.navigateTo({ url: '/pages/feedback/feedback' });
    }
  },

  copyUserId() {
    if (this.data.userInfo && this.data.userInfo.user_id) {
      wx.setClipboardData({
        data: this.data.userInfo.user_id,
        success: () => wx.showToast({ title: 'ID已复制', icon: 'success' })
      });
    }
  }
});
