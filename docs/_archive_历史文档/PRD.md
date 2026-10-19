# 全球奢侈品价格比价小程序

## PRD 文档 v1.1

---

## 1. 产品概述

### 1.1 产品简介

**产品名称：** luxury-price-miniapp（奢侈品价格比价小程序）

**产品类型：** 微信小程序

**一句话描述：** 实时搜索奢侈品品牌各SKU在属地国家的价格，支持多国汇率换算、返点优惠、寻买手等一站式服务。

**项目地址：** https://github.com/Xiao-HU1987/luxury-price-miniapp

### 1.2 目标用户

- 海外购物爱好者
- 奢侈品消费者
- 代购/买手从业者
- 追求高性价比购物的用户

### 1.3 核心价值

- **省心**：一键比较全球价格，锁定最低价
- **省钱**：实时汇率+返点优惠，计算真实到手价
- **省时**：快速找到靠谱买手，无需自行海淘

---

## 2. 产品结构

### 2.1 底部导航（TabBar）

| 序号 | Tab名称 | 页面路径 | 功能说明 |
|------|---------|----------|----------|
| 1 | 优惠 | pages/rebate/rebate | 返点优惠、优惠券信息 |
| 2 | 汇率 | pages/exchange/exchange | 多国货币实时汇率计算 |
| 3 | 比价 | pages/index/index | 商品搜索、比价列表 |
| 4 | 买手 | pages/buyer/buyer | 寻买手、发布需求 |
| 5 | 我的 | pages/profile/profile | 个人中心、设置 |

---

## 3. 功能模块详细说明

### 3.1 优惠页（返点优惠）

**功能概述：** 集中展示全球购物返点信息和优惠券

**页面结构：**

#### 3.1.1 日本优惠券区
- 展示日本主要商场的返点二维码和优惠信息
- 优惠券卡片包含：
  - 商场Logo/图标
  - 优惠券名称
  - 优惠说明（免税比例、返现额度等）
  - 状态标识（已使用/可领取）
- 支持一键领取功能

**数据字段：**
| 字段 | 类型 | 说明 |
|------|------|------|
| id | String | 优惠券唯一标识 |
| name | String | 优惠券名称 |
| description | String | 优惠说明 |
| logo | String | Logo图标 |
| status | String | 状态：used/unused |

#### 3.1.2 国内优惠券区
- 展示国内商场、品牌专柜的返现优惠券
- 格式同日本优惠券区

#### 3.1.3 商品比价区
- 展示热门商品的中日价格对比
- 点击跳转商品详情页

---

### 3.2 汇率页（实时汇率）

**功能概述：** 支持13种货币的实时汇率计算

**支持国家/货币（13个）：**
| 国家代码 | 国家名称 | 货币代码 | 货币名称 | 货币符号 | 国旗 |
|----------|----------|----------|----------|----------|------|
| CN | 中国 | CNY | 人民币 | ¥ | 🇨🇳 |
| US | 美国 | USD | 美元 | $ | 🇺🇸 |
| FR | 法国 | EUR | 欧元 | € | 🇫🇷 |
| IT | 意大利 | EUR | 欧元 | € | 🇮🇹 |
| UK | 英国 | GBP | 英镑 | £ | 🇬🇧 |
| JP | 日本 | JPY | 日元 | ¥ | 🇯🇵 |
| KR | 韩国 | KRW | 韩元 | ₩ | 🇰🇷 |
| HK | 中国香港 | HKD | 港币 | HK$ | 🇭🇰 |
| SG | 新加坡 | SGD | 新加坡元 | S$ | 🇸🇬 |
| AU | 澳大利亚 | AUD | 澳元 | A$ | 🇦🇺 |
| CH | 瑞士 | CHF | 瑞士法郎 | CHF | 🇨🇭 |
| CA | 加拿大 | CAD | 加元 | C$ | 🇨🇦 |
| TH | 泰国 | THB | 泰铢 | ฿ | 🇹🇭 |

**核心功能：**

#### 3.2.1 汇率计算器
- 输入金额
- 选择源货币
- 选择目标货币
- 实时显示换算结果
- 显示当前汇率值
- 支持货币互换
- 支持手动刷新汇率

#### 3.2.2 汇率列表
- 以当前选中的源货币为基准
- 显示所有货币的汇率
- 点击快速切换为源货币

**数据缓存：**
- 本地缓存1小时
- 过期自动更新

---

### 3.3 比价页（商品比价）

**功能概述：** 商品搜索和全球价格对比

**页面结构：**

#### 3.3.1 顶部导航栏
- 页面标题：到手比价
- 右侧操作按钮（占位）

#### 3.3.2 搜索栏
- 占位提示：请输入货号/商品中文名称
- 支持关键词搜索
- 跳转商品列表页

