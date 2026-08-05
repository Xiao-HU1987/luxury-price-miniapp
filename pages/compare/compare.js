const dataService = require('../../utils/dataService.js');

function formatPrice(num) {
  if (!num || isNaN(num)) return '0';
  return Number(num).toLocaleString('zh-CN');
}

Page({
  data: {
    products: []
  },

  onLoad() {
    this.loadCompareList();
  },

  onShow() {
    this.loadCompareList();
  },

  async loadCompareList() {
    try {
      const res = await dataService.getCompareList();
      let list = [];
      if (res && res.code === 0) {
        list = res.data && res.data.list ? res.data.list : (res.data || []);
      } else if (Array.isArray(res)) {
        list = res;
      }
      const products = this.enrichProducts(list);
      this.setData({ products });
    } catch (e) {
      console.error('[compare] 加载对比列表失败:', e);
      this.setData({ products: [] });
    }
  },

  enrichProducts(list) {
    return list.map(p => {
      const cnOfficialPrice = Number(p.cnOfficialPrice || 0);
      const jpCnyPrice = Number(p.jpCnyPrice || 0);
      const krCnyPrice = Number(p.krCnyPrice || 0);

      const prices = [];
      if (cnOfficialPrice > 0) prices.push({ country: 'CN', price: cnOfficialPrice });
      if (jpCnyPrice > 0) prices.push({ country: 'JP', price: jpCnyPrice });
      if (krCnyPrice > 0) prices.push({ country: 'KR', price: krCnyPrice });

      let bestGlobalPrice = cnOfficialPrice;
      let bestCountry = 'CN';
      if (prices.length > 0) {
        const best = prices.reduce((min, cur) => cur.price < min.price ? cur : min);
        bestGlobalPrice = best.price;
        bestCountry = best.country;
      }
      if (p.bestGlobalPrice) bestGlobalPrice = p.bestGlobalPrice;
      if (p.bestCountry) bestCountry = p.bestCountry;

      const saveAmount = Math.max(0, cnOfficialPrice - bestGlobalPrice);

      return {
        productId: p.productId,
        nameCn: p.nameCn || p.name || '',
        brandName: p.brandName || '',
        mainImage: p.mainImage || '',
        cnOfficialPrice,
        jpCnyPrice,
        krCnyPrice,
        bestGlobalPrice,
        bestCountry,
        saveAmount,
        cnOfficialPriceStr: formatPrice(cnOfficialPrice),
        jpCnyPriceStr: formatPrice(jpCnyPrice),
        krCnyPriceStr: formatPrice(krCnyPrice),
        bestGlobalPriceStr: formatPrice(bestGlobalPrice),
        saveAmountStr: formatPrice(saveAmount)
      };
    });
  },

  async removeProduct(e) {
    const productId = e.currentTarget.dataset.id;
    if (!productId) return;

    try {
      wx.showLoading({ title: '移除中...', mask: true });
      await dataService.removeFromCompare(productId);
      wx.hideLoading();
      wx.showToast({ title: '已移除', icon: 'success' });
      this.loadCompareList();
    } catch (e) {
      wx.hideLoading();
      console.error('[compare] 移除失败:', e);
      wx.showToast({ title: '操作失败', icon: 'none' });
    }
  },

  async clearAll() {
    const { products } = this.data;
    if (products.length === 0) return;

    wx.showModal({
      title: '提示',
      content: '确定清空所有对比商品吗？',
      success: async (res) => {
        if (res.confirm) {
          try {
            wx.showLoading({ title: '清空中...', mask: true });
            await dataService.clearCompare();
            wx.hideLoading();
            wx.showToast({ title: '已清空', icon: 'success' });
            this.setData({ products: [] });
          } catch (e) {
            wx.hideLoading();
            console.error('[compare] 清空失败:', e);
            wx.showToast({ title: '操作失败', icon: 'none' });
          }
        }
      }
    });
  },

  goToDetail(e) {
    const id = e.currentTarget.dataset.id;
    if (!id) return;
    wx.navigateTo({
      url: `/pages/product-detail/product-detail?id=${id}`
    });
  },

  addHint() {
    wx.navigateBack({
      fail: () => {
        wx.switchTab({
          url: '/pages/index/index'
        });
      }
    });
  }
});
