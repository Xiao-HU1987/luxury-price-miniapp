const request = require('../../utils/request.js');
const { COUNTRIES } = require('../../utils/constants.js');
const { convertCurrency } = require('../../utils/util.js');

const app = getApp();

Page({
  data: {
    statusBarHeight: 20,
    keyword: '',
    brandId: '',
    category: '',
    country: '',
    sortBy: 'price-low',
    products: [],
    exchangeRates: null,
    showFilter: false,
    brands: [],
    countries: COUNTRIES,
    sortOptions: [
      { value: 'price-low', label: '价格从低到高' },
      { value: 'price-high', label: '价格从高到低' }
    ],
    currentSortLabel: '价格从低到高'
  },

  onLoad(options) {
    this.setData({ statusBarHeight: app.globalData.statusBarHeight || 20 });
    const keyword = options.keyword || '';
    const brandId = options.brandId || '';
    const category = options.category || '';
    this.setData({
      keyword: decodeURIComponent(keyword),
      brandId,
      category
    });
    this.loadBrands();
    this.searchProducts();
  },

  loadBrands() {
    const that = this;
    request.get('/api/product/brands').then(data => {
      if (data && Array.isArray(data)) {
        // 兼容云函数返回（brandId/brandName）与旧后端（brand_id/name_cn）
        const brands = data.map(b => ({
          id: b.brandId || b.brand_id,
          name: b.brandName || b.name,
          nameCn: b.brandName || b.name_cn || b.name,
          logo: b.logo || ''
        })).filter(b => b.id);
        that.setData({ brands });
      }
    }).catch(() => {});
  },

  onShow() {
    const rates = app.globalData.exchangeRates;
    if (rates) {
      this.setData({ exchangeRates: rates });
    }
    this.searchProducts();
  },

  onKeywordInput(e) {
    this.setData({ keyword: e.detail.value });
  },

  onSearch() {
    this.searchProducts();
  },

  searchProducts() {
    const that = this;
    const { keyword, brandId, category, country, sortBy } = this.data;

    const params = { page: 1, pageSize: 50, keyword, brandId };
    request.get('/api/product/search', params).then((data) => {
      if (data && data.list) {
        const rates = that.data.exchangeRates;
        const formatPrice = (n) => n > 0 ? String(Math.round(n)).replace(/\B(?=(\d{3})+(?!\d))/g, ',') : '';
        // 默认（未搜索/未选品牌）时：无真实名称的商品不展示；搜索场景不过滤（保证可搜到）
        const isSearch = !!((keyword || '').trim() || brandId);
        const list = (isSearch ? data.list : data.list.filter(p => p.nameCn || p.nameJp || p.nameEn)) || [];
        const processed = list.map(p => {
          // 云函数返回驼峰字段（productId/cnOfficialPrice/jpCnyPrice/krCnyPrice/countryCount）
          const cnPrice = p.cnOfficialPrice || 0;
          const jpCny = p.jpCnyPrice || 0;
          const krCny = p.krCnyPrice || 0;
          return {
            id: p.productId,
            productId: p.productId,
            brandId: p.brandId || '',
            brandName: p.brandName || '',
            name: p.nameCn || p.nameJp || p.nameEn || '暂无名称',
            nameEn: p.nameEn || '',
            image: p.mainImage || (p.images && p.images[0]) || '',
            images: (p.images && p.images.length > 0) ? p.images : ((p.mainImage) ? [p.mainImage] : []),
            imageError: false,
            cnPriceStr: formatPrice(cnPrice),
            jpPrice: p.jpPrice || 0,
            jpCnyPrice: jpCny,
            jpCnyStr: formatPrice(jpCny),
            jpPriceCnyStr: formatPrice(jpCny),
            krPrice: p.krPrice || 0,
            krCnyPrice: krCny,
            krCnyStr: formatPrice(krCny),
            bestGlobalPrice: p.bestGlobalPrice || 0,
            bestCountry: p.bestCountry || '',
            countryCount: p.countryCount || 0,
            skuCount: p.countryCount || 0,
            hasJpPrice: jpCny > 0,
            hasKrPrice: krCny > 0
          };
        });

        if (sortBy === 'price-low') {
          processed.sort((a, b) => (a.jpCnyPrice || 0) - (b.jpCnyPrice || 0));
        } else if (sortBy === 'price-high') {
          processed.sort((a, b) => (b.jpCnyPrice || 0) - (a.jpCnyPrice || 0));
        }

        that.setData({ products: processed });
      }
    }).catch(() => {});
  },

  onProductTap(e) {
    const id = e.currentTarget.dataset.id;
    wx.navigateTo({
      url: '/pages/product-detail/product-detail?id=' + id
    });
  },

  onImageError(e) {
    const id = e.currentTarget.dataset.id;
    const products = this.data.products.map(p => {
      if (p.id !== id) return p;
      // 容错重试：当前图失败时，尝试用其余图片；仅剩单图时标记错误显示占位
      const rest = (p.images || []).filter(u => u && u !== p.image);
      const img = rest[0] || '';
      return {
        ...p,
        image: img,
        images: rest.length > 0 ? rest : p.images,
        imageError: img ? false : true
      };
    });
    this.setData({ products });
  },

  toggleFilter() {
    this.setData({ showFilter: !this.data.showFilter });
  },

  closeFilter() {
    this.setData({ showFilter: false });
  },

  selectBrand(e) {
    const brandId = e.currentTarget.dataset.brandId;
    const current = this.data.brandId === brandId ? '' : brandId;
    this.setData({ brandId: current });
  },

  selectCountry(e) {
    const country = e.currentTarget.dataset.country;
    const current = this.data.country === country ? '' : country;
    this.setData({ country: current });
  },

  selectSort(e) {
    const value = e.currentTarget.dataset.value;
    const option = this.data.sortOptions.find(o => o.value === value);
    this.setData({
      sortBy: value,
      currentSortLabel: option ? option.label : ''
    });
    this.searchProducts();
  },

  applyFilter() {
    this.setData({ showFilter: false });
    this.searchProducts();
  },

  resetFilter() {
    this.setData({
      brandId: '',
      country: '',
      sortBy: 'price-low',
      currentSortLabel: '价格从低到高'
    });
    this.searchProducts();
  },

  goBack() {
    wx.navigateBack({ delta: 1 });
  }
});
