const { convertCurrency } = require('../../utils/util.js');
const request = require('../../utils/request.js');
const app = getApp();

const DEFAULT_JP_RATE = 21.58;

Page({
  data: {
    jpCoupons: [
      {
        id: 'jp001',
        name: '近铁百货返点二维码(6/10-28)',
        description: '免税+当天返3.1%(LV卡地亚等可用)',
        logo: '🚇',
        status: 'used',
        statusText: '使用'
      },
      {
        id: 'jp002',
        name: '近铁百货9折黑卡(白金卡)',
        description: '',
        logo: '🃏',
        status: 'unused',
        statusText: '领取'
      },
      {
        id: 'jp003',
        name: 'Bic Camera',
        description: '最大17%折扣+免税',
        logo: '📷',
        status: 'used',
        statusText: '使用'
      },
      {
        id: 'jp004',
        name: '日本威士忌LINXAS 大阪',
        description: '当天返现5%+免税',
        logo: '🥃',
        status: 'used',
        statusText: '使用'
      }
    ],
    cnCoupons: [
      {
        id: 'cn001',
        name: 'Gucci返现(广州K11店)',
        description: '当天返现2%',
        logo: 'G',
        status: 'used',
        statusText: '使用'
      }
    ],
    products: [],
    exchangeRates: null,
    statusBarHeight: 20,
    loading: false
  },

  onLoad() {
    this.setData({ statusBarHeight: app.globalData.statusBarHeight || 20 });
    this.loadCoupons();
    this.loadProducts();
  },

  onShow() {
    const rates = app.globalData.exchangeRates;
    if (rates) {
      this.setData({ exchangeRates: rates });
      this.loadProducts();
    }
  },

  loadCoupons() {
    const that = this;
    request.get('/api/coupon/list', { page: 1, page_size: 50, status: 'active' })
      .then((res) => {
        const list = res.list || [];
        const jpCoupons = [];
        const cnCoupons = [];
        
        list.forEach(c => {
          const coupon = {
            id: c.coupon_id,
            name: c.title,
            description: c.description || '',
            logo: c.store_name ? c.store_name.charAt(0) : '🎫',
            status: 'used',
            statusText: '使用',
            discount: c.discount,
            threshold: c.threshold,
            type: c.type,
            storeName: c.store_name
          };
          
          if (c.country === 'JP') {
            jpCoupons.push(coupon);
          } else if (c.country === 'CN') {
            cnCoupons.push(coupon);
          }
        });

        that.setData({
          jpCoupons: jpCoupons.length > 0 ? jpCoupons : that.data.jpCoupons,
          cnCoupons: cnCoupons.length > 0 ? cnCoupons : that.data.cnCoupons
        });
      })
      .catch((err) => {
        console.error('加载优惠券失败:', err);
      });
  },

  loadProducts() {
    const rates = this.data.exchangeRates;
    
    this.setData({ loading: true });
    request.get('/api/product/search', { page: 1, page_size: 3 })
      .then((res) => {
        const list = res.list || [];
        const products = list.map(p => {
          let cnPrice = 0;
          let jpPriceYen = 0;
          
          if (p.countries && p.countries.includes('CN')) {
            cnPrice = p.min_price || 0;
          }
          if (p.countries && p.countries.includes('JP')) {
            jpPriceYen = p.max_price || 0;
          }

          let jpPriceCny = 0;
          if (jpPriceYen > 0 && rates && rates.rates) {
            jpPriceCny = Math.round(convertCurrency(jpPriceYen, 'JPY', 'CNY', rates));
          }

          return {
            id: p.spu_id,
            name: p.name,
            articleNo: p.article_no || '',
            cnPrice: cnPrice,
            cnPriceStr: String(Math.round(cnPrice)).replace(/\B(?=(\d{3})+(?!\d))/g, ','),
            jpPriceCny: jpPriceCny,
            jpPriceCnyStr: String(jpPriceCny).replace(/\B(?=(\d{3})+(?!\d))/g, ','),
            hasJpPrice: p.countries && p.countries.includes('JP')
          };
        });

        this.setData({ products, loading: false });
      })
      .catch((err) => {
        console.error('加载商品失败:', err);
        this.setData({ loading: false });
      });
  },

  onCouponTap(e) {
    const coupon = e.currentTarget.dataset.coupon;
    if (coupon.status === 'unused') {
      wx.showToast({ title: '已领取', icon: 'success' });
    } else {
      wx.showToast({ title: '使用中', icon: 'none' });
    }
  },

  onProductTap(e) {
    const productId = e.currentTarget.dataset.productId;
    wx.navigateTo({
      url: '/pages/product-detail/product-detail?id=' + productId
    });
  },

  goToMoreProducts() {
    wx.switchTab({ url: '/pages/index/index' });
  },

  goToExchange() {
    wx.switchTab({ url: '/pages/exchange/exchange' });
  },

  goToBuyer() {
    wx.switchTab({ url: '/pages/buyer/buyer' });
  },

  goToProfile() {
    wx.switchTab({ url: '/pages/profile/profile' });
  }
});