#### 3.3.3 筛选栏
| 筛选项 | 说明 |
|--------|------|
| 品牌筛选 | 下拉选择品牌 |
| 品类 | 下拉选择商品分类 |
| 价格 | 可切换升序/降序 |
| 汇率 | 显示当前日元汇率，点击跳转汇率页 |

#### 3.3.4 商品列表
- 商品卡片展示：
  - 商品图片
  - 商品名称
  - 货号（Article No.）
  - 中国价格（红色标识）
  - 日本到手价（橙色标识，已换算人民币）
  - "到手价"标签
  - 底部说明：日本最低到手价(实时更新)

**商品数据模型：**

```javascript
{
  id: String,           // SPU ID
  brandId: String,      // 品牌ID
  brandName: String,    // 品牌名称
  name: String,         // 商品名称
  articleNo: String,    // 货号
  category: String,     // 品类ID
  image: String,        // 图片URL
  description: String, // 描述
  skus: [
    {
      id: String,       // SKU ID
      spuId: String,    // SPU ID
      name: String,     // SKU名称
      color: String,    // 颜色
      size: String,     // 尺寸
      prices: {
        CN: { price: Number, currency: String, stock: Number, store: String },
        JP: { price: Number, currency: String, stock: Number, store: String },
        FR: { ... },
        US: { ... },
        // ...
      }
    }
  ]
}
```

**品牌数据（8个）：**
| 品牌ID | 品牌名称 | 英文名 | 简称 | 品类 |
|--------|----------|--------|------|------|
| b001 | 路易威登 | Louis Vuitton | LV | 箱包 |
| b002 | 古驰 | Gucci | G | 箱包服饰 |
| b003 | 爱马仕 | Hermès | H | 箱包 |
| b004 | 香奈儿 | Chanel | C | 箱包服饰 |
| b005 | 迪奥 | Dior | D | 服饰箱包 |
| b006 | 劳力士 | Rolex | R | 腕表 |
| b007 | 卡地亚 | Cartier | Ca | 珠宝腕表 |
| b008 | 普拉达 | Prada | P | 箱包 |

**品类数据（6个）：**
| 品类ID | 品类名称 | 图标 |
|--------|----------|------|
| c001 | 箱包 | 👜 |
| c002 | 腕表 | ⌚ |
| c003 | 珠宝 | 💎 |
| c004 | 服饰 | 👗 |
| c005 | 鞋履 | 👠 |
| c006 | 配饰 | 🕶️ |

---

### 3.4 商品详情页

**功能概述：** 展示单个商品的全球价格对比

**页面结构：**

#### 3.4.1 商品基本信息
- 商品图片
- 商品名称（中/英文）
- 货号
- 品牌

#### 3.4.2 SKU选择
- 颜色/规格选择
- 切换后更新价格信息

#### 3.4.3 全球价格对比
- 表格形式展示各国价格
- 包含字段：
  - 国家/地区
  - 原价
  - 汇率换算（人民币）
  - 库存状态
  - 门店信息

#### 3.4.4 价格计算
- 到手价计算（原价 + 汇率差 + 返点）
- 支持选择目标国家自动计算

---

### 3.5 买手页

**功能概述：** 连接买家与全球买手

**页面结构：**

#### 3.5.1 Tab切换
- 找买手：浏览买手列表
- 需求广场：查看/发布采购需求

#### 3.5.2 找买手视图

**搜索筛选：**
- 买手名称搜索
- 国家/地区筛选

**买手卡片：**
| 字段 | 说明 |
|------|------|
| 头像 | 买手头像 |
| 姓名 | 买手昵称 |
| 评分 | ⭐ 星级评分 |
| 地区 | 国籍 · 城市 |
| 已完成订单 | 历史成交单数 |
| 服务费 | 百分比 |
| 到货时间 | 天数 |
| 擅长品牌 | 标签展示 |

**数据字段：**
```javascript
{
  id: String,
  name: String,
  avatar: String,
  rating: Number,        // 4.0-5.0
  country: String,       // 国家代码
  city: String,
  orders: Number,        // 已完成订单数
  feeRate: Number,       // 服务费比例 %
  deliveryDays: Number,  // 到货天数
  specialty: [String],   // 擅长品牌ID列表
  intro: String          // 个人简介
}
```

#### 3.5.3 需求广场视图

**需求卡片：**
| 字段 | 说明 |
|------|------|
| 商品名称 | 采购商品 |
| 状态标签 | 招标中/已匹配/已完成 |
| 目标国家 | 采购目的地 |
| 预算 | 人民币金额 |
| 交期 | 截止日期 |
| 已投标 | 投标买手数量 |
| 发布时间 | 相对时间 |

