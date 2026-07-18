Component({
  data: {
    selected: 0,
    list: [
      {
        pagePath: '/pages/index/index',
        text: '比价',
        icon: 'compare'
      },
      {
        pagePath: '/pages/exchange/exchange',
        text: '汇率',
        icon: 'exchange'
      },
      {
        pagePath: '/pages/rebate/rebate',
        text: '优惠',
        icon: 'coupon'
      },
      {
        pagePath: '/pages/profile/profile',
        text: '我的',
        icon: 'profile'
      }
    ]
  },
  methods: {
    switchTab(e) {
      const { index, url } = e.currentTarget.dataset;
      wx.switchTab({ url });
    }
  }
});
