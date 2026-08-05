// importProducts - 批量导入商品和价格库存数据
// 用于将爬虫抓取的数据批量导入到云数据库

const cloud = require('wx-server-sdk');
cloud.init({ env: cloud.DYNAMIC_CURRENT_ENV });

const db = cloud.database();
const _ = db.command;

const BATCH_SIZE = 20;

async function batchInsert(collection, docs) {
  const results = [];
  for (let i = 0; i < docs.length; i += BATCH_SIZE) {
    const batch = docs.slice(i, i + BATCH_SIZE);
    const tasks = batch.map(doc => 
      collection.add({ data: doc }).then(res => ({ success: true, id: res._id }))
        .catch(err => ({ success: false, error: err.message }))
    );
    const batchResults = await Promise.all(tasks);
    results.push(...batchResults);
  }
  return results;
}

exports.main = async (event, context) => {
  const { action = 'import', products = [], priceStocks = [], clearExisting = false } = event;

  try {
    if (action === 'clear-only') {
      const productsCol = db.collection('products');
      const priceStockCol = db.collection('price_stock');

      // 清空集合
      let offset = 0;
      while (true) {
        const res = await productsCol.skip(offset).limit(100).get();
        if (res.data.length === 0) break;
        for (const doc of res.data) {
          await productsCol.doc(doc._id).remove();
        }
        offset += 100;
        if (offset >= 10000) break;
      }

      offset = 0;
      while (true) {
        const res = await priceStockCol.skip(offset).limit(100).get();
        if (res.data.length === 0) break;
        for (const doc of res.data) {
          await priceStockCol.doc(doc._id).remove();
        }
        offset += 100;
        if (offset >= 10000) break;
      }

      return { code: 0, message: '已清空 products 和 price_stock 集合' };
    }

    // 如果指定清除现有数据
    if (clearExisting) {
      const productsCol = db.collection('products');
      const priceStockCol = db.collection('price_stock');

      let offset = 0;
      while (true) {
        const res = await productsCol.skip(offset).limit(100).get();
        if (res.data.length === 0) break;
        for (const doc of res.data) {
          await productsCol.doc(doc._id).remove();
        }
        offset += 100;
        if (offset >= 10000) break;
      }

      offset = 0;
      while (true) {
        const res = await priceStockCol.skip(offset).limit(100).get();
        if (res.data.length === 0) break;
        for (const doc of res.data) {
          await priceStockCol.doc(doc._id).remove();
        }
        offset += 100;
        if (offset >= 10000) break;
      }
    }

    // 准备商品数据
    const productsCol = db.collection('products');
    const priceStockCol = db.collection('price_stock');

    const productDocs = products.map(p => ({
      productId: p.productId || '',
      slug: p.slug || '',
      nameCn: p.nameCn || '',
      nameEn: p.nameEn || '',
      mainImage: p.mainImage || '',
      images: p.images || [],
      cnOfficialPrice: p.cnOfficialPrice || 0,
      category: p.category || 'handbag',
      brandId: p.brandId || 'b001',
      brandName: p.brandName || 'Louis Vuitton',
      dimensions: p.dimensions || {},
      createTime: db.serverDate()
    }));

    const priceStockDocs = priceStocks.map(ps => ({
      productId: ps.productId || '',
      countryCode: ps.countryCode || '',
      localPrice: ps.localPrice || 0,
      currency: ps.currency || '',
      cnyPrice: ps.cnyPrice || 0,
      stockStatus: ps.stockStatus || 'available',
      storeInfo: ps.storeInfo || {},
      priceUpdateTime: db.serverDate()
    }));

    // 批量导入
    const productResults = await batchInsert(productsCol, productDocs);
    const priceResults = await batchInsert(priceStockCol, priceStockDocs);

    const productSuccess = productResults.filter(r => r.success).length;
    const priceSuccess = priceResults.filter(r => r.success).length;

    return {
      code: 0,
      message: '导入完成',
      products: { total: productDocs.length, success: productSuccess, failed: productDocs.length - productSuccess },
      priceStocks: { total: priceStockDocs.length, success: priceSuccess, failed: priceStockDocs.length - priceSuccess }
    };
  } catch (err) {
    console.error('importProducts error:', err);
    return { code: -1, message: '导入失败: ' + err.message };
  }
};