**需求数据字段：**
```javascript
{
  id: String,
  userId: String,            // 发布用户ID
  productName: String,       // 商品名称
  brandId: String,           // 品牌ID
  country: String,           // 目标国家代码
  deadline: String,          // 截止日期 YYYY-MM-DD
  budget: Number,            // 预算金额
  budgetCurrency: String,    // 预算货币
  quantity: Number,          // 数量
  status: String,            // bidding/matched/completed
  bids: Number,              // 投标买手数量
  matchedBuyer: String,      // 已匹配买手ID
  createTime: String,        // 创建时间 ISO
  description: String        // 补充说明
}
```

#### 3.5.4 发布需求
- 商品名称（必填）
- 品牌选择
- 目标国家/地区
- 交期时间（日期选择）
- 预算（人民币）
- 数量
- 补充说明

---

### 3.6 我的页面

**功能概述：** 用户个人中心

**页面结构：**

#### 3.6.1 用户信息卡片
- 头像
- 昵称
- 用户ID（可点击复制）

#### 3.6.2 功能菜单
| 功能 | 图标 |
|------|------|
| 我的收藏 | ⭐ |
| 浏览历史 | 🕐 |
| 我的需求 | 📋 |
| 我的优惠券 | 🎫 |

#### 3.6.3 设置项
| 设置 | 图标 |
|------|------|
| 消息通知 | 🔔 |
| 默认货币 | 💰 |
| 关于我们 | ℹ️ |
| 意见反馈 | 💬 |

---

## 4. 数据结构

### 4.1 商场/门店数据

```javascript
{
  id: String,
  name: String,          // 商场名称
  type: String,          // mall/street/dutyfree 商场/专卖店街/免税店
  country: String,       // 国家代码
  city: String,          // 城市
  address: String,       // 地址
  brands: [String],      // 入驻品牌ID列表
  rating: Number,        // 评分
  image: String          // 图片
}
```

### 4.2 优惠券数据

```javascript
{
  id: String,
  title: String,         // 优惠券标题
  type: String,          // discount/percent/cashback 满减/折扣/返现
  discount: Number,      // 优惠额度（金额或百分比）
  threshold: Number,     // 满减门槛
  country: String,       // 国家代码
  storeId: String,       // 门店ID
  storeName: String,     // 门店名称
  expireDate: String,    // 过期日期 YYYY-MM-DD
  status: String         // available/used/expired
}
```

### 4.3 用户数据

```javascript
{
  userId: String,         // 用户ID（自动生成，U+时间戳）
  nickname: String,      // 昵称
  avatar: String,         // 头像
  createTime: String      // 创建时间 ISO
}
```

---

## 5. 技术实现

### 5.1 技术栈
- **框架**：微信小程序（基础库 2.32.3+）
- **样式**：WXSS
- **逻辑**：JavaScript (ES6+)
- **数据**：本地模拟数据（Mock）
- **存储**：wx.storage 本地缓存
- **图标生成**：Python 脚本（纯 PNG 生成，无需依赖）

### 5.2 文件结构
```
├── app.js                    # 小程序入口
├── app.json                  # 全局配置
├── app.wxss                  # 全局样式
├── project.config.json       # 项目配置
├── sitemap.json              # 站点地图
├── data/
│   └── mock.js               # 模拟数据（商品/门店/优惠券/买手/需求）
├── utils/
│   ├── constants.js          # 常量定义（国家/品牌/品类）
│   └── util.js              # 工具函数（价格格式化等）
├── images/
│   └── tab/                  # TabBar图标（选中/未选中各5个）
├── scripts/
│   └── generate_icons.py    # TabBar图标生成脚本
└── pages/
    ├── rebate/               # 返点优惠（TabBar启动页）
    ├── index/                # 商品比价（TabBar）
    ├── exchange/             # 汇率计算（TabBar）
    ├── buyer/                # 寻买手（TabBar）
    ├── profile/              # 个人中心（TabBar）
    ├── products/             # 商品列表
    ├── product-detail/       # 商品详情
    ├── stores/               # 商场门店
    └── coupons/              # 优惠券
```

### 5.3 核心算法

#### 汇率换算
```javascript
// 将源货币转换为目标货币（基准货币为 CNY）
function convertCurrency(amount, fromCurrency, toCurrency, rates) {
  const fromRate = rates.rates[fromCurrency];
  const toRate = rates.rates[toCurrency];
  // 转换为基础货币后，再换算为目标货币
  const baseAmount = amount / fromRate;
  return baseAmount * toRate;
}
```

#### 到手价计算
```
到手价 = 原价 × 汇率 + 服务费 + 运费 - 返点
```

#### 价格格式化
```javascript
// 千分位格式化（不使用 toLocaleString，避免 WXML 模板限制）
function formatPrice(num) {
  return String(num).replace(/\B(?=(\d{3})+(?!\d))/g, ',');
}
```

