// scripts/upload_to_cloud.js
// 读取 import_products.json 和 import_price_stock.json，生成云函数调用载荷
// 用法：node scripts/upload_to_cloud.js

const fs = require('fs');
const path = require('path');

const DATA_DIR = path.join(__dirname, '..', 'data');
const CHUNK_SIZE = 30;

function loadJSON(filename) {
  const filepath = path.join(DATA_DIR, filename);
  if (!fs.existsSync(filepath)) {
    console.error(`文件不存在: ${filepath}`);
    process.exit(1);
  }
  return JSON.parse(fs.readFileSync(filepath, 'utf-8'));
}

function chunkArray(arr, size) {
  const chunks = [];
  for (let i = 0; i < arr.length; i += size) {
    chunks.push(arr.slice(i, i + size));
  }
  return chunks;
}

function main() {
  console.log('读取导入数据...');
  const products = loadJSON('import_products.json');
  const priceStocks = loadJSON('import_price_stock.json');

  console.log(`商品数: ${products.length}`);
  console.log(`价格库存数: ${priceStocks.length}`);

  // 按 productId 分组价格库存
  const psMap = {};
  for (const ps of priceStocks) {
    if (!psMap[ps.productId]) psMap[ps.productId] = [];
    psMap[ps.productId].push(ps);
  }

  // 生成导入批次
  const productChunks = chunkArray(products, CHUNK_SIZE);
  const batches = [];

  for (let i = 0; i < productChunks.length; i++) {
    const chunkProducts = productChunks[i];
    const chunkProductIds = chunkProducts.map(p => p.productId);
    const chunkPriceStocks = [];
    
    for (const pid of chunkProductIds) {
      if (psMap[pid]) {
        chunkPriceStocks.push(...psMap[pid]);
      }
    }

    batches.push({
      batchIndex: i + 1,
      totalBatches: productChunks.length,
      products: chunkProducts,
      priceStocks: chunkPriceStocks
    });
  }

  // 输出每个批次的概要
  console.log(`\n总共 ${batches.length} 个导入批次:`);
  for (const batch of batches) {
    console.log(`  批次 ${batch.batchIndex}/${batch.totalBatches}: ${batch.products.length} 商品, ${batch.priceStocks.length} 价格库存`);
  }

  // 保存批次文件
  const outputDir = path.join(DATA_DIR, 'import_batches');
  if (!fs.existsSync(outputDir)) {
    fs.mkdirSync(outputDir, { recursive: true });
  }

  for (const batch of batches) {
    const filename = `batch_${String(batch.batchIndex).padStart(3, '0')}.json`;
    const filepath = path.join(outputDir, filename);
    // 只保存 products 和 priceStocks，不含元数据
    const payload = {
      products: batch.products,
      priceStocks: batch.priceStocks
    };
    fs.writeFileSync(filepath, JSON.stringify(payload, null, 2));
  }

  console.log(`\n批次文件已生成到: ${outputDir}`);
  console.log('\n========================================');
  console.log('导入步骤:');
  console.log('1. 上传并部署 importProducts 云函数');
  console.log('2. 在云开发控制台 -> 云函数 -> importProducts -> 测试');
  console.log('3. 将每个批次的 JSON 内容作为测试参数传入');
  console.log('   格式: { "products": [...], "priceStocks": [...] }');
  console.log('4. 或使用 action: "clear-only" 先清空再逐批导入');
  console.log('========================================');
}

main();
