const request = require('../../utils/request.js');
const dataService = require('../../utils/dataService.js');

const app = getApp();

Page({
  data: {
    statusBarHeight: 20,
    list: [],
    empty: true,
    loading: true,
    selectMode: false,   // 清理（多选）模式
    selectedIds: []
  },

  onLoad() {
    this.setData({ statusBarHeight: app.globalData.statusBarHeight || 20 });
  },

  onShow() {
    this.loadHistory();
  },

  // 本地缓存key：浏览历史（未登录/重登录都能看到，登录后与云端合并）
  getLocalHistoryKey() {
    const userInfo = wx.getStorageSync('userInfo') || {};
    return 'viewHistoryLocal:' + (userInfo.user_id || 'guest');
  },

  // 本地商品简要信息key（详情页写入，供未登录/云端缺失时展示名称与图片）
  getMetaKey() {
    return this.getLocalHistoryKey() + ':meta';
  },

  loadHistory() {
    const userInfo = app.globalData.userInfo || wx.getStorageSync('userInfo') || {};
    this.setData({ loading: true });

    const localIds = wx.getStorageSync(this.getLocalHistoryKey()) || [];

    const applyItems = (items) => {
      this.setData({ list: items, empty: items.length === 0, loading: false, selectMode: false, selectedIds: [] });
    };

    // 登录后从云端拉取（云函数已联查商品信息），与本地合并；未登录只展示本地
    if (userInfo.user_id) {
      request.get('/api/user/history', { user_id: userInfo.user_id })
        .then((data) => {
          // 云函数返回商品数据数组，兼容 {list}/{data} 包装
          const raw = Array.isArray(data) ? data : ((data && (data.list || data.data)) || []);
          const cloudItems = raw.filter(Boolean).map(p => this._normalize(p)).filter(i => i.id);
          const cloudIds = cloudItems.map(i => i.id);
          const localOnlyIds = localIds.filter(id => !cloudIds.includes(id));
          this._fillLocalIds(localOnlyIds, cloudItems).then(merged => {
            wx.setStorageSync(this.getLocalHistoryKey(), merged.map(i => i.id));
            applyItems(merged);
          });
        })
        .catch(() => {
          this._fillLocalIds(localIds, []).then(applyItems);
        });
    } else {
      this._fillLocalIds(localIds, []).then(applyItems);
    }
  },

  // 本地单独存在的记录：先用本地meta补名称/图片，再拉商品列表补充价格信息
  // 商品总数远超100，列表匹配不到的商品需单独调用 getProductDetail 补充
  _fillLocalIds(ids, baseItems) {
    const localMeta = wx.getStorageSync(this.getMetaKey()) || {};
    const missing = ids.filter(id => !baseItems.some(i => i.id === id));
    if (missing.length === 0) {
      return Promise.resolve(baseItems.filter(i => i.id));
    }
    const withMeta = ids.map(id => {
      const exist = baseItems.find(i => i.id === id);
      if (exist) return exist;
      const m = localMeta[id] || {};
      return { id, name: m.name || '', brandName: '', image: m.image || '' };
    });
    return dataService.getProductList({ page: 1, pageSize: 100 })
      .then(data => {
        const all = data.list || [];
        const matched = [];
        const unmatched = [];
        withMeta.forEach(item => {
          const p = all.find(x => x.productId === item.id);
          if (p) {
            matched.push(this._normalize(p));
          } else {
            unmatched.push(item);
          }
        });
        // 对列表匹配不到的商品，逐个调用 getProductDetail 补充名称和图片
        if (unmatched.length === 0) {
          return matched.filter(i => i.id);
        }
        return Promise.all(unmatched.map(item =>
          dataService.getProductDetail(item.id)
            .then(detail => {
              if (detail && detail.product) {
                return this._normalize(detail.product);
              }
              return item;
            })
            .catch(() => item)
        )).then(detailed => matched.concat(detailed).filter(i => i.id));
      })
      .catch(() => withMeta.filter(i => i.id));
  },

  // 商品字段规范化：兼容云函数联查原始文档与 getProductList 返回
  _normalize(p) {
    const cnPrice = Number(p.cnOfficialPrice || 0);
    const jpCny = Number(p.jpCnyPrice || 0);
    const name = p.nameCn || p.nameJp || p.nameEn || this._fallbackName(p) || '';
    return {
      id: p.productId || p.id || '',
      name,
      brandName: p.brandName || '',
      image: p.mainImage || (p.images && p.images[0]) || '',
      hasCn: cnPrice > 0,
      cnPriceStr: this._formatPrice(cnPrice),
      hasJp: jpCny > 0,
      jpCnyStr: this._formatPrice(jpCny)
    };
  },

  // 三语名全空时（数据源仅捕获韩文名），从韩文名括号或主图URL提取英文名兜底
  _fallbackName(p) {
    const kr = p.nameKr || '';
    const m = kr.match(/\(([^()]*[A-Za-z][^()]*)\)/);
    if (m) return m[1].trim();
    const url = p.mainImage || '';
    if (!url) return '';
    let base = String(url.split('/').pop() || '').split('?')[0].split('--')[0];
    const words = base.split('-').map(w => w.trim()).filter(Boolean);
    while (words.length && ['louis', 'vuitton', 'lv'].includes(words[0].toLowerCase())) words.shift();
    if (words.length === 0) return '';
    const SIZE_MAP = { mm: 'MM', pm: 'PM', gm: 'GM', bb: 'BB', nm: 'NM', tm: 'TM' };
    return words.map(w => {
      const low = w.toLowerCase();
      if (SIZE_MAP[low]) return SIZE_MAP[low];
      return low === 'x' ? 'X' : w.charAt(0).toUpperCase() + w.slice(1);
    }).join(' ');
  },

  _formatPrice(n) {
    return String(n || 0).replace(/\B(?=(\d{3})+(?!\d))/g, ',');
  },

  onImageError(e) {
    const idx = e.currentTarget.dataset.index;
    const key = `list[${idx}].image`;
    this.setData({ [key]: '' });
  },

  // ===== 多选删除 =====
  startClear() {
    this.setData({ selectMode: true, selectedIds: [] });
    this._refreshSelection();
  },

  cancelSelect() {
    this.setData({ selectMode: false, selectedIds: [] });
    this._refreshSelection();
  },

  toggleSelect(e) {
    const id = e.currentTarget.dataset.id;
    let sel = this.data.selectedIds;
    sel = sel.includes(id) ? sel.filter(x => x !== id) : sel.concat(id);
    this.setData({ selectedIds: sel });
    this._refreshSelection();
  },

  _refreshSelection() {
    const sel = this.data.selectedIds;
    const list = this.data.list.map(i => ({ ...i, selected: sel.includes(i.id) }));
    this.setData({ list });
  },

  onItemTap(e) {
    if (this.data.selectMode) {
      this.toggleSelect(e);
      return;
    }
    const id = e.currentTarget.dataset.id;
    if (id) {
      wx.navigateTo({ url: `/pages/product-detail/product-detail?id=${id}` });
    }
  },

  onDeleteSelected() {
    const sel = this.data.selectedIds;
    if (sel.length === 0) {
      wx.showToast({ title: '请先选择记录', icon: 'none' });
      return;
    }
    wx.showModal({
      title: '提示',
      content: `确定删除所选 ${sel.length} 条浏览记录吗？`,
      success: (res) => {
        if (res.confirm) {
          this._doDelete(sel);
        }
      }
    });
  },

  _doDelete(ids) {
    const userInfo = app.globalData.userInfo || wx.getStorageSync('userInfo') || {};
    const finish = () => {
      const localIds = wx.getStorageSync(this.getLocalHistoryKey()) || [];
      wx.setStorageSync(this.getLocalHistoryKey(), localIds.filter(x => !ids.includes(x)));
      wx.showToast({ title: '已删除', icon: 'success' });
      this.loadHistory();
    };
    if (userInfo.user_id) {
      request.del('/api/user/history/remove-batch', { productIds: ids, user_id: userInfo.user_id })
        .then(finish)
        .catch(() => {
          wx.showToast({ title: '操作失败', icon: 'none' });
        });
    } else {
      finish();
    }
  },

  // 返回：回到我的 tab
  goBack() {
    const pages = getCurrentPages();
    if (pages.length > 1) {
      wx.navigateBack({
        fail: () => {
          wx.switchTab({ url: '/pages/profile/profile' });
        }
      });
    } else {
      wx.switchTab({ url: '/pages/profile/profile' });
    }
  }
});