const request = require('../../utils/request.js');

const app = getApp();

Page({
  data: {
    statusBarHeight: 20,
    tab: 'available',
    list: [],
    empty: true,
    loading: true,
    tabs: [
      { key: 'available', name: '可用' },
      { key: 'used', name: '已使用' },
      { key: 'expired', name: '已过期' }
    ]
  },

  onLoad() {
    this.setData({ statusBarHeight: app.globalData.statusBarHeight || 20 });
  },

  onShow() {
    this.loadCoupons();
  },

  loadCoupons() {
    const userInfo = app.globalData.userInfo || wx.getStorageSync('userInfo') || {};
    if (!userInfo.user_id) {
      wx.showToast({ title: '请先登录', icon: 'none' });
      return;
    }

    this.setData({ loading: true });
    request.get('/api/user/my-coupons', {
      user_id: userInfo.user_id,
      status: this.data.tab === 'available' ? null : this.data.tab
    })
      .then(data => {
        const list = (data.list || []).map(item => ({
          id: item.coupon_id,
          userCouponId: item.user_coupon_id,
          title: item.title,
          type: item.type,
          discount: item.discount,
          minAmount: item.min_amount,
          country: item.country,
          storeName: item.store_name,
          status: item.status,
          time: this.formatTime(item.obtained_at)
        }));
        this.setData({
          list,
          empty: list.length === 0,
          loading: false
        });
      })
      .catch(() => {
        this.setData({ loading: false });
      });
  },

  onTabTap(e) {
    const tab = e.currentTarget.dataset.tab;
    this.setData({ tab });
    this.loadCoupons();
  },

  getCouponDesc(coupon) {
    if (coupon.type === 'discount') {
      return `满${coupon.minAmount}元减${coupon.discount}元`;
    } else if (coupon.type === 'percent') {
      return `${coupon.discount}折优惠`;
    }
    return `${coupon.discount}元优惠券`;
  },

  formatTime(timeStr) {
    if (!timeStr) return '';
    const date = new Date(timeStr);
    return `${date.getFullYear()}/${date.getMonth() + 1}/${date.getDate()}`;
  }
});
