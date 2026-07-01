const app = getApp();
const request = require('../../utils/request.js');

Page({
  data: {
    orderId: '',
    order: {},
    statusText: '',
    statusIcon: ''
  },

  onLoad(options) {
    if (options.order_id) {
      this.setData({ orderId: options.order_id });
      this.loadOrderDetail(options.order_id);
    }
  },

  onShow() {
    if (this.data.orderId) {
      this.loadOrderDetail(this.data.orderId);
    }
  },

  loadOrderDetail(orderId) {
    request.get(`/api/order/${orderId}`)
      .then(data => {
        const order = {
          ...data,
          cnyPriceDisplay: (data.cny_price || 0).toFixed(2),
          feeAmountDisplay: (data.fee_amount || 0).toFixed(2),
          shippingFeeDisplay: (data.shipping_fee || 0).toFixed(2),
          totalAmountDisplay: (data.total_amount || 0).toFixed(2)
        };
        const statusMap = {
          pending: { text: '待支付', icon: '⏰' },
          paid: { text: '待发货', icon: '💳' },
          shipped: { text: '待收货', icon: '🚚' },
          completed: { text: '已完成', icon: '✅' },
          cancelled: { text: '已取消', icon: '❌' },
          refunded: { text: '已退款', icon: '↩️' }
        };
        const info = statusMap[order.status] || { text: order.status, icon: '📋' };
        this.setData({
          order,
          statusText: info.text,
          statusIcon: info.icon
        });
      })
      .catch(err => {
        console.error('加载订单详情失败:', err);
        wx.showToast({ title: '加载失败', icon: 'none' });
      });
  },

  formatDateTime(dateStr) {
    if (!dateStr) return '';
    const date = new Date(dateStr);
    const y = date.getFullYear();
    const m = String(date.getMonth() + 1).padStart(2, '0');
    const d = String(date.getDate()).padStart(2, '0');
    const h = String(date.getHours()).padStart(2, '0');
    const mi = String(date.getMinutes()).padStart(2, '0');
    return `${y}-${m}-${d} ${h}:${mi}`;
  },

  payOrder() {
    const orderId = this.data.orderId;
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
        this.loadOrderDetail(orderId);
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
    request.post(`/api/order/mock-pay/${orderId}`)
      .then(() => {
        wx.showToast({ title: '支付成功', icon: 'success' });
        this.loadOrderDetail(orderId);
      })
      .catch(err => {
        console.error('模拟支付失败:', err);
        wx.showToast({ title: '模拟支付失败', icon: 'none' });
      });
  },

  confirmReceive() {
    wx.showModal({
      title: '确认收货',
      content: '确认已收到商品？',
      success: (res) => {
        if (res.confirm) {
          request.put(`/api/order/${this.data.orderId}/status?status_value=completed`)
            .then(() => {
              wx.showToast({ title: '确认成功', icon: 'success' });
              this.loadOrderDetail(this.data.orderId);
            })
            .catch(err => {
              console.error('确认收货失败:', err);
              wx.showToast({ title: '操作失败', icon: 'none' });
            });
        }
      }
    });
  },

  cancelOrder() {
    wx.showModal({
      title: '取消订单',
      content: '确认取消此订单？',
      success: (res) => {
        if (res.confirm) {
          request.put(`/api/order/${this.data.orderId}/status?status_value=cancelled`)
            .then(() => {
              wx.showToast({ title: '已取消', icon: 'success' });
              this.loadOrderDetail(this.data.orderId);
            })
            .catch(err => {
              console.error('取消订单失败:', err);
              wx.showToast({ title: '操作失败', icon: 'none' });
            });
        }
      }
    });
  }
});
