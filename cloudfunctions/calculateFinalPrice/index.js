// calculateFinalPrice - 到手价计算器
// 调用方式：wx.cloud.callFunction({ name: 'calculateFinalPrice', data: { ... } })
// 参数：{
//   price: 商品原价（当地货币）,
//   currency: 货币代码 (JPY/EUR/GBP等),
//   channel: 购买渠道 (alipay/wechat/card/cash),
//   refundRate: 退税率 (0-1),
//   rebateRate: 返点率 (0-1),
//   storePrice: 中国官网价（可选，用于对比）
// }
// 返回：{ code, data: { breakdown, finalCny, savings } }

const cloud = require('wx-server-sdk');
cloud.init({ env: cloud.DYNAMIC_CURRENT_ENV });

const db = cloud.database();

// 各渠道手续费率
const CHANNEL_FEES = {
  alipay: 0.0038,
  wechat: 0.0038,
  card: 0.015,
  cash: 0
};

exports.main = async (event, context) => {
  const {
    price = 0,
    currency = 'JPY',
    channel = 'alipay',
    refundRate = 0,
    rebateRate = 0,
    storePrice = 0
  } = event;

  if (!price || price <= 0) {
    return { code: -1, message: '请输入有效价格' };
  }

  try {
    // 获取汇率
    const ratesRes = await db.collection('exchange_rates')
      .where({ baseRate: { $exists: true } })
      .orderBy({ updateTime: 'desc' })
      .limit(1)
      .get();

    let baseRate = 0;
    let channelFee = CHANNEL_FEES[channel] || 0;

    if (ratesRes.data && ratesRes.data.length > 0) {
      const rateDoc = ratesRes.data[0];
      baseRate = rateDoc.rates[currency] || 0;

      // 获取渠道阶梯优惠
      if (channel && rateDoc.channels && rateDoc.channels[channel]) {
        const channelData = rateDoc.channels[channel];
        if (channelData.feeRate !== undefined) {
          channelFee = channelData.feeRate;
        }
      }
    }

    if (!baseRate || baseRate <= 0) {
      return { code: -1, message: '汇率数据不可用' };
    }

    const rawPrice = price;
    const refundAmount = rawPrice * (refundRate / 100);
    const rebateAmount = rawPrice * (rebateRate / 100);
    const afterDiscount = rawPrice - refundAmount - rebateAmount;
    const feeAmount = afterDiscount * channelFee;
    const finalLocal = afterDiscount + feeAmount;
    const finalCny = Math.round(finalLocal / baseRate);

    const breakdown = {
      rawPrice: Math.round(rawPrice),
      rawPriceStr: Math.round(rawPrice).toLocaleString(),
      currency,
      refundAmount: Math.round(refundAmount),
      refundAmountStr: Math.round(refundAmount).toLocaleString(),
      refundRate,
      rebateAmount: Math.round(rebateAmount),
      rebateAmountStr: Math.round(rebateAmount).toLocaleString(),
      rebateRate,
      channelFee: (channelFee * 100).toFixed(2),
      feeAmount: Math.round(feeAmount),
      feeAmountStr: Math.round(feeAmount).toLocaleString(),
      afterDiscount: Math.round(afterDiscount),
      afterDiscountStr: Math.round(afterDiscount).toLocaleString(),
      baseRate,
      channel
    };

    let savings = null;
    if (storePrice && storePrice > 0) {
      const save = storePrice - finalCny;
      savings = {
        storePrice,
        storePriceStr: storePrice.toLocaleString(),
        saveAmount: Math.max(0, save),
        saveAmountStr: Math.max(0, save).toLocaleString(),
        savePercent: storePrice > 0 ? Math.max(0, Math.round(save / storePrice * 100)) : 0
      };
    }

    return {
      code: 0,
      data: {
        breakdown,
        finalCny,
        finalCnyStr: finalCny.toLocaleString(),
        savings
      }
    };
  } catch (err) {
    console.error('calculateFinalPrice error:', err);
    return { code: -1, message: '计算失败' };
  }
};
