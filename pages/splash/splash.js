// 启动页 - 展示Logo/插屏广告后跳转首页
// 广告位需在微信公众平台「流量主」开通插屏广告后获得 adUnitId
// 未配置广告位时自动回退为普通启动页，不影响使用

const INTERSTITIAL_AD_UNIT_ID = ''; // TODO: 开通流量主后填入插屏广告位ID

Page({
  data: {
    statusBarHeight: 20
  },

  onLoad() {
    const sysInfo = wx.getSystemInfoSync();
    this.setData({ statusBarHeight: sysInfo.statusBarHeight || 20 });

    // 有广告位ID则尝试展示插屏广告，否则直接跳转
    if (INTERSTITIAL_AD_UNIT_ID) {
      this._showInterstitialAd();
    } else {
      this._jumpAfterDelay();
    }
  },

  _showInterstitialAd() {
    const that = this;
    let interstitialAd = null;

    // 初始化插屏广告
    try {
      if (wx.createInterstitialAd) {
        interstitialAd = wx.createInterstitialAd({ adUnitId: INTERSTITIAL_AD_UNIT_ID });
      }
    } catch (e) {
      // 初始化失败则直接跳转
      this._jumpAfterDelay();
      return;
    }

    if (!interstitialAd) {
      this._jumpAfterDelay();
      return;
    }

    // 监听关闭后跳转
    interstitialAd.onClose(() => {
      that._jumpAfterDelay();
    });
    interstitialAd.onError(() => {
      that._jumpAfterDelay();
    });

    // 展示广告，失败则直接跳转
    interstitialAd.show().catch(() => {
      that._jumpAfterDelay();
    });

    // 兜底：广告最多停留 5 秒，超时强制跳转
    setTimeout(() => {
      that._jumpAfterDelay();
    }, 5000);
  },

  _jumpAfterDelay() {
    wx.switchTab({ url: '/pages/index/index' });
  }
});