const app = getApp();
const dataService = require('../../utils/dataService.js');

Page({
  data: {
    list: [],
    totalCount: 0,
    empty: true,
    loading: true
  },

  onShow() {
    this.loadAlerts();
  },

  async loadAlerts() {
    this.setData({ loading: true });
    try {
      const res = await dataService.getPriceAlerts();
      const rawList = this._extractList(res);

      const enrichedList = [];
      for (const item of rawList) {
        const productId = item.productId;
        const targetPrice = Number(item.targetPrice || 0);

        let product = item.product || {};
        if (!product || !product.productId) {
          try {
            const detailRes = await dataService.getProductDetail(productId);
            if (detailRes && detailRes.product) {
              product = detailRes.product;
              if (detailRes.priceStocks) {
                product._priceStocks = detailRes.priceStocks;
              }
            }
          } catch (e) {
            console.warn('Fetch product detail failed:', productId, e.message);
          }
        }

        const priceStocks = product._priceStocks || (item.priceStocks ? item.priceStocks : this._getPriceStocksFromMock(productId));
        const bestGlobalPrice = this._calcBestGlobalPrice(product, priceStocks);
        const reached = bestGlobalPrice > 0 && bestGlobalPrice <= targetPrice;

        enrichedList.push({
          productId: product.productId || productId,
          brandName: product.brandName || item.brandName || '',
          displayName: this._pickDisplayName(product),
          nameCn: product.nameCn || '',
          nameEn: product.nameEn || '',
          mainImage: product.mainImage || item.mainImage || '',
          bestGlobalPrice: bestGlobalPrice,
          bestPriceStr: this._formatPrice(bestGlobalPrice),
          targetPrice: targetPrice,
          targetPriceStr: this._formatPrice(targetPrice),
          reached: reached
        });
      }

      this.setData({
        list: enrichedList,
        totalCount: enrichedList.length,
        empty: enrichedList.length === 0,
        loading: false
      });
    } catch (err) {
      console.error('[price-alerts] loadAlerts error:', err);
      this.setData({
        list: [],
        totalCount: 0,
        empty: true,
        loading: false
      });
    }
  },

  handleDelete(e) {
    const productId = e.currentTarget.dataset.productId;
    if (!productId) return;

    const that = this;
    wx.showModal({
      title: '删除提醒',
      content: '确定删除该价格提醒吗？',
      confirmText: '删除',
      confirmColor: '#E53935',
      async success(res) {
        if (res.confirm) {
          try {
            await dataService.removePriceAlert(productId);
            wx.showToast({ title: '已删除', icon: 'success' });
            that.loadAlerts();
          } catch (err) {
            console.error('[price-alerts] delete error:', err);
            wx.showToast({ title: '删除失败', icon: 'none' });
          }
        }
      }
    });
  },

  _extractList(res) {
    if (!res) return [];
    if (Array.isArray(res)) return res;
    if (res.data) {
      if (Array.isArray(res.data)) return res.data;
      if (res.data.list && Array.isArray(res.data.list)) return res.data.list;
      if (res.data.alerts && Array.isArray(res.data.alerts)) return res.data.alerts;
    }
    if (res.list && Array.isArray(res.list)) return res.list;
    if (res.alerts && Array.isArray(res.alerts)) return res.alerts;
    return [];
  },

  _getPriceStocksFromMock(productId) {
    try {
      const mock = require('../../utils/mock.js');
      if (mock.PRICE_STOCK && Array.isArray(mock.PRICE_STOCK)) {
        return mock.PRICE_STOCK.filter(ps => ps.productId === productId && ps.stockStatus === 'available');
      }
    } catch (e) {}
    return [];
  },

  _calcBestGlobalPrice(product, priceStocks) {
    if (product && typeof product.bestGlobalPrice === 'number' && product.bestGlobalPrice > 0) {
      return product.bestGlobalPrice;
    }
    if (product && typeof product.jpCnyPrice === 'number' && product.jpCnyPrice > 0) {
      return product.jpCnyPrice;
    }
    if (priceStocks && priceStocks.length > 0) {
      const available = priceStocks.filter(ps => ps.stockStatus === 'available' || ps.stockStatus === undefined);
      if (available.length > 0) {
        const best = available.reduce((min, ps) => {
          const cny = typeof ps.cnyPrice === 'number' ? ps.cnyPrice : Infinity;
          return cny < min ? cny : min;
        }, Infinity);
        if (best !== Infinity) return best;
      }
    }
    if (product && typeof product.cnOfficialPrice === 'number' && product.cnOfficialPrice > 0) {
      return product.cnOfficialPrice;
    }
    return 0;
  },

  _pickDisplayName(product) {
    if (!product) return '';
    if (product.displayName) return product.displayName;
    const nameCn = product.nameCn || '';
    const nameJp = product.nameJp || '';
    const nameEn = product.nameEn || '';
    const isPureChinese = /^[\u4e00-\u9fff]+$/.test(nameCn);
    if (isPureChinese) return nameJp || nameCn;
    return nameCn || nameJp || nameEn;
  },

  _formatPrice(price) {
    const num = Number(price);
    if (!isFinite(num) || num <= 0) return '0';
    return Math.round(num).toLocaleString('en-US');
  }
});
