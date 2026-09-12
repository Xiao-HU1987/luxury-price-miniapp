/**
 * 云数据库导入辅助脚本
 * 
 * 使用方法：
 * 1. 在微信开发者工具中打开项目
 * 2. 将 chunk JSON 文件上传到云存储（例如 cloud://your-env.xxx/import/）
 * 3. 在开发者工具控制台中粘贴并运行此脚本
 * 
 * 注意：需要先将 cloud:// 开头的 fileID 替换为实际值
 */

// ============================================================
// 配置：将下面的 fileIDs 替换为实际的云存储文件 ID
// ============================================================
const CHUNK_FILE_IDS = [
  // 例如: 'cloud://your-env-id.xxx/import/import_chunk_000.json'
  // 请在上传文件到云存储后，替换为实际的文件 ID
];

// 是否首次导入时清空现有数据
const CLEAR_ON_FIRST = true;

// ============================================================
// 导入逻辑
// ============================================================
async function importAllChunks() {
  if (CHUNK_FILE_IDS.length === 0) {
    console.error('❌ 请先设置 CHUNK_FILE_IDS 数组！');
    return;
  }

  console.log(`🚀 开始导入 ${CHUNK_FILE_IDS.length} 个 chunk...`);
  const startTime = Date.now();
  const results = [];

  for (let i = 0; i < CHUNK_FILE_IDS.length; i++) {
    const fileID = CHUNK_FILE_IDS[i];
    console.log(`\n📦 [${i + 1}/${CHUNK_FILE_IDS.length}] 导入: ${fileID}`);
    
    try {
      const res = await wx.cloud.callFunction({
        name: 'importAllData',
        data: {
          action: 'import-from-storage',
          fileID: fileID,
          partIndex: i,
          clear: (i === 0 && CLEAR_ON_FIRST)
        }
      });
      
      const r = res.result;
      console.log(`  ✅ 商品: ${r.dedupedProducts} 个, 价格库存: ${r.dedupedPriceStocks} 条`);
      console.log(`  📝 写入: ${r.products?.inserted} products, ${r.priceStocks?.inserted} priceStocks`);
      results.push(r);
    } catch (e) {
      console.error(`  ❌ 失败: ${e.message}`);
      results.push({ error: e.message });
    }
  }

  const elapsed = ((Date.now() - startTime) / 1000).toFixed(1);
  const totalProducts = results.reduce((s, r) => s + (r.dedupedProducts || 0), 0);
  const totalPS = results.reduce((s, r) => s + (r.dedupedPriceStocks || 0), 0);
  
  console.log(`\n========================================`);
  console.log(`🎉 导入完成! 耗时 ${elapsed}s`);
  console.log(`📊 总计: ${totalProducts} 商品, ${totalPS} 价格库存`);
  console.log(`========================================`);
}

// 运行导入
importAllChunks().catch(e => console.error('导入异常:', e));