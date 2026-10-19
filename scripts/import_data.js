// scripts/import_data.js
// 一键数据导入脚本：读取爬虫原始数据 → 过滤非包包 → 去重 → 生成导入批次
// 用法：node scripts/import_data.js
// 然后在微信开发者工具中调用 importAllData 云函数（action: all）

const fs = require('fs');
const path = require('path');

const BASE_DIR = path.join(__dirname, '..');
const CAPTURES_DIR = path.join(BASE_DIR, 'server', 'crawler', 'raw_captures');
const OUTPUT_DIR = path.join(BASE_DIR, 'data');
const BATCHES_DIR = path.join(OUTPUT_DIR, 'import_batches');

const JPY_RATE = 0.0462;

const CATEGORY_MAP = {
  'handbag': 'handbag',
  'bag': 'handbag',
  'wallet': 'wallet',
  'small-leather-goods': 'slg',
};

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

function isHandbag(product) {
  const slug = (product.slug || '').toLowerCase();
  const url = (product.url || '').toLowerCase();
  for (const kw of NON_BAG_KEYWORDS) {
    if (slug.includes(kw) || url.includes(kw)) return false;
  }
  return true;
}

function extractSlug(url) {
  if (!url) return '';
  const match = url.match(/\/products\/([^/]+)/);
  return match ? match[1] : '';
}

function extractSkuFiles() {
  if (!fs.existsSync(CAPTURES_DIR)) return [];
  return fs.readdirSync(CAPTURES_DIR)
    .filter(f => f.includes('skus_') && f.endsWith('.json'))
    .map(f => path.join(CAPTURES_DIR, f));
}

function processCaptures() {
  const files = extractSkuFiles();
  console.log(`找到 ${files.length} 个捕获文件`);

  const products = [];
  const priceStocks = [];
  const slugSeen = {};

  for (const filepath of files) {
    try {
      const data = JSON.parse(fs.readFileSync(filepath, 'utf-8'));
      if (!Array.isArray(data)) continue;

      for (const item of data) {
        if (typeof item !== 'object') continue;

        const skuId = item.skuId || '';
        const nameJp = item.name || '';
        const priceRaw = item.priceRaw || 0;
        const medias = item.medias || [];
        const sellable = item.sellable || false;
        const url = item.url || '';
        const slug = extractSlug(url);

        if (!skuId || !slug) continue;

        // 非包包过滤
        const testProduct = { slug, url };
        if (!isHandbag(testProduct)) continue;

        // slug 去重：保留第一个
        if (slugSeen[slug]) continue;
        slugSeen[slug] = skuId;

        // 主图
        let mainImage = '';
        let allImages = [];
        if (Array.isArray(medias)) {
          for (const m of medias) {
            if (m.url) {
              const url = m.url.startsWith('//') ? 'https:' + m.url : m.url;
              allImages.push(url);
            }
          }
          if (allImages.length) mainImage = allImages[0];
        }

        // 分类
        const pathLower = url.toLowerCase();
        let category = 'handbag';
        for (const key of Object.keys(CATEGORY_MAP)) {
          if (pathLower.includes(key)) {
            category = CATEGORY_MAP[key];
            break;
          }
        }

        const jpCny = Math.round(priceRaw * JPY_RATE);

        products.push({
          productId: skuId,
          slug,
          nameCn: nameJp,
          nameEn: '',
          mainImage,
          images: allImages.slice(0, 5),
          cnOfficialPrice: 0,
          category,
          brandId: 'b001',
          brandName: 'Louis Vuitton',
          dimensions: (item.dimensionsData && item.dimensionsData[0]) || {},
          createTime: new Date().toISOString() + 'Z',
        });

        if (priceRaw > 0) {
          priceStocks.push({
            productId: skuId,
            countryCode: 'JP',
            localPrice: priceRaw,
            currency: 'JPY',
            cnyPrice: jpCny,
            stockStatus: sellable ? 'available' : 'out_of_stock',
            storeInfo: {
              city: '东京',
              storeName: '日本官网',
              address: '',
            },
            priceUpdateTime: new Date().toISOString() + 'Z',
          });
        }
      }
    } catch (e) {
      console.warn(`处理文件失败 ${filepath}: ${e.message}`);
    }
  }

  // productId 去重
  const pidSeen = {};
  const dedupedProducts = [];
  for (const p of products) {
    if (!pidSeen[p.productId]) {
      pidSeen[p.productId] = true;
      dedupedProducts.push(p);
    }
  }

  // priceStock 去重
  const psSeen = {};
  const dedupedPS = [];
  for (const ps of priceStocks) {
    const key = `${ps.productId}_${ps.countryCode}`;
    if (!psSeen[key]) {
      psSeen[key] = true;
      dedupedPS.push(ps);
    }
  }

  return { products: dedupedProducts, priceStocks: dedupedPS };
}

