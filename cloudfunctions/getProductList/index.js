// getProductList - 获取商品列表 / 品牌列表
// _method: 'list' | 'brands'

const cloud = require('wx-server-sdk');
cloud.init({ env: cloud.DYNAMIC_CURRENT_ENV });

const db = cloud.database();
const _ = db.command;

const FALLBACK_RATES = { CNY: 1, JPY: 21.58, KRW: 192.5 };

// 从 exchange_rates 集合读取最新汇率（getExchangeRates 每次抓取后写入）
// 未找到时使用内置兜底，保证接口可用
async function getLatestRates() {
  try {
    const res = await db.collection('exchange_rates')
      .orderBy('updateTime', 'desc')
      .limit(1)
      .get();
    if (res.data && res.data.length > 0 && res.data[0].rates) {
      const r = res.data[0].rates;
      return { CNY: 1, JPY: r.JPY || FALLBACK_RATES.JPY, KRW: r.KRW || FALLBACK_RATES.KRW };
    }
  } catch (e) {
    // 集合不存在等错误，走兜底
  }
  return FALLBACK_RATES;
}

// 非包包类商品关键词黑名单（slug 中包含这些词的都不是包包）
// 与 importAllData 保持一致，作为防御性兜底过滤
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

// 部分商品数据源仅捕获韩文名（nameKr），中/日/英名为空。
// 优先从韩文名括号内提取英文名（如 "알마 PM (Alma PM)" -> "Alma PM"），
// 其次从主图URL文件名的规范slug提取（无需重新爬数据即可补齐显示名称）。
function deriveEnName(p) {
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
}

// 名称兜底：三语全空时利用 nameKr/URL 推导英文名，保证列表与详情都有名称可展示
function resolveNames(p) {
  const nameCn = p.nameCn || '';
  const nameJp = p.nameJp || '';
  let nameEn = p.nameEn || '';
  if (!nameCn && !nameJp && !nameEn) {
    nameEn = deriveEnName(p);
  }
  return { nameCn, nameJp, nameEn };
}

