// userAction - 用户操作（收藏、浏览历史、价格提醒、商品对比、设置等）
// actions:
//   - 'getProfile': 获取用户数据
//   - 'toggleFavorite': 收藏/取消收藏 { productId }
//   - 'getFavorites': 获取收藏列表（含商品信息）
//   - 'addHistory': 添加浏览历史 { productId }
//   - 'getHistory': 获取浏览历史
//   - 'addCalcHistory': 添加计算历史 { price, currency, ... }
//   - 'updateSettings': 更新用户设置 { settings }
//   - 'addPriceAlert': 添加价格提醒 { productId, targetPrice }
//   - 'removePriceAlert': 删除价格提醒 { productId }
//   - 'getPriceAlerts': 获取价格提醒列表（含商品信息）
//   - 'addToCompare': 添加对比 { productId }（最多3个）
//   - 'removeFromCompare': 从对比移除 { productId }
//   - 'clearCompare': 清空对比
//   - 'getCompareList': 获取对比列表（含商品信息）

const cloud = require('wx-server-sdk');
cloud.init({ env: cloud.DYNAMIC_CURRENT_ENV });

const db = cloud.database();
const _ = db.command;

const COLLECTION = 'user_favorites';

exports.main = async (event, context) => {
  const { OPENID } = cloud.getWXContext();
  const { action, ...data } = event;

  if (!action) {
    return { code: -1, message: '缺少操作类型' };
  }

  try {
    // 获取用户文档
    const userRes = await db.collection(COLLECTION)
      .where({ _openid: OPENID })
      .limit(1)
      .get();

    let userDoc = null;
    if (userRes.data && userRes.data.length > 0) {
      userDoc = userRes.data[0];
    }

    switch (action) {
      case 'getProfile':
        return { code: 0, data: userDoc || { favorites: [], viewHistory: [], calcHistory: [], priceAlerts: [], compareList: [], settings: {} };

      case 'toggleFavorite': {
        const { productId } = data;
        if (!productId) return { code: -1, message: '缺少商品ID' };

        if (!userDoc) {
          await db.collection(COLLECTION).add({
            data: {
              favorites: [productId],
              viewHistory: [],
              calcHistory: [],
              settings: {},
              createTime: db.serverDate(),
              updateTime: db.serverDate()
            }
          });
          return { code: 0, favorited: true };
        }

        const favs = userDoc.favorites || [];
        const idx = favs.indexOf(productId);
        if (idx >= 0) {
          favs.splice(idx, 1);
        } else {
          favs.push(productId);
        }

        await db.collection(COLLECTION).doc(userDoc._id).update({
          data: { favorites: favs, updateTime: db.serverDate() }
        });

        return { code: 0, favorited: idx < 0 };
      }

      case 'getFavorites':
        return { code: 0, data: (userDoc && userDoc.favorites) || [] };

      case 'addHistory': {
        const { productId } = data;
        if (!productId) return { code: -1, message: '缺少商品ID' };

        const history = (userDoc && userDoc.viewHistory) || [];
        const filtered = history.filter(id => id !== productId);
        filtered.unshift(productId);
        const trimmed = filtered.slice(0, 50);

        if (!userDoc) {
          await db.collection(COLLECTION).add({
            data: {
              favorites: [],
              viewHistory: trimmed,
              calcHistory: [],
              settings: {},
              createTime: db.serverDate(),
              updateTime: db.serverDate()
            }
          });
        } else {
          await db.collection(COLLECTION).doc(userDoc._id).update({
            data: { viewHistory: trimmed, updateTime: db.serverDate() }
          });
        }

        return { code: 0 };
      }

      case 'getHistory':
        return { code: 0, data: (userDoc && userDoc.viewHistory) || [] };

      case 'addCalcHistory': {
        if (!userDoc) {
          await db.collection(COLLECTION).add({
            data: {
              favorites: [],
              viewHistory: [],
              calcHistory: [data],
              settings: {},
              createTime: db.serverDate(),
              updateTime: db.serverDate()
            }
          });
        } else {
          const calcHistory = userDoc.calcHistory || [];
          calcHistory.unshift({ ...data, createTime: db.serverDate() });
          const trimmed = calcHistory.slice(0, 30);
          await db.collection(COLLECTION).doc(userDoc._id).update({
            data: { calcHistory: trimmed, updateTime: db.serverDate() }
          });
        }
        return { code: 0 };
      }

      case 'updateSettings': {
        const { settings } = data;
        if (!settings) return { code: -1, message: '缺少设置数据' };

        if (!userDoc) {
          await db.collection(COLLECTION).add({
            data: {
              favorites: [],
              viewHistory: [],
              calcHistory: [],
              priceAlerts: [],
              compareList: [],
              settings,
              createTime: db.serverDate(),
              updateTime: db.serverDate()
            }
          });
        } else {
          await db.collection(COLLECTION).doc(userDoc._id).update({
            data: { settings, updateTime: db.serverDate() }
          });
        }
        return { code: 0 };
      }

      // ===== 价格提醒 =====
      case 'addPriceAlert': {
        const { productId, targetPrice } = data;
        if (!productId) return { code: -1, message: '缺少商品ID' };
        if (!targetPrice) return { code: -1, message: '缺少目标价格' };

        const priceAlerts = (userDoc && userDoc.priceAlerts) || [];
        // 已存在则更新目标价
        const idx = priceAlerts.findIndex(a => a.productId === productId);
        if (idx >= 0) {
          priceAlerts[idx].targetPrice = Number(targetPrice);
          priceAlerts[idx].updateTime = db.serverDate();
        } else {
          priceAlerts.push({
            productId,
            targetPrice: Number(targetPrice),
            createTime: db.serverDate(),
            updateTime: db.serverDate()
          });
        }

        if (!userDoc) {
          await db.collection(COLLECTION).add({
            data: {
              favorites: [],
              viewHistory: [],
              calcHistory: [],
              priceAlerts,
              compareList: [],
              settings: {},
              createTime: db.serverDate(),
              updateTime: db.serverDate()
            }
          });
        } else {
          await db.collection(COLLECTION).doc(userDoc._id).update({
            data: { priceAlerts, updateTime: db.serverDate() }
          });
        }
        return { code: 0, data: priceAlerts.length };
      }

      case 'removePriceAlert': {
        const { productId } = data;
        if (!userDoc) return { code: 0 };
        const priceAlerts = ((userDoc.priceAlerts) || []).filter(a => a.productId !== productId);
        await db.collection(COLLECTION).doc(userDoc._id).update({
          data: { priceAlerts, updateTime: db.serverDate() }
        });
        return { code: 0, data: priceAlerts.length };
      }

      case 'getPriceAlerts': {
        const alerts = (userDoc && userDoc.priceAlerts) || [];
        // 联查商品信息
        const pids = alerts.map(a => a.productId).filter(Boolean);
        let productsMap = {};
        if (pids.length > 0) {
          try {
            const prods = await db.collection('products')
              .where({ productId: _.in(pids) })
              .limit(100)
              .get();
            prods.data.forEach(p => { productsMap[p.productId] = p; });
          } catch (e) { console.warn('products联查失败', e); }
        }
        const list = alerts.map(a => ({
          ...a,
          product: productsMap[a.productId] || null
        })).filter(a => a.product);
        return { code: 0, data: list, count: list.length };
      }

      // ===== 商品对比 =====
      case 'addToCompare': {
        const { productId } = data;
        if (!productId) return { code: -1, message: '缺少商品ID' };
        let compareList = (userDoc && userDoc.compareList) || [];
        if (!compareList.includes(productId)) {
          if (compareList.length >= 3) {
            return { code: -2, message: '最多只能对比3个商品，请先移除一个', data: compareList };
          }
          compareList.push(productId);
        }
        if (!userDoc) {
          await db.collection(COLLECTION).add({
            data: {
              favorites: [],
              viewHistory: [],
              calcHistory: [],
              priceAlerts: [],
              compareList,
              settings: {},
              createTime: db.serverDate(),
              updateTime: db.serverDate()
            }
          });
        } else {
          await db.collection(COLLECTION).doc(userDoc._id).update({
            data: { compareList, updateTime: db.serverDate() }
          });
        }
        return { code: 0, data: compareList, count: compareList.length };
      }

      case 'removeFromCompare': {
        const { productId } = data;
        if (!userDoc) return { code: 0, data: [], count: 0 };
        const compareList = (userDoc.compareList || []).filter(id => id !== productId);
        await db.collection(COLLECTION).doc(userDoc._id).update({
          data: { compareList, updateTime: db.serverDate() }
        });
        return { code: 0, data: compareList, count: compareList.length };
      }

      case 'clearCompare': {
        if (!userDoc) return { code: 0, data: [], count: 0 };
        await db.collection(COLLECTION).doc(userDoc._id).update({
          data: { compareList: [], updateTime: db.serverDate() }
        });
        return { code: 0, data: [], count: 0 };
      }

      case 'getCompareList': {
        const ids = (userDoc && userDoc.compareList) || [];
        let list = [];
        if (ids.length > 0) {
          try {
            const prods = await db.collection('products')
              .where({ productId: _.in(ids) })
              .limit(100)
              .get();
            // 保持原始顺序
            list = ids.map(id => prods.data.find(p => p.productId === id) || null).filter(Boolean);
          } catch (e) { console.warn('compare联查失败', e); }
        }
        return { code: 0, data: list, count: list.length };
      }

      case 'getFavorites': {
        const ids = (userDoc && userDoc.favorites) || [];
        let list = [];
        if (ids.length > 0) {
          try {
            const prods = await db.collection('products')
              .where({ productId: _.in(ids) })
              .limit(1000)
              .get();
            list = ids.map(id => prods.data.find(p => p.productId === id) || null).filter(Boolean);
          } catch (e) { console.warn('favorites联查失败', e); }
        }
        return { code: 0, data: list, count: list.length };
      }

      case 'getHistory': {
        const ids = (userDoc && userDoc.viewHistory) || [];
        let list = [];
        if (ids.length > 0) {
          try {
            const prods = await db.collection('products')
              .where({ productId: _.in(ids) })
              .limit(100)
              .get();
            list = ids.map(id => prods.data.find(p => p.productId === id) || null).filter(Boolean);
          } catch (e) { console.warn('history联查失败', e); }
        }
        return { code: 0, data: list, count: list.length };
      }

      default:
        return { code: -1, message: '未知操作: ' + action };
    }
  } catch (err) {
    console.error('userAction error:', err);
    return { code: -1, message: '操作失败' };
  }
};
