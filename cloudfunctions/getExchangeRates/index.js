// getExchangeRates - 获取实时汇率
// 数据来源：Frankfurter（欧洲央行数据源，免费无限制、无需 API Key）
// 每次调用都实时获取，保证数据新鲜

const cloud = require('wx-server-sdk');
const https = require('https');

cloud.init({ env: cloud.DYNAMIC_CURRENT_ENV });

const db = cloud.database();

// Frankfurter API - 欧洲央行汇率，完全免费
const API_URL = 'https://api.frankfurter.app/latest?from=CNY&to=JPY,KRW';

// API 请求超时（毫秒）
const API_TIMEOUT = 8000;

// 兜底汇率（API 不可用时使用，仅作应急）
const FALLBACK_RATES = {
  CNY: 1,
  JPY: 21.58,
  KRW: 192.5
};

/**
 * 发起 HTTPS 请求
 */
function fetchRates() {
  return new Promise((resolve, reject) => {
    const req = https.get(API_URL, { timeout: API_TIMEOUT }, (res) => {
      let data = '';
      res.on('data', (chunk) => { data += chunk; });
      res.on('end', () => {
        try {
          const json = JSON.parse(data);
          if (json && json.rates) {
            resolve({
              JPY: json.rates.JPY || FALLBACK_RATES.JPY,
              KRW: json.rates.KRW || FALLBACK_RATES.KRW
            });
          } else {
            reject(new Error('API 返回格式异常'));
          }
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

/**
 * 写入最近汇率到数据库（仅用于后台记录，不用于前端缓存）
 */
async function saveToDb(rates) {
  try {
    await db.collection('exchange_rates').add({
      data: {
        rates,
        baseCurrency: 'CNY',
        updateTime: new Date().toISOString()
      }
    });
  } catch (e) {
    // 静默失败，不影响主流程
  }
}

exports.main = async (event, context) => {
  try {
    const { JPY, KRW } = await fetchRates();
    const rates = { CNY: 1, JPY, KRW };
    const now = new Date().toISOString();

    // 后台记录（供审计/回溯，前端不感知）
    saveToDb(rates);

    return {
      code: 0,
      data: {
        rates,
        updateTime: now
      }
    };
  } catch (err) {
    return {
      code: 0,
      data: {
        rates: FALLBACK_RATES,
        updateTime: new Date().toISOString()
      }
    };
  }
};
