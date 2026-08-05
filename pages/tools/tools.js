// 综合工具页 - 汇率看板 + 返点优惠
const app = getApp();
const dataService = require('../../utils/dataService.js');

// 币种列表（1 CNY 兑换的外币数量）
const CURRENCY_LIST = [
  { code: 'CNY', name: '人民币', symbol: '¥', flag: '🇨🇳' },
  { code: 'JPY', name: '日元', symbol: '¥', flag: '🇯🇵' },
  { code: 'KRW', name: '韩元', symbol: '₩', flag: '🇰🇷' }
];

// 默认汇率（1 CNY 兑换的外币数量）
const DEFAULT_RATES = {
  CNY: 1,
  JPY: 21.58,
  KRW: 192.5
};

// 返点优惠数据（内置，后续可迁移到云数据库）
const REBATE_SHOPS = [
  {
    id: 'r001',
    shopName: 'LV 日本官方',
    country: 'JP',
    countryName: '日本',
    rebateRate: 8,
    minAmount: 0,
    conditions: '全品类适用，无需额外申请',
    validUntil: '长期有效',
    isHot: true,
    tags: ['官方直营', '退税10%']
  },
  {
    id: 'r002',
    shopName: 'LV 韩国免税店',
    country: 'KR',
    countryName: '韩国',
    rebateRate: 10,
    minAmount: 0,
    conditions: '免税店购买，需出示护照',
    validUntil: '2026-12-31',
    isHot: true,
    tags: ['免税店', '即时退税']
  },
  {
    id: 'r003',
    shopName: '日本百货渠道',
    country: 'JP',
    countryName: '日本',
    rebateRate: 12,
    minAmount: 100000,
    conditions: '单笔满10万日元，需通过指定代理',
    validUntil: '2026-09-30',
    isHot: false,
    tags: ['高额返点', '需预约']
  },
  {
    id: 'r004',
    shopName: '韩国百货渠道',
    country: 'KR',
    countryName: '韩国',
    rebateRate: 15,
    minAmount: 500000,
    conditions: '单笔满50万韩元，仅限VIP会员',
    validUntil: '2026-08-31',
    isHot: false,
    tags: ['VIP专享', '高额返点']
  }
];

