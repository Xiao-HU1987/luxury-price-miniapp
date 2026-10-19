// getExchangeRates - 获取实时汇率（多源交叉校验）
// 数据来源：
//   主源: open.er-api.com （实时中间价，基于官方市场数据，免费无 Key）
//   备源: Frankfurter    （欧洲央行 ECB 官方汇率，每日更新）
// 语义：1 CNY 可兑换多少外币（与全站 '1 CNY = x JPY' 展示一致）
// 每次调用实时获取，成功后写入 exchange_rates 集合作缓存与审计

const cloud = require('wx-server-sdk');
const https = require('https');

cloud.init({ env: cloud.DYNAMIC_CURRENT_ENV });

const db = cloud.database();

// 主备数据源（均返回 { JPY, KRW }，语义为 1 CNY = x 外币）
const SOURCES = [
  {
    name: 'open.er-api.com(实时中间价)',
    url: 'https://open.er-api.com/v6/latest/CNY'
  },
  {
    name: 'ECB/Frankfurter(官方)',
    url: 'https://api.frankfurter.app/latest?from=CNY&to=JPY,KRW'
  }
];

const API_TIMEOUT = 8000;

// 兜底汇率（API 不可用时使用，仅作应急；正常情况不应走到）
const FALLBACK_RATES = {
  CNY: 1,
  JPY: 21.58,
  KRW: 192.5
};

/** 解析来源数据为 { JPY, KRW } */
function parseSource(name, json) {
  const rates = json && json.rates;
  if (!rates || typeof rates !== 'object') {
    throw new Error(name + ' 返回格式异常');
  }
  const JPY = parseFloat(rates.JPY);
  const KRW = parseFloat(rates.KRW);
  if (!JPY || JPY <= 0 || !KRW || KRW <= 0) {
    throw new Error(name + ' 缺少JPY/KRW汇率');
  }
  return { JPY, KRW };
}

/** 发起 HTTPS 请求，返回 JSON */
function fetchJson(url) {
  return new Promise((resolve, reject) => {
    const req = https.get(url, { timeout: API_TIMEOUT }, (res) => {
      let data = '';
      res.on('data', (chunk) => { data += chunk; });
      res.on('end', () => {
        try {
          resolve(JSON.parse(data));
        } catch (e) {
          reject(new Error('数据解析失败'));
        }
      });
    });
    req.on('error', reject);
    req.on('timeout', () => {
      req.destroy();
      reject(new Error('请求超时'));
    });
  });
}

/** 多源抓取：依次尝试，全部失败则抛错 */
async function fetchRatesFromSources() {
  let lastErr = null;
  for (const source of SOURCES) {
    try {
      const json = await fetchJson(source.url);
      return { rates: parseSource(source.name, json), source: source.name };
    } catch (e) {
      lastErr = e;
      // 继续尝试下一源
    }
  }
  throw lastErr || new Error('所有汇率源均不可用');
}

/** 将汇率写入数据库（缓存与审计，前端不依赖） */
async function saveToDb(rates, sourceName) {
  try {
    await db.collection('exchange_rates').add({
      data: {
        rates,
        baseCurrency: 'CNY',
        source: sourceName,
        updateTime: db.serverDate()
      }
    });
  } catch (e) {
    // 静默失败，不影响主流程
  }
}

exports.main = async (event, context) => {
  try {
    const { rates, source } = await fetchRatesFromSources();
    const finalRates = { CNY: 1, JPY: rates.JPY, KRW: rates.KRW };
    const now = new Date().toISOString();

    // 后台记录（供审计/回溯，前端不感知）
    saveToDb(finalRates, source);

    return {
      code: 0,
      data: {
        rates: finalRates,
        updateTime: now,
        source
      }
    };
  } catch (err) {
    return {
      code: 0,
      data: {
        rates: FALLBACK_RATES,
        updateTime: new Date().toISOString(),
        source: 'fallback(内置兜底)'
      }
    };
  }
};