exports.main = async (event, context) => {
  const { _method = 'list', keyword = '', brandId = '', sort = 'default', page = 1, pageSize = 20 } = event;

  try {
    // 品牌列表
    if (_method === 'brands') {
      const productsRes = await db.collection('products')
        .field({ brandId: true, brandName: true })
        .limit(1000)
        .get();

      const brandMap = {};
      productsRes.data.forEach(p => {
        if (p.brandId && !brandMap[p.brandId]) {
          brandMap[p.brandId] = {
            brandId: p.brandId,
            brandName: p.brandName || p.brandId,
            count: 1
          };
        } else if (p.brandId) {
          brandMap[p.brandId].count++;
        }
      });

      const brands = Object.values(brandMap);
      return { code: 0, data: brands };
    }

    // 商品列表
    const productsCol = db.collection('products');
    const priceStockCol = db.collection('price_stock');
    
    // 固定只查询包包类商品
    let query = { category: 'handbag' };

    if (keyword) {
      query = _.and([
        { category: 'handbag' },
        _.or(
          { nameCn: db.RegExp({ regexp: keyword, options: 'i' }) },
          { nameEn: db.RegExp({ regexp: keyword, options: 'i' }) },
          { nameJp: db.RegExp({ regexp: keyword, options: 'i' }) },
          { productId: db.RegExp({ regexp: keyword, options: 'i' })},
          { slug: db.RegExp({ regexp: keyword, options: 'i' })}
        )
      ]);
    }

    if (brandId && brandId !== 'all') {
      query.brandId = brandId;
    }

    // 拉取全部匹配商品（数据量约100条，可一次性拉取）
    // 先在内存中用 slug 黑名单过滤非包包商品，再排序和分页
    const allRes = await productsCol.where(query).limit(1000).get();
    
    // 防御性兜底：用 slug 黑名单过滤掉非包包商品
    const handbagProducts = allRes.data.filter(isHandbag);
    
    // 按 slug 去重：同一 slug 只保留一个，优先保留有图片的
    const slugMap = {};
    for (const p of handbagProducts) {
      const key = p.slug || p.productId || '';
      if (!key) continue;
      if (!slugMap[key]) {
        slugMap[key] = p;
      } else if (p.mainImage && !slugMap[key].mainImage) {
        // 已有记录无图，但当前有图，替换
        slugMap[key] = p;
      }
    }
    const filteredProducts = Object.values(slugMap);
    const totalCount = filteredProducts.length;

    // 内存排序
    if (sort === 'price-asc') {
      filteredProducts.sort((a, b) => (a.cnOfficialPrice || 0) - (b.cnOfficialPrice || 0));
    } else if (sort === 'price-desc') {
      filteredProducts.sort((a, b) => (b.cnOfficialPrice || 0) - (a.cnOfficialPrice || 0));
    } else {
      // 默认按 productId 降序
      filteredProducts.sort((a, b) => (b.productId || '').localeCompare(a.productId || ''));
    }

    // 内存分页
    const startIdx = (page - 1) * pageSize;
    const products = filteredProducts.slice(startIdx, startIdx + pageSize);

    // 读取最新实时汇率（1 CNY = x 外币），用于动态换算人民币价格
    const latestRates = await getLatestRates();
    const jpyRate = latestRates.JPY || FALLBACK_RATES.JPY;
    const krwRate = latestRates.KRW || FALLBACK_RATES.KRW;

    // 直接使用 products 集合中冗余存储的价格字段（避免 price_stock 的 100 条限制）
    const list = products.map(p => {
      const cnOfficialPrice = p.cnOfficialPrice || 0;
      const hasCnPrice = p.hasCnPrice || cnOfficialPrice > 0;
      // 真实来源判定：数据库 jpCnyPrice/krCnyPrice 已按 source_jp/source_kr 生成（为0表示官网无真实在售价，如推算价）
      // 有真实价格时用最新汇率动态换算，避免旧汇率失真
      const hasJp = (p.jpCnyPrice || 0) > 0;
      const hasKr = (p.krCnyPrice || 0) > 0;
      let jpCnyPrice = 0;
      if (hasJp && p.jpPrice && p.jpPrice > 0 && jpyRate > 0) {
        jpCnyPrice = Math.round(p.jpPrice / jpyRate);
      } else {
        jpCnyPrice = 0;
      }
      let krCnyPrice = 0;
      if (hasKr && p.krPrice && p.krPrice > 0 && krwRate > 0) {
        krCnyPrice = Math.round(p.krPrice / krwRate);
      } else {
        krCnyPrice = 0;
      }
      // 动态计算比价国家/最优价/最优国家，不信任数据库冗余旧值（可能与实时汇率不一致）
      const priceEntries = [];
      if (hasCnPrice) priceEntries.push({ country: 'CN', price: cnOfficialPrice });
      if (jpCnyPrice > 0) priceEntries.push({ country: 'JP', price: jpCnyPrice });
      if (krCnyPrice > 0) priceEntries.push({ country: 'KR', price: krCnyPrice });
      priceEntries.sort((a, b) => a.price - b.price);
      const bestGlobalPrice = priceEntries.length > 0 ? priceEntries[0].price : 0;
      const bestCountry = priceEntries.length > 0 ? priceEntries[0].country : '';
      const countryCount = priceEntries.length;
      const countries = priceEntries.map(e => e.country);

      const names = resolveNames(p);
      return {
        productId: p.productId,
        nameCn: names.nameCn,
        nameJp: names.nameJp,
        nameEn: names.nameEn,
        mainImage: p.mainImage || (p.images && p.images[0]) || '',
        images: (p.images && p.images.length > 0) ? p.images : (p.mainImage ? [p.mainImage] : []),
        cnOfficialPrice: cnOfficialPrice,
        hasCnPrice,
        category: p.category || '',
        brandId: p.brandId || '',
        brandName: p.brandName || 'Louis Vuitton',
        jpPrice: p.jpPrice || 0,
        jpCnyPrice: jpCnyPrice,
        krPrice: p.krPrice || 0,
        krCnyPrice: krCnyPrice,
        bestGlobalPrice,
        bestCountry,
        countries: countries,
        countryCount
      };
    });

    return {
      code: 0,
      data: {
        list,
        total: totalCount
      }
    };
  } catch (err) {
    console.error('getProductList error:', err);
    return { code: -1, message: '获取数据失败: ' + err.message };
  }
};