Page({
  data: {
    statusBarHeight: 20,
    navBarTotalHeight: 64,
    contentPaddingTop: 80,

    // 汇率看板
    currencyList: CURRENCY_LIST,
    rates: DEFAULT_RATES,
    rateUpdateTime: '',
    rateChannels: [],
    fromCurrency: 'CNY',
    toCurrency: 'JPY',
    amountInput: '100',
    convertResult: '',
    ratesLoading: false
  },

  onLoad() {
    const sysInfo = wx.getSystemInfoSync();
    const statusBarHeight = sysInfo.statusBarHeight || 20;
    const menuButton = wx.getMenuButtonBoundingClientRect();
    const menuButtonTop = menuButton ? menuButton.top : statusBarHeight + 6;
    const menuButtonBottom = menuButton ? menuButton.bottom : statusBarHeight + 38;
    const navBarTotalHeight = menuButtonBottom + (menuButtonTop - statusBarHeight);
    const contentPaddingTop = navBarTotalHeight + 16;

    this.setData({
      statusBarHeight,
      navBarTotalHeight,
      contentPaddingTop
    });

    this.loadExchangeRates();
    this.calcConvert();
  },

  onShow() {
    if (typeof this.getTabBar === 'function' && this.getTabBar()) {
      this.getTabBar().setData({ selected: 2 });
    }
  },

  // 加载汇率数据
  loadExchangeRates() {
    this.setData({ ratesLoading: true });
    dataService.getExchangeRates().then(data => {
      if (data && data.rates) {
        const rates = { ...DEFAULT_RATES, ...data.rates };
        const updateTime = data.updateTime || '';
        const channels = data.channels || [];
        const rateChannels = this.formatChannels(channels, rates);

        this.setData({
          rates,
          rateUpdateTime: this.formatTime(updateTime),
          rateChannels,
          ratesLoading: false
        });
        this.calcConvert();
      } else {
        this.setData({ ratesLoading: false });
      }
    }).catch(() => {
      const rateChannels = this.formatChannels([], DEFAULT_RATES);
      this.setData({
        rates: DEFAULT_RATES,
        rateChannels,
        ratesLoading: false
      });
      this.calcConvert();
    });
  },

  // 格式化渠道列表
  formatChannels(channels, rates) {
    const result = [];

    // JPY 渠道
    if (rates.JPY) {
      result.push({
        currency: 'JPY',
        currencyName: '日元',
        flag: '🇯🇵',
        baseRate: rates.JPY,
        cnyToJpy: rates.JPY,
        jpyToCny: (1 / rates.JPY).toFixed(4),
        tieredRules: this.extractRules(channels, 'JPY')
      });
    }

    // KRW 渠道
    if (rates.KRW) {
      result.push({
        currency: 'KRW',
        currencyName: '韩元',
        flag: '🇰🇷',
        baseRate: rates.KRW,
        cnyToKrw: rates.KRW,
        krwToCny: (1 / rates.KRW).toFixed(4),
        tieredRules: this.extractRules(channels, 'KRW')
      });
    }

    return result;
  },

  // 提取阶梯规则
  extractRules(channels, currency) {
    if (!channels || !channels.length) {
      // 返回默认规则
      return [
        { minAmount: 0, discountRate: 0, description: '基础汇率，无额外折扣' }
      ];
    }

    const channel = channels.find(c => c.currency === currency);
    if (channel && channel.tieredRules && channel.tieredRules.length) {
      return channel.tieredRules;
    }

    return [
      { minAmount: 0, discountRate: 0, description: '基础汇率，无额外折扣' }
    ];
  },

  // 格式化时间
  formatTime(timeStr) {
    if (!timeStr) return '未知';
    try {
      const d = new Date(timeStr);
      const month = String(d.getMonth() + 1).padStart(2, '0');
      const day = String(d.getDate()).padStart(2, '0');
      const hour = String(d.getHours()).padStart(2, '0');
      const minute = String(d.getMinutes()).padStart(2, '0');
      return `${month}-${day} ${hour}:${minute}`;
    } catch (e) {
      return '未知';
    }
  },

  // 汇率换算：输入金额
  onAmountInput(e) {
    this.setData({ amountInput: e.detail.value }, () => this.calcConvert());
  },

  // 选择源币种
  onFromCurrencyChange(e) {
    const code = e.currentTarget.dataset.code;
    let toCurrency = this.data.toCurrency;
    // 避免源和目标相同
    if (code === toCurrency) {
      const other = CURRENCY_LIST.find(c => c.code !== code);
      toCurrency = other ? other.code : 'JPY';
    }
    this.setData({ fromCurrency: code, toCurrency }, () => this.calcConvert());
  },

  // 选择目标币种
  onToCurrencyChange(e) {
    const code = e.currentTarget.dataset.code;
    if (code === this.data.fromCurrency) return;
    this.setData({ toCurrency: code }, () => this.calcConvert());
  },

  // 币种交换
  swapCurrency() {
    const { fromCurrency, toCurrency } = this.data;
    this.setData({ fromCurrency: toCurrency, toCurrency: fromCurrency }, () => this.calcConvert());
  },

  // 计算换算结果
  calcConvert() {
    const { amountInput, fromCurrency, toCurrency, rates } = this.data;
    const amount = parseFloat(amountInput) || 0;
    if (amount <= 0) {
      this.setData({ convertResult: '0.00' });
      return;
    }

    // 换算路径：源币种 -> CNY -> 目标币种
    const fromRate = rates[fromCurrency] || 1; // 1 CNY = fromRate 源币种
    const toRate = rates[toCurrency] || 1;     // 1 CNY = toRate 目标币种

    // 源金额 -> CNY
    const cnyAmount = amount / fromRate;
    // CNY -> 目标币种
    const result = cnyAmount * toRate;

    // 格式化：日元/韩元不保留小数，人民币保留2位
    let resultStr;
    if (toCurrency === 'JPY' || toCurrency === 'KRW') {
      resultStr = Math.round(result).toLocaleString('en-US');
    } else {
      resultStr = result.toFixed(2);
    }

    this.setData({ convertResult: resultStr });
  },

  // 刷新汇率
  refreshRates() {
    wx.showLoading({ title: '刷新中...' });
    this.loadExchangeRates();
    setTimeout(() => {
      wx.hideLoading();
      wx.showToast({ title: '已刷新', icon: 'success' });
    }, 1000);
  }
});
