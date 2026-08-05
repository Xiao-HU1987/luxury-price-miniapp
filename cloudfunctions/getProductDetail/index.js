// getProductDetail - 获取商品详情
// 返回格式匹配规范：{ product, priceStocks }

const cloud = require('wx-server-sdk');
cloud.init({ env: cloud.DYNAMIC_CURRENT_ENV });

const db = cloud.database();

const JPY_RATE = 21.58;
const KRW_RATE = 192.5;

// 非包包类商品关键词黑名单（与 importAllData/getProductList 保持一致）
const NON_BAG_KEYWORDS = [
  'sunglass', 'sneaker', 'jacket', 'knit-top', 'blanket',
  'card-holder', 'key-pouch', 'babies', 'wallet-on-chain',
  'scarf', 'belt', 'hat', 'glove', 'jewelry', 'watch',
  'ring', 'necklace', 'earring', 'bracelet',
  'shoe', 'sandal', 'boot', 'shirt', 'pant', 'dress',
  'skirt', 'coat', 'swimwear', 'umbrella', 'phone-case',
  'airpods', 'mask', 'pet', 'baby', 'toy', 'book',
  'pen', 'notebook', 'agenda', 'planner',
];

// 判断商品是否为包包类（通过 slug 黑名单排除）
function isHandbag(product) {
  const slug = (product.slug || '').toLowerCase();
  for (const keyword of NON_BAG_KEYWORDS) {
    if (slug.includes(keyword)) {
      return false;
    }
  }
  return true;
}

exports.main = async (event, context) => {
  const { productId } = event;

  if (!productId) {
    return { code: -1, message: '缺少商品ID' };
  }

  try {
    // 获取商品主数据
    const productRes = await db.collection('products')
      .where({ productId })
      .limit(1)
      .get();

    if (!productRes.data || productRes.data.length === 0) {
      return { code: -1, message: '商品不存在' };
    }

    const p = productRes.data[0];

    // 分类校验：通过 slug 黑名单排除非包包类商品
    if (!isHandbag(p)) {
      return { code: -1, message: '该商品非包包类，不支持查看' };
    }

    // 构建商品信息（规范字段）
    const product = {
      productId: p.productId,
      slug: p.slug || '',
      nameCn: p.nameCn || '',
      nameJp: p.nameJp || '',
      nameEn: p.nameEn || '',
      mainImage: p.mainImage || '',
      images: p.images || (p.mainImage ? [p.mainImage] : []),
      cnOfficialPrice: p.cnOfficialPrice || 0,
      category: p.category || '',
      brandId: p.brandId || '',
      brandName: 'Louis Vuitton',
      createTime: p.createTime || '',
      updateTime: p.updateTime || ''
    };

    // 获取所有价格和库存
    const priceStockRes = await db.collection('price_stock')
      .where({ productId })
      .get();

    // 构建价格库存列表（规范字段）
    const priceStocks = priceStockRes.data.map(ps => ({
      productId: ps.productId,
      countryCode: ps.countryCode,
      localPrice: ps.localPrice,
      currency: ps.currency,
      cnyPrice: ps.cnyPrice || Math.round(ps.localPrice / (ps.currency === 'JPY' ? JPY_RATE : ps.currency === 'KRW' ? KRW_RATE : 1)),
      stockStatus: ps.stockStatus,
      storeInfo: ps.storeInfo || { city: '', storeName: '', address: '' },
      priceUpdateTime: ps.updateTime || ps.createTime || ''
    }));

    return {
      code: 0,
      data: {
        product,
        priceStocks
      }
    };
  } catch (err) {
    console.error('getProductDetail error:', err);
    return { code: -1, message: '获取详情失败: ' + err.message };
  }
};
