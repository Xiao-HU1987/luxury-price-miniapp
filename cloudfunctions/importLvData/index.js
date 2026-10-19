/**
 * 一键导入 LV 整合数据（从云存储读取）
 * 
 * 使用方法：
 * 1. 将 import_chunk_000.json ~ import_chunk_011.json 上传到云存储
 * 2. 在云存储控制台复制每个文件的 fileID
 * 3. 在微信开发者工具控制台调用：
 *    wx.cloud.callFunction({ 
 *      name: 'importLvData', 
 *      data: { 
 *        clear: true,
 *        fileIDs: ['cloud://xxx/import_chunk_000.json', ...]
 *      } 
 *    })
 */

const cloud = require('wx-server-sdk');
cloud.init({ env: cloud.DYNAMIC_CURRENT_ENV });
const db = cloud.database();

const BATCH_SIZE = 100;

// 非包包类关键词黑名单
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

function isHandbag(slug) {
  const lower = (slug || '').toLowerCase();
  return !NON_BAG_KEYWORDS.some(kw => lower.includes(kw));
}

async function clearCollection(name) {
  const MAX_LIMIT = 100;
  try {
    const res = await db.collection(name).limit(MAX_LIMIT).get();
    const ids = res.data.map(d => d._id);
    while (ids.length > 0) {
      const batch = ids.splice(0, MAX_LIMIT);
      await Promise.all(batch.map(id =>
        db.collection(name).doc(id).remove().catch(() => {})
      ));
    }
    console.log(`[clear] ${name}: 已清空`);
  } catch (e) {
    console.log(`[clear] ${name}: ${e.message}`);
  }
}

async function batchInsert(name, records) {
  if (!records || records.length === 0) return { added: 0 };
  let added = 0;
  try {
    for (let i = 0; i < records.length; i += BATCH_SIZE) {
      const chunk = records.slice(i, i + BATCH_SIZE);
      await Promise.all(chunk.map(r =>
        db.collection(name).add({ data: r }).catch(e => {
          if (e.errCode === -502003) {
            // 记录已存在，尝试更新
            return db.collection(name).where({ productId: r.productId }).update({ data: r }).catch(() => {});
          }
          console.log(`[batchInsert] 跳过: ${r.productId}, ${e.message}`);
        })
      ));
      added += chunk.length;
    }
  } catch (e) {
    console.log(`[batchInsert] ${name}: ${e.message}`);
  }
  return { added };
}

exports.main = async (event) => {
  const { clear = false, fileIDs = [] } = event;
  const startTime = Date.now();
  const results = [];

  console.log(`[importLvData] 开始导入, clear=${clear}, fileIDs数量=${fileIDs.length}`);

  if (!fileIDs || fileIDs.length === 0) {
    return { code: -1, message: '请传入 fileIDs 参数（云存储文件ID数组）' };
  }

  if (clear) {
    console.log('[importLvData] 清空现有数据...');
    await clearCollection('products');
    await clearCollection('price_stock');
  }

  let totalProducts = 0;
  let totalPriceStocks = 0;

  for (let i = 0; i < fileIDs.length; i++) {
    const fileID = fileIDs[i];
    console.log(`\n[importLvData] [${i + 1}/${fileIDs.length}] 下载: ${fileID}`);

    try {
      const downloadRes = await cloud.downloadFile({ fileID });
      if (!downloadRes || !downloadRes.fileContent) {
        console.log(`  跳过: 文件内容为空`);
        continue;
      }

      const content = downloadRes.fileContent.toString('utf-8');
      const data = JSON.parse(content);
      const products = data.products || [];
      const priceStocks = data.priceStocks || [];

      console.log(`  解析: ${products.length} products, ${priceStocks.length} priceStocks`);

      // 去重
      const slugMap = {};
      for (const p of products) {
        const key = p.slug || p.productId || '';
        if (!key) continue;
        if (!slugMap[key]) {
          slugMap[key] = p;
        } else if (p.mainImage && !slugMap[key].mainImage) {
          slugMap[key] = p;
        }
      }
      const dedupedProducts = Object.values(slugMap);
      const dedupedIds = new Set(dedupedProducts.map(p => p.productId));
      const dedupedPS = priceStocks.filter(ps => dedupedIds.has(ps.productId));

      console.log(`  去重后: ${dedupedProducts.length} products, ${dedupedPS.length} priceStocks`);

      // 分批写入
      const PRODUCT_PART_SIZE = 100;
      let pInserted = 0;
      for (let j = 0; j < dedupedProducts.length; j += PRODUCT_PART_SIZE) {
        const chunk = dedupedProducts.slice(j, j + PRODUCT_PART_SIZE);
        const toInsert = chunk.map(p => ({ ...p, createTime: db.serverDate() }));
        const r = await batchInsert('products', toInsert);
        pInserted += (r && r.added) || chunk.length;
      }

      const PS_PART_SIZE = 200;
      let psInserted = 0;
      for (let j = 0; j < dedupedPS.length; j += PS_PART_SIZE) {
        const chunk = dedupedPS.slice(j, j + PS_PART_SIZE);
        const toInsert = chunk.map(ps => ({ ...ps, priceUpdateTime: db.serverDate() }));
        const r = await batchInsert('price_stock', toInsert);
        psInserted += (r && r.added) || chunk.length;
      }

      console.log(`  写入: ${pInserted} products, ${psInserted} priceStocks`);
      totalProducts += dedupedProducts.length;
      totalPriceStocks += dedupedPS.length;
      results.push({ chunk: i, products: dedupedProducts.length, priceStocks: dedupedPS.length });
    } catch (e) {
      console.log(`  失败: ${e.message}`);
      results.push({ chunk: i, error: e.message });
    }
  }

  const elapsed = ((Date.now() - startTime) / 1000).toFixed(1);
  console.log(`\n[importLvData] 完成! 耗时 ${elapsed}s, 总计 ${totalProducts} products, ${totalPriceStocks} priceStocks`);

  return {
    code: 0,
    message: `导入完成: ${totalProducts} 商品, ${totalPriceStocks} 价格库存`,
    elapsed,
    totalProducts,
    totalPriceStocks,
    results
  };
};