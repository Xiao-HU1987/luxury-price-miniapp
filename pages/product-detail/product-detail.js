const app = getApp();
const dataService = require('../../utils/dataService.js');
const { COUNTRIES } = require('../../utils/constants.js');

const DEFAULT_JP_RATE = 21.58;
const DEFAULT_KRW_RATE = 192.5;

Page({
  data: {
    statusBarHeight: 20,
    navBarHeight: 44,
    menuButtonTop: 0,
    menuButtonHeight: 32,

    productId: '',
    slug: '',
    sku: '',
    displayName: '',
    subName: '',
    nameCn: '',
    nameEn: '',
    nameJp: '',
    brandName: '',
    mainImage: '',
    images: [],
    imageIndex: 0,

    cnOfficialPrice: 0,
    cnPriceStr: '',
    jpPrice: 0,
    jpCnyPrice: 0,
    jpCnyStr: '',
    krPrice: 0,
    krCnyPrice: 0,
    krCnyStr: '',

    priceChannels: [],
    lowestCny: 0,
    lowestCnyStr: '',
    expandedChannel: -1,

    inventories: [],
    jpInventories: [],
    krInventories: [],
    activeCountry: 'JP',
    inventoryExpanded: false,

    exchangeRates: null,
    jpRate: DEFAULT_JP_RATE,
    krRate: DEFAULT_KRW_RATE,

    isFavorited: false,
    inCompare: false,
    showAlertDialog: false,
    targetPriceInput: '',
    currentPriceStr: '',
    sourceUrl: '',
    jpUrl: '',
    krUrl: ''
  },

  onLoad(options) {
    const sysInfo = wx.getSystemInfoSync();
    const statusBarHeight = sysInfo.statusBarHeight || 20;
    const menuButton = wx.getMenuButtonBoundingClientRect();
    const menuButtonTop = menuButton ? menuButton.top : statusBarHeight + 6;
    const menuButtonHeight = menuButton ? menuButton.height : 32;
    const navBarHeight = (menuButtonTop - statusBarHeight) * 2 + menuButtonHeight;

    const id = options.id;
    if (id) {
      this.setData({
        statusBarHeight, navBarHeight, menuButtonTop, menuButtonHeight,
        productId: id
      });
      this.loadProductDetail(id);
    } else {
      this.setData({ statusBarHeight, navBarHeight, menuButtonTop, menuButtonHeight });
    }
  },

  onShow() {
    this.loadExchangeRates();
    this.checkFavorite();
  },

  loadExchangeRates() {
    const that = this;
    // 先使用全局数据（可能是默认汇率）
    const globalRates = app.globalData.exchangeRates;
    if (globalRates) {
      that.setData({ exchangeRates: globalRates });
    }
    // 异步获取实时汇率
    dataService.getExchangeRates().then(rates => {
      if (rates && rates.rates) {
        app.globalData.exchangeRates = rates;
        that.setData({ exchangeRates: rates });
      }
    }).catch(() => {});
  },

  loadProductDetail(productId) {
    const that = this;
    dataService.getProductDetail(productId)
      .then(data => {
        if (!data) return;
        
        const product = data.product || {};
        const priceStocks = data.priceStocks || [];

        that._mapProductInfo(product);
        that._buildImages(product);
        that._buildPriceChannels(priceStocks);
        that._buildInventories(priceStocks);
        that._buildSourceUrls(product);
        that._updateNavTitle(product);
      })
      .catch(err => {
        console.error('Load detail failed:', err);
        wx.showToast({ title: '加载失败', icon: 'none' });
      });
  },

  _mapProductInfo(product) {
    const productId = product.productId || '';
    const slug = product.slug || '';
    const sku = (slug || productId).toUpperCase().replace(/^SPU-LV-/, '');
    
    const nameCn = product.nameCn || '';
    const nameJp = product.nameJp || '';
    const nameEn = product.nameEn || '';
    
    // 智能选择显示名称：优先用日文名，其次法文名，再次英文名
    // 如果 nameCn 是纯中文（机翻垃圾），改用日文名
    const isPureChinese = /^[\u4e00-\u9fff]+$/.test(nameCn);
    const displayName = isPureChinese ? (nameJp || nameCn) : (nameCn || nameJp);
    const subName = isPureChinese ? nameCn : (nameJp || nameEn);
    
    const brandName = product.brandName || '';
    const mainImage = product.mainImage || '';
    const cnOfficialPrice = product.cnOfficialPrice || 0;
    const hasCnPrice = cnOfficialPrice > 0;
    const cnPriceStr = hasCnPrice ? this._formatPrice(cnOfficialPrice) : '';

    this.setData({
      productId,
      slug,
      sku,
      displayName,
      subName,
      nameCn,
      nameEn,
      nameJp,
      brandName,
      mainImage,
      cnOfficialPrice,
      hasCnPrice,
      cnPriceStr
    });
  },

  _buildImages(product) {
    const images = [];
    if (product.images && Array.isArray(product.images)) {
      images.push(...product.images.filter(u => u && u.trim() && !u.includes('404')));
    }
    if (product.mainImage && product.mainImage.trim() && !product.mainImage.includes('404')) {
      images.push(product.mainImage);
    }
    // 去重，过滤空值
    const unique = [...new Set(images.filter(u => u && u.trim()))];
    this.setData({ images: unique });
  },

  _buildPriceChannels(priceStocks) {
    const channels = [];
    const countryMap = {};
    let jpPrice = 0, jpCnyPrice = 0;
    let krPrice = 0, krCnyPrice = 0;

    for (const ps of priceStocks) {
      const cc = ps.countryCode;
      const countryInfo = COUNTRIES.find(c => c.code === cc) || { 
        name: cc, flag: '', currencySymbol: '' 
      };
      
      const cny = ps.cnyPrice || Math.round(ps.localPrice / this._getRate(cc));
      const isAvailable = ps.stockStatus === 'available';
      const storeName = ps.storeInfo ? ps.storeInfo.storeName : '';
      const city = ps.storeInfo ? ps.storeInfo.city : '';

      // 按 countryCode 聚合：优先选有货 + 非官网的门店
      if (!countryMap[cc]) {
        countryMap[cc] = {
          countryCode: cc,
          countryName: countryInfo.name,
          flag: countryInfo.flag,
          localPrice: ps.localPrice,
          priceStr: this._formatPrice(ps.localPrice),
          currency: ps.currency,
          cny: cny,
          cnyStr: this._formatPrice(cny),
          inStock: isAvailable,
          storeName: storeName === '日本官网' ? '日本官网' : (storeName || ''),
          city: city,
          _score: (isAvailable ? 100 : 0) + (storeName && storeName !== '日本官网' ? 10 : 0)
        };
      } else {
        // 如果现有记录的"分数"更低，替换
        const existing = countryMap[cc];
        const newScore = (isAvailable ? 100 : 0) + (storeName && storeName !== '日本官网' ? 10 : 0);
        if (newScore > existing._score) {
          countryMap[cc] = {
            countryCode: cc,
            countryName: countryInfo.name,
            flag: countryInfo.flag,
            localPrice: ps.localPrice,
            priceStr: this._formatPrice(ps.localPrice),
            currency: ps.currency,
            cny: cny,
            cnyStr: this._formatPrice(cny),
            inStock: isAvailable,
            storeName: storeName === '日本官网' ? '日本官网' : (storeName || ''),
            city: city,
            _score: newScore
          };
        }
      }

      if (cc === 'JP' && isAvailable) {
        jpPrice = ps.localPrice;
        jpCnyPrice = cny;
      }
      if (cc === 'KR' && isAvailable) {
        krPrice = ps.localPrice;
        krCnyPrice = cny;
      }
    }

    // 按人民币价格排序
    for (const cc in countryMap) {
      channels.push(countryMap[cc]);
    }
    channels.sort((a, b) => a.cny - b.cny);
    if (channels.length > 0) channels[0].isLowest = true;

    this.setData({
      jpPrice,
      jpCnyPrice,
      jpCnyStr: this._formatPrice(jpCnyPrice),
      krPrice,
      krCnyPrice,
      krCnyStr: this._formatPrice(krCnyPrice),
      priceChannels: channels,
      lowestCny: channels.length > 0 ? channels[0].cny : 0,
      lowestCnyStr: channels.length > 0 ? channels[0].cnyStr : '0',
      currentPriceStr: this._formatPrice(jpCnyPrice || (channels.length > 0 ? channels[0].cny : 0))
    });
  },

  _buildInventories(priceStocks) {
    if (!priceStocks || !Array.isArray(priceStocks)) {
      this.setData({ jpInventories: [], krInventories: [], inventories: [] });
      return;
    }

    const jpMap = new Map();
    const krMap = new Map();
    let skippedOnline = 0;

    for (const ps of priceStocks) {
      if (!ps) continue;
      const storeInfo = ps.storeInfo || {};
      const storeName = storeInfo.storeName || '';
      const city = storeInfo.city || '';
      
      // 跳过线上渠道（日本官网）
      if (storeName === '日本官网') {
        skippedOnline++;
        continue;
      }
      
      // 跳过没有门店名的记录
      if (!storeName) continue;
      
      const key = `${city}_${storeName}`;
      const inv = {
        countryCode: ps.countryCode || '',
        city,
        storeName,
        address: storeInfo.address || '',
        stockStatus: ps.stockStatus || 'out_of_stock',
        inStock: ps.stockStatus === 'available',
      };

      if (ps.countryCode === 'JP') {
        if (!jpMap.has(key)) jpMap.set(key, inv);
      } else if (ps.countryCode === 'KR') {
        if (!krMap.has(key)) krMap.set(key, inv);
      }
    }

    const jpInventories = Array.from(jpMap.values());
    const krInventories = Array.from(krMap.values());

    console.log('[ inventories ] total:', priceStocks.length, 'skipped online:', skippedOnline, 'JP stores:', jpInventories.length, 'KR stores:', krInventories.length);

    this.setData({
      jpInventories,
      krInventories,
      inventories: [...jpInventories, ...krInventories]
    });
  },

  _buildSourceUrls(product) {
    const productId = product.productId || this.data.productId;
    const sourceUrl = product.sourceUrl || product.source_url || '';
    const jpUrl = `https://jp.louisvuitton.com/jpn-jp/products/${productId.toLowerCase()}`;
    const krUrl = `https://kr.louisvuitton.com/kr-kr/products/${productId.toLowerCase()}`;
    
    this.setData({ sourceUrl, jpUrl, krUrl });
  },

  _updateNavTitle(product) {
    const title = this.data.displayName || product.nameCn || '商品详情';
    wx.setNavigationBarTitle({ title });
  },

  _getRate(countryCode) {
    const rates = this.data.exchangeRates;
    // countryCode 是 JP/KR，汇率 key 是 JPY/KRW
    const rateKey = countryCode === 'JP' ? 'JPY' : countryCode === 'KR' ? 'KRW' : countryCode;
    if (rates && rates.rates && rates.rates[rateKey]) {
      return rates.rates[rateKey];
    }
    if (countryCode === 'JP') return DEFAULT_JP_RATE;
    if (countryCode === 'KR') return DEFAULT_KRW_RATE;
    return 1;
  },

  _formatPrice(num) {
    if (!num) return '0';
    return String(Math.round(num)).replace(/\B(?=(\d{3})+(?!\d))/g, ',');
  },

  // 交互方法
  onImageSwiper(e) {
    this.setData({ imageIndex: e.detail.current });
  },

  toggleChannelExpand(e) {
    const index = e.currentTarget.dataset.index;
    this.setData({
      expandedChannel: this.data.expandedChannel === index ? -1 : index
    });
  },

  switchCountry(e) {
    const country = e.currentTarget.dataset.country;
    this.setData({ activeCountry: country });
  },

  toggleInventoryExpand() {
    this.setData({ inventoryExpanded: !this.data.inventoryExpanded });
  },

  toggleFavorite() {
    const { isFavorited, productId } = this.data;
    const newStatus = !isFavorited;
    this.setData({ isFavorited: newStatus });

    // 本地存储（快速响应）
    const favorites = wx.getStorageSync('favorites') || [];
    if (newStatus) {
      if (!favorites.includes(productId)) favorites.push(productId);
    } else {
      const idx = favorites.indexOf(productId);
      if (idx > -1) favorites.splice(idx, 1);
    }
    wx.setStorageSync('favorites', favorites);

    // 云端同步（异步，不阻塞）
    if (wx.cloud && wx.cloud.callFunction) {
      wx.cloud.callFunction({
        name: 'userAction',
        data: { action: 'toggleFavorite', productId }
      }).catch(() => {});
    }

    wx.showToast({
      title: newStatus ? '已收藏' : '已取消收藏',
      icon: 'none'
    });
  },

  checkFavorite() {
    const { productId } = this.data;
    if (!productId) return;
    
    // 先从本地缓存读取
    const favorites = wx.getStorageSync('favorites') || [];
    this.setData({ isFavorited: favorites.includes(productId) });

    // 从云端同步最新状态
    if (wx.cloud && wx.cloud.callFunction) {
      wx.cloud.callFunction({
        name: 'userAction',
        data: { action: 'getFavorites' }
      }).then(res => {
        if (res.result && res.result.code === 0) {
          const cloudFavs = res.result.data || [];
          // 合并云端收藏到本地
          const merged = [...new Set([...favorites, ...cloudFavs])];
          wx.setStorageSync('favorites', merged);
          this.setData({ isFavorited: merged.includes(productId) });
        }
      }).catch(() => {});
    }

    // 检查对比状态
    this.checkCompare();

    // 添加浏览历史
    if (productId && wx.cloud && wx.cloud.callFunction) {
      wx.cloud.callFunction({
        name: 'userAction',
        data: { action: 'addHistory', productId }
      }).catch(() => {});
    }
  },

  checkCompare() {
    const { productId } = this.data;
    if (!productId) return;
    const local = wx.getStorageSync('compareList') || [];
    if (local.includes(productId)) {
      this.setData({ inCompare: true });
      return;
    }
    dataService.getCompareList().then(res => {
      const list = (res && (res.data || res.list || res)) || [];
      const ids = list.length > 0 && typeof list[0] === 'string' ? list : list.map(p => p.productId);
      const merged = [...new Set([...local, ...ids])];
      wx.setStorageSync('compareList', merged);
      this.setData({ inCompare: merged.includes(productId) });
    }).catch(() => {
      this.setData({ inCompare: local.includes(productId) });
    });
  },

  copyLink() {
    const url = this.data.sourceUrl || this.data.jpUrl;
    if (url) {
      wx.setClipboardData({
        data: url,
        success: () => {
          wx.showToast({ title: '链接已复制', icon: 'none' });
        }
      });
    }
  },

  calculateFinalPrice() {
    const { productId } = this.data;
    if (!productId) return;
    
    // rebate 是 tabBar 页面，不能用 navigateTo
    // 用全局变量传递 productId，在 rebate 的 onShow 中读取
    app.globalData.pendingProductId = productId;
    wx.switchTab({
      url: '/pages/rebate/rebate'
    });
  },

  goBack() {
    wx.navigateBack({ delta: 1 });
  },

  onShareAppMessage() {
    const { displayName, mainImage, productId, jpCnyStr, cnPriceStr } = this.data;
    const priceStr = jpCnyStr || cnPriceStr || '';
    return {
      title: `${displayName || 'LV商品'}${priceStr ? ` · ¥${priceStr}` : ''}`,
      path: `/pages/product-detail/product-detail?id=${productId}`,
      imageUrl: mainImage || ''
    };
  },

  onShareTimeline() {
    const { displayName, mainImage, productId, jpCnyStr, cnPriceStr } = this.data;
    const priceStr = jpCnyStr || cnPriceStr || '';
    return {
      title: `${displayName || 'LV商品'}${priceStr ? ` · ¥${priceStr}` : ''}`,
      query: `id=${productId}`,
      imageUrl: mainImage || ''
    };
  },

  showAddCompare() {
    const { productId, inCompare } = this.data;
    if (!productId) return;
    if (inCompare) {
      // 移除对比
      const local = wx.getStorageSync('compareList') || [];
      const newList = local.filter(id => id !== productId);
      wx.setStorageSync('compareList', newList);
      dataService.removeFromCompare(productId).catch(() => {});
      this.setData({ inCompare: false });
      wx.showToast({ title: '已移出对比', icon: 'none' });
      return;
    }
    dataService.addToCompare(productId).then(res => {
      if (res && res.code === 0) {
        const local = wx.getStorageSync('compareList') || [];
        if (!local.includes(productId)) local.push(productId);
        wx.setStorageSync('compareList', local);
        this.setData({ inCompare: true });
        wx.showModal({
          title: '已加入对比',
          content: '商品已加入对比清单，是否立即查看？',
          confirmText: '去对比',
          cancelText: '继续浏览',
          success: (r) => {
            if (r.confirm) {
              wx.navigateTo({ url: '/pages/compare/compare' });
            }
          }
        });
      } else if (res && res.code === 4001) {
        wx.showModal({
          title: '对比清单已满',
          content: res.message || '最多支持3个商品同时对比，请先移除后再添加。',
          confirmText: '管理对比',
          cancelText: '知道了',
          success: (r) => {
            if (r.confirm) {
              wx.navigateTo({ url: '/pages/compare/compare' });
            }
          }
        });
      } else {
        wx.showToast({ title: (res && res.message) || '添加失败', icon: 'none' });
      }
    }).catch(() => {
      wx.showToast({ title: '添加失败，请稍后重试', icon: 'none' });
    });
  },

  showPriceAlert() {
    const { currentPriceStr, jpCnyPrice } = this.data;
    // 默认目标价设为当前价的 9 折
    const defaultTarget = jpCnyPrice ? Math.round(jpCnyPrice * 0.9) : '';
    this.setData({
      showAlertDialog: true,
      currentPriceStr,
      targetPriceInput: defaultTarget ? String(defaultTarget) : ''
    });
  },

  closeAlertDialog() {
    this.setData({ showAlertDialog: false });
  },

  onTargetPriceInput(e) {
    this.setData({ targetPriceInput: e.detail.value });
  },

  confirmPriceAlert() {
    const { productId, targetPriceInput, jpCnyPrice } = this.data;
    const targetPrice = parseInt(targetPriceInput, 10);
    if (!targetPrice || targetPrice <= 0) {
      wx.showToast({ title: '请输入有效的目标价格', icon: 'none' });
      return;
    }
    if (jpCnyPrice && targetPrice >= jpCnyPrice) {
      wx.showModal({
        title: '价格提醒设置提示',
        content: `您设置的目标价 ¥${targetPrice} 高于或等于当前到手价 ¥${jpCnyPrice}，是否仍要设置？`,
        success: (r) => {
          if (r.confirm) this._submitPriceAlert(targetPrice);
        }
      });
      return;
    }
    this._submitPriceAlert(targetPrice);
  },

  _submitPriceAlert(targetPrice) {
    const { productId } = this.data;
    dataService.addPriceAlert(productId, targetPrice).then(res => {
      if (res && res.code === 0) {
        this.setData({ showAlertDialog: false });
        wx.showToast({ title: '已开启降价提醒', icon: 'success' });
      } else {
        wx.showToast({ title: (res && res.message) || '设置失败', icon: 'none' });
      }
    }).catch(() => {
      wx.showToast({ title: '设置失败，请稍后重试', icon: 'none' });
    });
  }
});
