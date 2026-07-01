const app = getApp();
const request = require('../../utils/request.js');

Page({
  data: {
    isVip: false,
    vipExpireDate: '',
    plans: [],
    selectedPlan: 'VIP_QUARTER',
    paying: false
  },

  onLoad() {
    this.loadUserInfo();
    this.loadVipPlans();
  },

  onShow() {
    this.loadUserInfo();
  },

  loadUserInfo() {
    const userInfo = app.globalData.userInfo || wx.getStorageSync('userInfo') || {};
    const isVip = userInfo.is_vip || false;
    let vipExpireDate = '';
    if (userInfo.vip_expire_time) {
      vipExpireDate = this.formatDate(userInfo.vip_expire_time);
    }
    this.setData({ isVip, vipExpireDate });
  },

  formatDate(dateStr) {
    if (!dateStr) return '';
    const date = new Date(dateStr);
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    return `${year}.${month}.${day}`;
  },

  loadVipPlans() {
    request.get('/api/vip/plans')
      .then(data => {
        const plans = (data || []).map(item => ({
          ...item,
          priceDisplay: item.price.toFixed(2),
          originalPriceDisplay: item.original_price.toFixed(2)
        }));
        this.setData({ plans });
        if (plans.length > 0 && !this.data.selectedPlan) {
          const popular = plans.find(p => p.is_popular);
          this.setData({ selectedPlan: popular ? popular.plan_id : plans[0].plan_id });
        }
      })
      .catch(err => {
        console.error('加载VIP套餐失败:', err);
        wx.showToast({ title: '加载失败', icon: 'none' });
      });
  },

  selectPlan(e) {
    const plan = e.currentTarget.dataset.plan;
    if (plan && plan.plan_id) {
      this.setData({ selectedPlan: plan.plan_id });
    }
  },

  handlePay() {
    const { selectedPlan, paying } = this.data;
    if (paying) return;
    if (!selectedPlan) {
      wx.showToast({ title: '请选择套餐', icon: 'none' });
      return;
    }

    const userInfo = app.globalData.userInfo || wx.getStorageSync('userInfo') || {};
    if (!userInfo || !userInfo.user_id) {
      wx.showToast({ title: '请先登录', icon: 'none' });
      return;
    }

    this.setData({ paying: true });
    wx.showLoading({ title: '正在创建订单...' });

    request.post('/api/vip/order', { plan_id: selectedPlan })
      .then(data => {
        wx.hideLoading();
        if (data && data.pay_params) {
          this.invokeWechatPay(data);
        } else {
          wx.showToast({ title: '创建订单失败', icon: 'none' });
          this.setData({ paying: false });
        }
      })
      .catch(err => {
        wx.hideLoading();
        console.error('创建订单失败:', err);
        wx.showToast({ title: err.message || '创建订单失败', icon: 'none' });
        this.setData({ paying: false });
      });
  },

  invokeWechatPay(orderData) {
    const payParams = orderData.pay_params;
    const orderNo = orderData.order_no;

    wx.requestPayment({
      timeStamp: payParams.timeStamp,
      nonceStr: payParams.nonceStr,
      package: payParams.package,
      signType: payParams.signType || 'MD5',
      paySign: payParams.paySign,
      success: () => {
        this.onPaySuccess(orderNo);
      },
      fail: (err) => {
        console.error('支付失败:', err);
        if (err.errMsg && err.errMsg.indexOf('cancel') > -1) {
          wx.showToast({ title: '已取消支付', icon: 'none' });
        } else {
          this.mockPay(orderNo);
        }
        this.setData({ paying: false });
      }
    });
  },

  mockPay(orderNo) {
    wx.showModal({
      title: '调试模式',
      content: '是否模拟支付成功？',
      confirmText: '模拟支付',
      success: (res) => {
        if (res.confirm) {
          request.post(`/api/vip/mock-pay/${orderNo}`)
            .then(data => {
              this.onPaySuccess(orderNo, data);
            })
            .catch(err => {
              console.error('模拟支付失败:', err);
              wx.showToast({ title: '模拟支付失败', icon: 'none' });
              this.setData({ paying: false });
            });
        }
      }
    });
  },

  onPaySuccess(orderNo, data) {
    wx.showToast({ title: '支付成功', icon: 'success' });
    
    const userInfo = app.globalData.userInfo || wx.getStorageSync('userInfo') || {};
    userInfo.is_vip = true;
    if (data && data.vip_expire_time) {
      userInfo.vip_expire_time = data.vip_expire_time;
    }
    app.globalData.userInfo = userInfo;
    wx.setStorageSync('userInfo', userInfo);
    
    setTimeout(() => {
      this.loadUserInfo();
      this.setData({ paying: false });
    }, 1500);
  }
});
