const app = getApp();
const dataService = require('../../utils/dataService.js');

const COUNTRY_PRESETS = [
  { code: 'JP', name: '日本', currency: 'JPY', symbol: '¥', flag: '🇯🇵', taxRate: 10 },
  { code: 'KR', name: '韩国', currency: 'KRW', symbol: '₩', flag: '🇰🇷', taxRate: 10 }
];

const PAYMENT_METHODS = [
  { code: 'alipay', name: '支付宝', rate: 0.38 },
  { code: 'wechat', name: '微信支付', rate: 0.38 },
  { code: 'card', name: '银行卡', rate: 1.5 },
  { code: 'cash', name: '现金', rate: 0 }
];

const FALLBACK_RATES = {
  JPY: 21.58,
  KRW: 192.5
};

Page({
  data: {
    countries: COUNTRY_PRESETS,
    payments: PAYMENT_METHODS,
    selectedCountryCode: 'JP',
    selectedCountry: COUNTRY_PRESETS[0],
    selectedPaymentCode: 'alipay',
    selectedPayment: PAYMENT_METHODS[0],
    priceInput: '',
    taxRateInput: '10',
    rebateRateInput: '0',
    exchangeRateInput: '',
    exchangeRateDisplay: '',
    exchangeRateEditing: false,
    rateSource: 'global',
    statusBarHeight: 20,
    navBarTotalHeight: 64,
    contentPaddingTop: 80,
    productInfo: null,
    result: {
      priceStr: '¥0.00',
      taxAmountStr: '-¥0.00',
      rebateAmountStr: '-¥0.00',
      paymentFeeStr: '+¥0.00',
      finalCnyStr: '0.00',
      savings: 0,
      savingsStr: '0'
    }
  },

  onLoad(options) {
    const sysInfo = wx.getSystemInfoSync();
    const statusBarHeight = sysInfo.statusBarHeight || 20;
    const menuButton = wx.getMenuButtonBoundingClientRect();
    const menuButtonTop = menuButton ? menuButton.top : statusBarHeight + 6;
    const menuButtonBottom = menuButton ? menuButton.bottom : statusBarHeight + 38;
    const navBarTotalHeight = menuButtonBottom + (menuButtonTop - statusBarHeight);
    const contentPaddingTop = navBarTotalHeight + 24;

    this.setData({
      statusBarHeight: statusBarHeight,
      navBarTotalHeight: navBarTotalHeight,
      contentPaddingTop: contentPaddingTop
    });

    // 如果从商品详情页跳转，携带 productId
    if (options && options.productId) {
      this.loadProductData(options.productId);
    }
  },

  loadProductData(productId) {
    dataService.getProductDetail(productId).then(data => {
      if (data && data.product) {
        const product = data.product;
        const priceStocks = data.priceStocks || [];
        
        // 填充商品信息
        this.setData({
          productInfo: {
            productId: product.productId,
            nameCn: product.nameCn,
            mainImage: product.mainImage,
            cnOfficialPrice: product.cnOfficialPrice
          }
        });

        // 查找当前选中国家的价格
        const countryCode = this.data.selectedCountryCode;
        const matchedPrice = priceStocks.find(p => p.countryCode === countryCode);
        if (matchedPrice && matchedPrice.localPrice) {
          this.setData({
            priceInput: String(matchedPrice.localPrice)
          });
        }
        this.calculate();
      }
    }).catch(() => {});
  },

  onShow() {
    if (typeof this.getTabBar === 'function' && this.getTabBar()) {
      this.getTabBar().setData({ selected: 2 });
    }
    this.refreshExchangeRate();

    // 检查是否有从商品详情页直接传递的价格数据（优先，无需云函数回填）
    const pendingCalc = app.globalData.pendingCalcData;
    if (pendingCalc && pendingCalc.productId) {
      app.globalData.pendingCalcData = null;
      this._applyPendingCalc(pendingCalc);
    }
    // 兼容旧链路：仅传了 productId（无价格）时走云函数回填
    else {
      const pendingProductId = app.globalData.pendingProductId;
      if (pendingProductId) {
        app.globalData.pendingProductId = null;
        this.loadProductData(pendingProductId);
      } else {
        this.calculate();
      }
    }
  },

  _applyPendingCalc(pendingCalc) {
    const country = COUNTRY_PRESETS.find(function (c) {
      return c.code === pendingCalc.countryCode;
    }) || COUNTRY_PRESETS[0];

    // 尝试用全局汇率同步填充（异步刷新前保证计算可用）
    let initRate = '';
    const globalRates = app.globalData.exchangeRates;
    if (globalRates && globalRates.rates) {
      const rate = globalRates.rates[country.currency] || 0; // 1 CNY = rate 外币
      const cnyPerUnit = rate > 0 ? 1 / rate : 0;
      if (cnyPerUnit > 0) initRate = cnyPerUnit.toFixed(4);
    }

    this.setData({
      productInfo: {
        productId: pendingCalc.productId,
        nameCn: pendingCalc.displayName || '',
        mainImage: pendingCalc.mainImage || ''
      },
      selectedCountryCode: country.code,
      selectedCountry: country,
      taxRateInput: String(country.taxRate),
      priceInput: pendingCalc.price ? String(pendingCalc.price) : '',
      exchangeRateInput: initRate,
      exchangeRateDisplay: initRate || '—',
      rateSource: 'global',
      exchangeRateEditing: false
    }, function () {
      this.calculate();
    });
  },

  refreshExchangeRate() {
    const country = this.data.selectedCountry;
    dataService.getExchangeRates().then(data => {
      if (data && data.rates) {
        // 云端语义：1 CNY = x 外币；展示/输入语义：1 外币 = x 人民币
        const rate = data.rates[country.currency] || 0; // 1 CNY = rate 外币
        const cnyPerUnit = rate > 0 ? 1 / rate : 0;     // 1 外币 = cnyPerUnit 人民币
        if (this.data.rateSource === 'global') {
          this.setData({
            exchangeRateInput: cnyPerUnit > 0 ? cnyPerUnit.toFixed(4) : '',
            exchangeRateDisplay: this.formatRate(cnyPerUnit, 'CNY')
          });
        }
      }
    });
  },

  onCountryTap(e) {
    const code = e.currentTarget.dataset.code;
    const country = COUNTRY_PRESETS.find(function (c) { return c.code === code; });
    if (!country) return;
    this.setData({
      selectedCountryCode: code,
      selectedCountry: country,
      taxRateInput: String(country.taxRate),
      rateSource: 'global',
      exchangeRateEditing: false
    }, function () {
      this.refreshExchangeRate();
      // 如果有商品信息，重新加载对应国家的价格
      if (this.data.productInfo && this.data.productInfo.productId) {
        this.loadProductData(this.data.productInfo.productId);
      } else {
        this.calculate();
      }
    });
  },

  onPaymentTap(e) {
    const code = e.currentTarget.dataset.code;
    const payment = PAYMENT_METHODS.find(function (p) { return p.code === code; });
    if (!payment) return;
    this.setData({
      selectedPaymentCode: code,
      selectedPayment: payment
    }, function () {
      this.calculate();
    });
  },

  onPriceInput(e) {
    this.setData({ priceInput: e.detail.value }, function () {
      this.calculate();
    });
  },

  onTaxRateInput(e) {
    this.setData({ taxRateInput: e.detail.value }, function () {
      this.calculate();
    });
  },

  onRebateRateInput(e) {
    this.setData({ rebateRateInput: e.detail.value }, function () {
      this.calculate();
    });
  },

  onExchangeRateTap() {
    this.setData({ exchangeRateEditing: true });
  },

  onExchangeRateInput(e) {
    this.setData({
      exchangeRateInput: e.detail.value,
      rateSource: 'manual'
    }, function () {
      this.calculate();
    });
  },

  onExchangeRateBlur() {
    const val = parseFloat(this.data.exchangeRateInput) || 0;
    this.setData({
      exchangeRateEditing: false,
      exchangeRateDisplay: this.formatRate(val, 'CNY')
    });
  },

  calculate() {
    const data = this.data;
    const price = parseFloat(data.priceInput) || 0;
    const taxRate = parseFloat(data.taxRateInput) || 0;
    const rebateRate = parseFloat(data.rebateRateInput) || 0;
    const paymentRate = data.selectedPayment.rate;
    // 汇率语义：1 外币 = x 人民币（用户输入与展示方向一致）
    const cnyPerUnit = parseFloat(data.exchangeRateInput) || 0;

    // 海外官网价格均为含税价：先倒推免税价，再按免税价计算税额（退税金额=含税价-免税价）
    const basePrice = price / (1 + taxRate / 100);
    const taxAmount = price - basePrice;
    const rebateAmount = price * (rebateRate / 100);
    const paymentFee = price * (paymentRate / 100);
    const discountedPrice = price - taxAmount - rebateAmount;
    const finalForeignCost = discountedPrice + paymentFee;
    const finalCny = cnyPerUnit > 0 ? finalForeignCost * cnyPerUnit : 0;

    const symbol = data.selectedCountry.symbol;

    this.setData({
      result: {
        priceStr: symbol + this.formatNumber(price),
        taxAmountStr: '-' + symbol + this.formatNumber(taxAmount),
        rebateAmountStr: '-' + symbol + this.formatNumber(rebateAmount),
        paymentFeeStr: '+' + symbol + this.formatNumber(paymentFee),
        finalCnyStr: this.formatNumber(finalCny),
        savings: 0,
        savingsStr: '0'
      }
    });
  },

  formatNumber(num) {
    if (!isFinite(num) || isNaN(num)) return '0.00';
    const fixed = Math.round(num * 100) / 100;
    const parts = fixed.toFixed(2).split('.');
    parts[0] = parts[0].replace(/\B(?=(\d{3})+(?!\d))/g, ',');
    return parts.join('.');
  },

  formatRate(rate, currency) {
    if (!rate || rate <= 0) return '—';
    if (currency === 'JPY' || currency === 'KRW') {
      return rate.toFixed(2);
    }
    return rate.toFixed(4);
  }
});
