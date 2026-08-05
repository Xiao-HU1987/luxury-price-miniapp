const app = getApp();
const dataService = require('../../utils/dataService.js');

Page({
  data: {
    userInfo: {},
    statusBarHeight: 20,
    favorites: [],
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
    const avatarUrl = e.detail.avatarUrl;
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
      const historyIds = hisProducts.length > 0 && typeof hisProducts[0] === 'string' ? hisProducts : hisProducts.map(p => p.productId);

      const alertsList = (alertRes && (alertRes.data || alertRes.list || alertRes)) || [];
      const alertsCount = Array.isArray(alertsList) ? alertsList.length : (alertRes.count || 0);

      const compList = (compRes && (compRes.data || compRes.list || compRes)) || [];
      const compareCount = Array.isArray(compList) ? compList.length : (compRes.count || 0);

      const localFavs = wx.getStorageSync('favorites') || [];
      const mergedFavIds = [...new Set([...localFavs, ...cloudFavIds])];
      wx.setStorageSync('favorites', mergedFavIds);

      // 如果云函数已经返回带商品详情的列表，直接使用
      let favDisplayProducts = [];
      if (isArray && favProducts.length > 0 && typeof favProducts[0] === 'object' && favProducts[0].productId) {
        const formatPrice = n => String(n || 0).replace(/\B(?=(\d{3})+(?!\d))/g, ',');
        favDisplayProducts = favProducts.map(p => ({
          productId: p.productId,
          nameCn: p.nameCn || p.displayName || p.nameJp || '',
          mainImage: p.mainImage || '',
          cnPriceStr: p.cnOfficialPrice ? formatPrice(p.cnOfficialPrice) :
                     (p.jpCnyPrice ? formatPrice(p.jpCnyPrice) :
                     (p.bestGlobalPrice ? formatPrice(p.bestGlobalPrice) : ''))
        }));
      } else {
        that.loadFavoriteDetails(mergedFavIds.slice(0, 20));
      }

      that.setData({
        favoritesCount: mergedFavIds.length,
        historyCount: historyIds.length,
        alertsCount,
        compareCount,
        favorites: favDisplayProducts,
        history: historyIds.slice(0, 10)
      });
    }).catch((err) => {
      console.warn('[profile] 加载用户数据失败', err && err.message);
      const localFavs = wx.getStorageSync('favorites') || [];
      this.loadFavoriteDetails(localFavs.slice(0, 20));
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

  loadFavoriteDetails(productIds) {
    if (!productIds || productIds.length === 0) {
      this.setData({ favorites: [] });
      return;
    }
    dataService.getProductList({ page: 1, pageSize: 50 }).then(data => {
      const allProducts = data.list || [];
      const favProducts = productIds.map(id => {
        const p = allProducts.find(item => item.productId === id);
        if (p) return {
          productId: p.productId,
          nameCn: p.nameCn,
          mainImage: p.mainImage,
          cnPriceStr: p.cnPriceStr,
          jpCnyStr: p.jpCnyStr
        };
        return { productId: id, nameCn: id, mainImage: '', placeholder: true };
      });
      this.setData({ favorites: favProducts.filter(Boolean) });
    }).catch(() => {
      const fallback = productIds.map(id => ({ productId: id, nameCn: id, mainImage: '' }));
      this.setData({ favorites: fallback });
    });
  },

  onMenuTap(e) {
    const menu = e.currentTarget.dataset.menu;
    if (menu === 'favorites') {
      if (this.data.favoritesCount === 0) {
        wx.showToast({ title: '暂无收藏', icon: 'none' });
      } else {
        wx.pageScrollTo({ selector: '#favSection', duration: 200 });
      }
    } else if (menu === 'history') {
      wx.navigateTo({ url: '/pages/history/history' });
    } else if (menu === 'compare') {
      wx.navigateTo({ url: '/pages/compare/compare' });
    } else if (menu === 'price-alerts') {
      wx.navigateTo({ url: '/pages/price-alerts/price-alerts' });
    }
  },

  scrollToFavs() {
    if (this.data.favoritesCount > 0) {
      wx.pageScrollTo({ selector: '#favSection', duration: 200 });
    }
  },

  scrollToHistory() {
    wx.showToast({ title: '即将上线', icon: 'none' });
  },

  goToDetail(e) {
    const id = e.currentTarget.dataset.id;
    if (id) {
      wx.navigateTo({ url: '/pages/product-detail/product-detail?id=' + id });
    }
  },

  onSettingTap(e) {
    const id = e.currentTarget.dataset.id;
    const map = { about: '关于比惠', feedback: '意见反馈' };
    wx.showToast({ title: map[id] || id, icon: 'none' });
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
