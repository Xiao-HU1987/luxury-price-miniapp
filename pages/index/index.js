const app = getApp();
const dataService = require('../../utils/dataService.js');

const HOT_KEYWORDS = ['LV', '老花', 'Speedy', 'Neverfull', 'Onthego'];

Page({
  data: {
    searchKeyword: '',
    products: [],
    statusBarHeight: 20,
    headerHeight: 0,
    headerInnerHeight: 48,
    hotKeywords: HOT_KEYWORDS,
    loading: false,
    loaded: false
  },

  onLoad() {
    const sysInfo = wx.getSystemInfoSync();
    const statusBarHeight = sysInfo.statusBarHeight || 20;
    const menuButton = wx.getMenuButtonBoundingClientRect();
    const menuButtonBottom = menuButton ? menuButton.bottom : statusBarHeight + 38;
    // 标题行高度对齐胶囊按钮底部，使"比惠"文字与胶囊下沿对齐
    const headerInnerHeight = menuButtonBottom - statusBarHeight;
    // 计算头部高度：状态栏 + 标题行 + 搜索框 + 关键词区 + padding，缩减多余空白以对齐工具tab间距
    const headerHeight = statusBarHeight + 136;

    this.setData({
      statusBarHeight,
      headerHeight,
      headerInnerHeight
    });
    this.loadProducts();
  },

  onShow() {
    if (typeof this.getTabBar === 'function' && this.getTabBar()) {
      this.getTabBar().setData({ selected: 0 });
    }
  },

  onPullDownRefresh() {
    this.loadProducts();
    wx.stopPullDownRefresh();
  },

  loadProducts() {
    this.setData({ loading: true });
    const that = this;
    const params = { page: 1, pageSize: 50 };
    if (this.data.searchKeyword) params.keyword = this.data.searchKeyword;

    dataService.getProductList(params).then(data => {
      const all = (data && data.list) || [];
      // 默认（未搜索）时：无真实名称的商品不在比价页显示；搜索场景不过滤（保证可搜到）
      const isSearch = !!this.data.searchKeyword.trim();
      const list = (isSearch ? all : all.filter(p => p.nameCn || p.nameJp || p.nameEn)) || [];
      
      // 格式化价格
      const formatPrice = (n) => String(n).replace(/\B(?=(\d{3})+(?!\d))/g, ',');
      
      const products = list.map(p => {
        const cnPrice = p.cnOfficialPrice || 0;
        const jpCny = p.jpCnyPrice || 0;
        const krCny = p.krCnyPrice || 0;
        const hasCnPrice = p.hasCnPrice && cnPrice > 0;
        
        // 智能选择显示名称
        const nameCn = p.nameCn || '';
        const nameJp = p.nameJp || '';
        const nameEn = p.nameEn || '';
        const isPureChinese = /^[\u4e00-\u9fff]+$/.test(nameCn);
        let displayName = isPureChinese ? (nameJp || nameCn) : (nameCn || nameJp);
        // 三语全空时兜底英文名（云端已从韩文名/图URL推导），再无则显示占位（无真实名称的商品默认列表已过滤）
        if (!displayName) displayName = nameEn || '暂无名称';
        let subName = isPureChinese ? nameCn : (nameJp || '');
        if (!subName && nameEn && nameEn !== displayName) subName = nameEn;
        
        return {
          productId: p.productId,
          brandName: p.brandName || '',
          nameCn: displayName,
          displayName,
          subName,
          nameEn: p.nameEn || '',
          mainImage: p.mainImage || (p.images && p.images[0]) || '',
          images: (p.images && p.images.length > 0) ? p.images : ((p.mainImage) ? [p.mainImage] : []),
          imageError: false,
          cnOfficialPrice: cnPrice,
          hasCnPrice,
          cnPriceStr: hasCnPrice ? formatPrice(cnPrice) : '—',
          jpPrice: p.jpPrice || 0,
          jpCnyPrice: jpCny,
          jpCnyStr: jpCny > 0 ? formatPrice(jpCny) : '—',
          krPrice: p.krPrice || 0,
          krCnyPrice: krCny,
          krCnyStr: krCny > 0 ? formatPrice(krCny) : '—',
          bestGlobalPrice: p.bestGlobalPrice || 0,
          bestCountry: p.bestCountry || '',
          countryCount: p.countryCount || 0,
          hasJpPrice: jpCny > 0,
          hasKrPrice: krCny > 0
        };
      });
      that.setData({ products, loaded: true, loading: false });
    }).catch(() => {
      that.setData({ loading: false });
    });
  },

  onSearchInput(e) {
    const value = e.detail.value;
    const prev = this.data.searchKeyword;
    this.setData({ searchKeyword: value });
    // 方案1：删除搜索框内容后自动回到比价首页（恢复默认列表）
    if (value === '' && prev !== '') {
      this.loadProducts();
    }
  },

  // 方案2：点击刷新键，清空关键词并回到比价首页
  onResetSearch() {
    if (!this.data.searchKeyword) {
      // 无关键词时相当于刷新列表
      this.loadProducts();
      return;
    }
    this.setData({ searchKeyword: '' });
    this.loadProducts();
  },

  onSearchConfirm() {
    const kw = this.data.searchKeyword.trim();
    if (!kw) return;
    this.loadProducts();
  },

  onHotKeywordTap(e) {
    const kw = e.currentTarget.dataset.keyword;
    this.setData({ searchKeyword: kw });
    this.loadProducts();
  },

  onProductTap(e) {
    const id = e.currentTarget.dataset.id;
    wx.navigateTo({ url: '/pages/product-detail/product-detail?id=' + id });
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
  }
});
