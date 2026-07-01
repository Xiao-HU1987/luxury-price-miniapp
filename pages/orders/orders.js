const app = getApp();
const request = require('../../utils/request.js');

Page({
  data: {
    tabs: [
      { status: '', name: '全部' },
      { status: 'pending', name: '待支付' },
      { status: 'paid', name: '待发货' },
      { status: 'shipped', name: '待收货' },
      { status: 'completed', name: '已完成' }
    ],
    currentTab: '',
    orders: [],
    loading: false
  },

  onLoad(options) {
    if (options.status) {
      this.setData({ currentTab: options.status });
    }
    this.loadOrders();
  },

  onShow() {
    this.loadOrders();
  },

  switchTab(e) {
    const status = e.currentTarget.dataset.status;
    this.setData({ currentTab: status });
    this.loadOrders();
  },

  loadOrders() {
    const userInfo = app.globalData.userInfo || wx.getStorageSync('userInfo') || {};
    if (!userInfo || !userInfo.user_id) {
      this.setData({ orders: [] });
      return;
    }

    this.setData({ loading: true });
    const params = {
      user_id: userInfo.user_id,
      page: 1,
      page_size: 50
    };
    if (this.data.currentTab) {
      params.status = this.data.currentTab;
    }

    request.get('/api/order/list', params)
      .then(data => {
        const orders = (data.list || []).map(item => ({
          ...item,
          totalAmountDisplay: item.total_amount.toFixed(2)
        }));
        this.setData({ orders, loading: false });
      })
      .catch(err => {
        console.error('加载订单失败:', err);
        this.setData({ loading: false });
      });
  },

  getStatusText(status) {
    const map = {
      pending: '待支付',
      paid: '待发货',
      shipped: '待收货',
      completed: '已完成',
      cancelled: '已取消',
      refunded: '已退款'
    };
    return map[status] || status;
  },

  formatDate(dateStr) {
    if (!dateStr) return '';
    const date = new Date(dateStr);
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    const hour = String(date.getHours()).padStart(2, '0');
    const minute = String(date.getMinutes()).padStart(2, '0');
    return `${month}-${day} ${hour}:${minute}`;
  },

  goToDetail(e) {
    const orderId = e.currentTarget.dataset.orderId;
    wx.navigateTo({ url: `/pages/order-detail/order-detail?order_id=${orderId}` });
  },

  payOrder(e) {
    const orderId = e.currentTarget.dataset.orderId;
    if (!orderId) return;

    wx.showLoading({ title: '正在创建支付...' });

    request.post(`/api/order/${orderId}/pay`)
      .then(data => {
        wx.hideLoading();
        if (data && data.pay_params) {
          this.invokeWechatPay(data);
        } else {
          wx.showToast({ title: '创建支付失败', icon: 'none' });
        }
      })
      .catch(err => {
        wx.hideLoading();
        console.error('创建支付失败:', err);
        wx.showModal({
          title: '调试模式',
          content: '是否模拟支付成功？',
          confirmText: '模拟支付',
          success: (res) => {
            if (res.confirm) {
              this.mockPay(orderId);
            }
          }
        });
      });
  },

  invokeWechatPay(orderData) {
    const payParams = orderData.pay_params;
    const orderId = orderData.order_id;

    wx.requestPayment({
      timeStamp: payParams.timeStamp,
      nonceStr: payParams.nonceStr,
      package: payParams.package,
      signType: payParams.signType || 'MD5',
      paySign: payParams.paySign,
      success: () => {
        wx.showToast({ title: '支付成功', icon: 'success' });
        this.loadOrders();
      },
      fail: (err) => {
        console.error('支付失败:', err);
        if (err.errMsg && err.errMsg.indexOf('cancel') > -1) {
          wx.showToast({ title: '已取消支付', icon: 'none' });
        } else {
          this.mockPay(orderId);
        }
      }
    });
  },

  mockPay(orderId) {
    wx.showModal({
      title: '调试模式',
      content: '是否模拟支付成功？',
      confirmText: '模拟支付',
      success: (res) => {
        if (res.confirm) {
          request.post(`/api/order/mock-pay/${orderId}`)
            .then(() => {
              wx.showToast({ title: '支付成功', icon: 'success' });
              this.loadOrders();
            })
            .catch(err => {
              console.error('模拟支付失败:', err);
              wx.showToast({ title: '模拟支付失败', icon: 'none' });
            });
        }
      }
    });
  },

  viewLogistics(e) {
    const orderId = e.currentTarget.dataset.orderId;
    wx.showToast({ title: '物流功能开发中', icon: 'none' });
  },

  confirmReceive(e) {
    const orderId = e.currentTarget.dataset.orderId;
    wx.showModal({
      title: '确认收货',
      content: '确认已收到商品？',
      success: (res) => {
        if (res.confirm) {
          request.put(`/api/order/${orderId}/status?status_value=completed`)
            .then(() => {
              wx.showToast({ title: '确认成功', icon: 'success' });
              this.loadOrders();
            })
            .catch(err => {
              console.error('确认收货失败:', err);
              wx.showToast({ title: '操作失败', icon: 'none' });
            });
        }
      }
    });
  }
});
