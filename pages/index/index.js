const app = getApp();
const dataService = require('../../utils/dataService.js');

const HOT_KEYWORDS = ['LV', '老花', 'Speedy', 'Neverfull', 'Onthego'];

Page({
  data: {
    searchKeyword: '',
    products: [],
    statusBarHeight: 20,
    headerHeight: 0,
    hotKeywords: HOT_KEYWORDS,
    loading: false,
    loaded: false
  },

  onLoad() {
    const sysInfo = wx.getSystemInfoSync();
    const statusBarHeight = sysInfo.statusBarHeight || 20;
    
    // 计算头部高度：状态栏 + 标题行(48px) + 搜索框(40px) + 关键词区(30px) + padding(24px) + 间距(18px)
    const headerHeight = statusBarHeight + 160;
    
    this.setData({ 
      statusBarHeight,
      headerHeight
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
      const list = (data && data.list) || [];
      
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
        const isPureChinese = /^[\u4e00-\u9fff]+$/.test(nameCn);
        const displayName = isPureChinese ? (nameJp || nameCn) : (nameCn || nameJp);
        const subName = isPureChinese ? nameCn : (nameJp || '');
        
        return {
          productId: p.productId,
          brandName: p.brandName || '',
          nameCn: displayName,
          displayName,
          subName,
          nameEn: p.nameEn || '',
          mainImage: p.mainImage || '',
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
    this.setData({ searchKeyword: e.detail.value });
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
    const products = this.data.products.map(p =>
      p.productId === id ? { ...p, imageError: true } : p
    );
    this.setData({ products });
  }
});