### 5.4 性能优化

#### 数据缓存
- **汇率数据**：本地缓存 1 小时，过期自动刷新
- **商品列表**：`_productsCache` 内存缓存，避免重复计算
- **用户信息**：wx.storage 持久化存储

#### WXML 模板约束
- WXML 不支持方法调用（如 `.toFixed()`、`.toLocaleString()`）
- 所有格式化数据需在 JS 中预处理后再绑定到模板
- 避免在 WXML 中使用复杂表达式

### 5.5 适配方案

#### iPhone 刘海屏适配
- 使用 `wx.getWindowInfo()` 获取状态栏高度（替代已弃用的 `wx.getSystemInfoSync()`）
- 页面顶部添加安全区域占位元素
- 导航栏使用三栏对称布局（左/中/右）确保标题居中

#### TabBar 规范
- 图标尺寸：81×81px PNG
- 未选中颜色：#999999（浅灰色）
- 选中颜色：#ff6b00（橙色）
- 每个 Tab 独立图标，样式与文字含义对应

---

## 6. 页面路由

| 页面 | 路由 | 参数 | 说明 |
|------|------|------|------|
| 优惠页 | /pages/rebate/rebate | - | TabBar（启动页） |
| 比价首页 | /pages/index/index | - | TabBar |
| 汇率页 | /pages/exchange/exchange | - | TabBar |
| 买手页 | /pages/buyer/buyer | - | TabBar |
| 我的页 | /pages/profile/profile | - | TabBar |
| 商品列表 | /pages/products/products | keyword, brandId, category | 搜索结果 |
| 商品详情 | /pages/product-detail/product-detail | id | 商品ID |
| 商场门店 | /pages/stores/stores | - | 页面 |
| 优惠券 | /pages/coupons/coupons | - | 页面 |

---

## 7. 视觉规范

### 7.1 主题色
| 用途 | 色值 |
|------|------|
| 主色调 | #ff6b00 (橙色) |
| 辅助色 | #ff8c00 (深橙) |
| 强调色-价格 | #e74c3c (红色) |
| 强调色-优惠 | #ff8c00 (橙色) |
| 背景色 | #f5f5f5 (浅灰) |
| 卡片背景 | #ffffff (白色) |
| 文字主色 | #333333 |
| 文字副色 | #666666 |
| 文字弱色 | #999999 |

### 7.2 字体规范
| 用途 | 字号 |
|------|------|
| 页面标题 | 32rpx |
| 模块标题 | 30rpx |
| 正文 | 28rpx |
| 辅助文字 | 24rpx |
| 标签文字 | 22rpx |

### 7.3 间距规范
| 用途 | 间距 |
|------|------|
| 页面边距 | 24rpx |
| 卡片内边距 | 24rpx |
| 模块间距 | 20rpx |
| 元素间距 | 12rpx |

---

## 8. 版本规划

### v1.1 当前版本
- [x] 底部TabBar导航（5个页面，独立图标）
- [x] 返点优惠页（启动页）
- [x] 实时汇率计算（13种货币，13个国家）
- [x] 商品比价首页（8个品牌，6个品类）
- [x] 商品搜索功能
- [x] 商品详情页（全球价格对比）
- [x] 寻买手功能（买手列表 + 需求广场）
- [x] 个人中心页
- [x] 商场/门店列表页
- [x] 优惠券列表页
- [x] iPhone 刘海屏安全区域适配
- [x] 导航栏标题居中布局
- [x] 本地数据缓存机制

### v2.0 规划功能
- [ ] 真实汇率API接入
- [ ] 用户登录注册（微信授权）
- [ ] 后端数据同步
- [ ] 商品图片展示
- [ ] 在线支付功能
- [ ] 订单管理系统
- [ ] 消息推送功能
- [ ] 社交分享功能
- [ ] 收藏/浏览历史功能
- [ ] 买手投标/竞价功能

---

## 9. 附录

### 9.1 专业术语

| 术语 | 说明 |
|------|------|
| SPU | 标准化产品单元，商品聚合的最小单位 |
| SKU | 库存量单位，具体的商品规格 |
| 货号 | 品牌内部商品编号 |
| 到手价 | 包含所有费用后的最终价格 |
| 返点 | 购物后返还的比例金额 |
| 买手 | 专业的海外代购人员 |

### 9.2 数据来源说明

当前版本使用本地模拟数据，后续需对接：
- 汇率数据：银行/第三方汇率API
- 商品数据：品牌官网API或第三方数据平台
- 门店数据：商场官方信息
- 优惠券数据：商场/品牌提供

---

**文档信息**
- 版本：v1.1
- 更新日期：2026-06-29
- 项目地址：https://github.com/Xiao-HU1987/luxury-price-miniapp
- 编写人：AI Assistant
- 审核状态：待审核