function generateImportPayload(products, priceStocks) {
  const CHUNK_SIZE = 30;
  const chunks = [];
  for (let i = 0; i < products.length; i += CHUNK_SIZE) {
    chunks.push(products.slice(i, i + CHUNK_SIZE));
  }

  const batches = chunks.map((chunk, idx) => {
    const pids = chunk.map(p => p.productId);
    const batchPS = priceStocks.filter(ps => pids.includes(ps.productId));
    return {
      action: 'import-part',
      part: idx,
      totalParts: chunks.length,
      products: chunk,
      priceStocks: batchPS
    };
  });

  return batches;
}

function main() {
  console.log('=== 比惠数据导入脚本 ===\n');

  // 1. 解析爬虫数据
  console.log('【步骤1】解析爬虫原始数据...');
  const { products, priceStocks } = processCaptures();
  console.log(`  过滤后商品数: ${products.length}`);
  console.log(`  价格库存数: ${priceStocks.length}`);

  if (products.length === 0) {
    console.log('\n❌ 没有可导入的商品数据，请先运行爬虫');
    process.exit(1);
  }

  // 2. 生成导入批次
  console.log('\n【步骤2】生成导入批次...');
  const batches = generateImportPayload(products, priceStocks);
  console.log(`  共 ${batches.length} 个批次`);

  // 3. 输出批次文件
  console.log('\n【步骤3】写入批次文件...');
  if (!fs.existsSync(BATCHES_DIR)) {
    fs.mkdirSync(BATCHES_DIR, { recursive: true });
  }

  batches.forEach(batch => {
    const filename = `batch_${String(batch.part + 1).padStart(3, '0')}.json`;
    const filepath = path.join(BATCHES_DIR, filename);
    fs.writeFileSync(filepath, JSON.stringify(batch, null, 2));
  });
  console.log(`  批次文件已写入: ${BATCHES_DIR}`);

  // 4. 生成云函数调用 payload
  console.log('\n【步骤4】生成云函数调用载荷...');
  const payload = {
    action: 'import-data',
    clear: true,
    products,
    priceStocks
  };
  const payloadPath = path.join(OUTPUT_DIR, 'cloud_payload.json');
  fs.writeFileSync(payloadPath, JSON.stringify(payload, null, 2));
  console.log(`  载荷文件: ${payloadPath}`);
  console.log(`  载荷大小: ${(JSON.stringify(payload).length / 1024).toFixed(1)} KB`);

  // 5. 打印导入指引
  console.log('\n=== 导入步骤 ===');
  console.log('在微信开发者工具中执行：');
  console.log('');
  console.log('1. 右键 importAllData 云函数 → 上传并部署：云端安装依赖');
  console.log('2. 打开云开发控制台 → 云函数 → importAllData → 测试');
  console.log(`3. 点击"打开"按钮，将 ${payloadPath} 的内容粘贴到测试参数框`);
  console.log('   或直接在测试参数中输入: { "action": "all" }（使用云函数内置数据）');
  console.log('');
  console.log('⚠️  注意：云函数单次请求有 6MB 大小限制，如数据量过大请使用分批模式');
  console.log('');
  console.log('=== 完成 ===');
}

main();
