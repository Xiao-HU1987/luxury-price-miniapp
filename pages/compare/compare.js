const dataService = require('../../utils/dataService.js');

const app = getApp();

function formatPrice(num) {
  if (!num || isNaN(num)) return '0';
  return Number(num).toLocaleString('zh-CN');
}

Page({
  data: {
    statusBarHeight: 20,
    products: []
  },

  onLoad() {
    this.setData({ statusBarHeight: app.globalData.statusBarHeight || 20 });
    this.loadCompareList();
  },

  onShow() {
    this.loadCompareList();
  },

  goBack() {
    wx.navigateBack({
      delta: 1,
      fail: () => {
        wx.switchTab({ url: '/pages/profile/profile' });
      }
    });
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
      // 对无商品详情的项调用 getProductDetail 兜底
      const enriched = [];
      for (const item of list) {
        if (item && item.productId && !item.nameCn && !item.name) {
          try {
            const detailRes = await dataService.getProductDetail(item.productId);
            if (detailRes && detailRes.product) {
              enriched.push(detailRes.product);
              continue;
            }
          } catch (e) {
            console.warn('[compare] Fetch product detail failed:', item.productId, e.message);
          }
        }
        enriched.push(item);
      }
      const products = this.enrichProducts(enriched);
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
        mainImage: p.mainImage || (p.images && p.images[0]) || '',
        images: (p.images && p.images.length > 0) ? p.images : ((p.mainImage) ? [p.mainImage] : []),
        imageError: false,
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

  onImageError(e) {
    const id = e.currentTarget.dataset.id;
    const products = this.data.products.map(p => {
      if (p.productId !== id) return p;
      // 容错重试：当前图失败时，尝试用其余图片；仅剩单图时标记错误显示占位
      const rest = (p.images || []).filter(u => u && u !== p.mainImage);
      const img = rest[0] || '';
      return {
        ...p,
        mainImage: img,
        images: rest.length > 0 ? rest : p.images,
        imageError: img ? false : true
      };
    });
    this.setData({ products });
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
