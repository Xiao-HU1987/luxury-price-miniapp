// scripts/import_to_cloud.js
// 一键导入数据到云数据库（无需手动操作云开发控制台）
// 用法：node scripts/import_to_cloud.js
//
// 前提条件：
//   1. 已运行 npm install 安装依赖
//   2. 已在 scripts/cloud_config.json 中配置腾讯云密钥

const fs = require('fs');
const path = require('path');

const BASE_DIR = path.join(__dirname, '..');
const CONFIG_PATH = path.join(__dirname, 'cloud_config.json');

// 云开发环境 ID
const ENV_ID = 'cloud1-d9gvjg9fy04acef08';

// 加载配置
function loadConfig() {
  if (!fs.existsSync(CONFIG_PATH)) {
    console.log('\n❌ 未找到配置文件 scripts/cloud_config.json');
    console.log('\n请按以下步骤获取腾讯云 API 密钥：');
    console.log('  1. 打开 https://console.cloud.tencent.com/cam/capi');
    console.log('  2. 登录腾讯云账号（与微信开发者工具同一个账号）');
    console.log('  3. 点击「新建密钥」');
    console.log('  4. 复制 SecretId 和 SecretKey');
    console.log('  5. 创建文件 scripts/cloud_config.json，内容如下：');
    console.log('\n  {');
    console.log('    "secretId": "你的SecretId",');
    console.log('    "secretKey": "你的SecretKey"');
    console.log('  }\n');
    process.exit(1);
  }
  const config = JSON.parse(fs.readFileSync(CONFIG_PATH, 'utf-8'));
  if (!config.secretId || !config.secretKey) {
    console.log('❌ 配置文件中 secretId 或 secretKey 为空');
    process.exit(1);
  }
  return config;
}

// 非包包类商品关键词
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

function isHandbag(item) {
  const slug = (item.slug || '').toLowerCase();
  const url = (item.url || '').toLowerCase();
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

// 从爬虫捕获文件解析数据
function parseCrawlerData() {
  const capturesDir = path.join(BASE_DIR, 'server', 'crawler', 'raw_captures');
  if (!fs.existsSync(capturesDir)) {
    console.log('❌ 未找到爬虫数据目录: server/crawler/raw_captures');
    process.exit(1);
  }

  const files = fs.readdirSync(capturesDir)
    .filter(f => f.includes('skus_') && f.endsWith('.json'));

  console.log(`找到 ${files.length} 个爬虫捕获文件`);

  const products = [];
  const priceStocks = [];
  const slugSeen = {};

  for (const file of files) {
    const filepath = path.join(capturesDir, file);
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
        if (!isHandbag({ slug, url })) continue;
        if (slugSeen[slug]) continue;
        slugSeen[slug] = skuId;

        let mainImage = '';
        let allImages = [];
        if (Array.isArray(medias)) {
          for (const m of medias) {
            if (m.url) {
              const imgUrl = m.url.startsWith('//') ? 'https:' + m.url : m.url;
              allImages.push(imgUrl);
            }
          }
          if (allImages.length) mainImage = allImages[0];
        }

        const jpCny = Math.round(priceRaw * 0.0462);

        products.push({
          productId: skuId,
          slug,
          nameCn: nameJp,
          nameEn: '',
          mainImage,
          images: allImages.slice(0, 5),
          cnOfficialPrice: 0,
          category: 'handbag',
          brandId: 'b001',
          brandName: 'Louis Vuitton',
          dimensions: (item.dimensionsData && item.dimensionsData[0]) || {},
          createTime: new Date().toISOString(),
        });

        if (priceRaw > 0) {
          priceStocks.push({
            productId: skuId,
            countryCode: 'JP',
            localPrice: priceRaw,
            currency: 'JPY',
            cnyPrice: jpCny,
            stockStatus: sellable ? 'available' : 'out_of_stock',
            storeInfo: { city: '东京', storeName: '日本官网', address: '' },
            priceUpdateTime: new Date().toISOString(),
          });
        }
      }
    } catch (e) {
      console.warn(`  跳过文件 ${file}: ${e.message}`);
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

async function main() {
  console.log('=== 比惠数据一键导入 ===\n');

  // 1. 加载配置
  const config = loadConfig();

  // 2. 解析爬虫数据
  console.log('【1/4】解析爬虫数据...');
  const { products, priceStocks } = parseCrawlerData();
  console.log(`  包包商品: ${products.length} 个`);
  console.log(`  价格库存: ${priceStocks.length} 条`);

  if (products.length === 0) {
    console.log('\n❌ 没有可导入的商品，请先运行爬虫');
    process.exit(1);
  }

  // 3. 初始化云开发 SDK
  console.log('\n【2/4】连接云开发环境...');
  const CloudBase = require('@cloudbase/manager-node');
  const tcb = new CloudBase({
    secretId: config.secretId,
    secretKey: config.secretKey,
    envId: ENV_ID
  });

  const db = tcb.database();
  console.log('  连接成功');

  // 4. 清空旧数据
  console.log('\n【3/4】清空旧数据...');
  try {
    await db.collection('products').where({ _id: db.command.neq('') }).delete();
    console.log('  products 集合已清空');
  } catch (e) {
    console.log(`  products 清空失败: ${e.message}`);
  }
  try {
    await db.collection('price_stock').where({ _id: db.command.neq('') }).delete();
    console.log('  price_stock 集合已清空');
  } catch (e) {
    console.log(`  price_stock 清空失败: ${e.message}`);
  }

  // 5. 分批写入数据
  console.log('\n【4/4】写入新数据...');

  // 商品数据（每批 20 条）
  const PRODUCT_BATCH = 20;
  let productCount = 0;
  for (let i = 0; i < products.length; i += PRODUCT_BATCH) {
    const batch = products.slice(i, i + PRODUCT_BATCH);
    try {
      await db.collection('products').add(batch);
      productCount += batch.length;
      process.stdout.write(`\r  商品: ${productCount}/${products.length}`);
    } catch (e) {
      console.log(`\n  批次 ${i} 写入失败: ${e.message}`);
    }
  }
  console.log('');

  // 价格库存数据（每批 30 条）
  const PS_BATCH = 30;
  let psCount = 0;
  for (let i = 0; i < priceStocks.length; i += PS_BATCH) {
    const batch = priceStocks.slice(i, i + PS_BATCH);
    try {
      await db.collection('price_stock').add(batch);
      psCount += batch.length;
      process.stdout.write(`\r  库存: ${psCount}/${priceStocks.length}`);
    } catch (e) {
      console.log(`\n  批次 ${i} 写入失败: ${e.message}`);
    }
  }
  console.log('');

  console.log('\n✅ 导入完成！');
  console.log(`   商品: ${productCount} 个`);
  console.log(`   价格库存: ${psCount} 条`);
  console.log('\n现在可以在小程序中清除缓存重新编译查看效果');
}

main().catch(err => {
  console.error('\n❌ 导入失败:', err.message);
  process.exit(1);
});
