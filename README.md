<div align="center">

# 奢侈品比价小程序

> 全球奢侈品价格比价微信小程序 — 帮你找到最优惠的购买渠道

[![WeChat](https://img.shields.io/badge/WeChat-MiniProgram-07C160?logo=wechat&logoColor=white)](https://developers.weixin.qq.com/miniprogram/dev/framework/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100%2B-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Vue](https://img.shields.io/badge/Vue-3.x-4FC08D?logo=vue.js&logoColor=white)](https://vuejs.org/)
[![Python](https://img.shields.io/badge/Python-3.8%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](#许可证)

</div>

## 目录

- [项目简介](#项目简介)
- [功能特性](#功能特性)
- [技术栈](#技术栈)
- [项目结构](#项目结构)
- [快速开始](#快速开始)
  - [环境要求](#环境要求)
  - [后端启动](#后端启动)
  - [小程序启动](#小程序启动)
  - [后台管理启动](#后台管理启动)
- [部署指南](#部署指南)
- [功能模块详解](#功能模块详解)
- [开发规范](#开发规范)
- [常见问题](#常见问题)
- [许可证](#许可证)

---

## 项目简介

全球奢侈品价格比价微信小程序，帮助用户快速查询全球各地奢侈品价格，支持多品牌、多品类、多国家/地区的价格对比，找到最优惠的购买渠道。

### 核心亮点

- 🌍 **全球比价**：覆盖中日欧美等主要奢侈品市场
- 💱 **实时汇率**：自动换算人民币价格，直观对比
- 🎯 **精准搜索**：按品牌、品类、关键词多维筛选
- 👜 **买手对接**：发布需求，专业买手为你找货
- 🎫 **优惠返点**：商场返点、信用卡返点一键掌握
- 👑 **VIP会员**：专属优惠，优先服务

---

## 功能特性

### 小程序端（用户端）

| 模块 | 功能 | 状态 |
|------|------|------|
| 开屏广告 | 启动广告展示、倒计时跳过、每日次数限制 | ✅ |
| 商品比价 | 关键词搜索、品牌筛选、分类筛选、价格排序 | ✅ |
| 商品详情 | 多SKU规格、全球价格对比表、最低价标识 | ✅ |
| 汇率换算 | 20+ 种货币、实时汇率、快捷换算 | ✅ |
| 优惠返点 | 返点活动列表、VIP专享、按国家筛选 | ✅ |
| 优惠券 | 优惠券领取、我的优惠券、使用说明 | ✅ |
| 买手列表 | 全球买手展示、按国家筛选、买手详情 | ✅ |
| 寻买手需求 | 发布找货需求、需求状态跟踪 | ✅ |
| 门店信息 | 商场/专卖店/免税店、品牌列表 | ✅ |
| 个人中心 | 收藏、浏览历史、我的订单、我的需求 | ✅ |
| 订单系统 | 订单创建、微信支付、状态流转 | ✅ |
| VIP会员 | 套餐购买、会员权益、状态管理 | ✅ |
| 隐私政策 | 用户隐私保护说明 | ✅ |

### 后台管理系统

| 模块 | 功能 | 状态 |
|------|------|------|
| 登录 | 管理员账号登录 | ✅ |
| 仪表盘 | 数据概览、订单趋势、流量趋势、热门商品 | ✅ |
| 商品管理 | 品牌/分类/SPU/SKU/价格 全链路CRUD | ✅ |
| 用户管理 | 用户列表、角色设置、状态管理 | ✅ |
| 订单管理 | 订单查询、状态修改、详情查看 | ✅ |
| 买手管理 | 买手CRUD、国家筛选 | ✅ |
| 需求管理 | 需求列表、状态管理 | ✅ |
| 营销管理 | 优惠券、返点活动、开屏广告 | ✅ |
| 门店管理 | 门店CRUD、类型/国家筛选 | ✅ |
| 汇率管理 | 汇率查询、手动更新 | ✅ |
| 日志管理 | 访问日志、操作日志 | ✅ |

---

## 技术栈

### 小程序端
- **框架**：微信小程序原生开发
- **状态管理**：GlobalData + LocalStorage
- **网络请求**：封装 `wx.request`，支持 token 自动刷新
- **UI 组件**：原生组件 + 自定义样式

### 后端
- **框架**：FastAPI（Python 3.8+）
- **ORM**：SQLAlchemy 2.0
- **数据库**：SQLite（开发）/ MySQL（生产）
- **认证**：JWT (JSON Web Token)
- **支付**：微信支付（统一下单 + 回调验签）
- **部署**：Uvicorn + Nginx

### 后台管理
- **框架**：Vue 3 + Vite
- **UI 组件库**：Element Plus
- **图表**：ECharts
- **网络请求**：Axios
- **路由**：Vue Router 5

---

## 项目结构

```
.
├── app.js                    # 小程序入口
├── app.json                  # 小程序配置
├── project.config.json       # 项目配置
├── sitemap.json              # 站点地图
├── pages/                    # 小程序页面
│   ├── splash/               # 启动页（开屏广告）
│   ├── index/                # 比价首页
│   ├── rebate/               # 优惠/返点
│   ├── exchange/             # 汇率换算
│   ├── buyer/                # 买手/需求
│   ├── profile/              # 个人中心
│   ├── products/             # 商品列表
│   ├── product-detail/       # 商品详情
│   ├── stores/               # 门店
│   ├── coupons/              # 优惠券
│   ├── orders/               # 订单列表
│   ├── order-detail/         # 订单详情
│   ├── vip/                  # VIP会员
│   ├── favorites/            # 我的收藏
│   ├── history/              # 浏览历史
│   ├── my-coupons/           # 我的优惠券
│   ├── my-demands/           # 我的需求
│   └── privacy/              # 隐私政策
├── utils/                    # 工具函数
│   ├── request.js            # 网络请求封装
│   ├── config.js             # 环境配置
│   ├── util.js               # 通用工具
│   └── constants.js          # 常量定义
├── images/                   # 图片资源
├── server/                   # 后端服务（FastAPI）
│   ├── app.py                # 应用入口
│   ├── config.py             # 配置管理
│   ├── database.py           # 数据库连接
│   ├── models/               # 数据模型（SQLAlchemy）
│   ├── schemas/              # 数据校验（Pydantic）
│   ├── routers/              # API 路由
│   ├── utils/                # 工具函数（微信支付等）
│   └── .env.example          # 环境变量模板
├── admin/                    # 后台管理系统（Vue3）
│   ├── src/
│   │   ├── views/            # 页面组件
│   │   ├── api/              # API 请求
│   │   ├── router/           # 路由配置
│   │   ├── utils/            # 工具函数
│   │   ├── layout/           # 布局组件
│   │   └── assets/           # 静态资源
│   ├── index.html
│   ├── vite.config.js
│   └── package.json
└── docs/                     # 项目文档
    ├── 管理员使用说明书.md
    ├── 上线准备清单与发布流程.md
    └── 后端部署文档.md
```

---

## 快速开始

### 环境要求

| 环境 | 版本要求 |
|------|----------|
| Node.js | 16+ |
| Python | 3.8+ |
| 微信开发者工具 | 最新版 |
| 数据库 | SQLite（开发）/ MySQL 5.7+（生产） |

### 后端启动

```bash
# 1. 进入后端目录
cd server

# 2. 安装依赖
pip install fastapi uvicorn sqlalchemy pydantic python-multipart passlib[bcrypt] python-jose[cryptography] requests

# 3. 配置环境变量（可选，使用默认配置可跳过）
cp .env.example .env
# 编辑 .env 填入真实配置

# 4. 启动服务
python app.py
# 或使用 uvicorn
uvicorn app:app --host 0.0.0.0 --port 8000 --reload
```

服务启动后访问：http://localhost:8000

API 文档：http://localhost:8000/docs

### 小程序启动

1. 下载安装 [微信开发者工具](https://developers.weixin.qq.com/miniprogram/dev/devtools/download.html)
2. 打开微信开发者工具，选择「导入项目」
3. 选择项目根目录
4. 填入你的 AppID（测试可选「测试号」）
5. 点击「导入」即可运行

> 默认连接 `http://localhost:8000`，如需修改请编辑 [utils/config.js](utils/config.js)

### 后台管理启动

```bash
# 1. 进入后台目录
cd admin

# 2. 安装依赖
npm install

# 3. 启动开发服务
npm run dev

# 4. 构建生产版本
npm run build
```

默认管理员账号：`admin` / `admin123`

---

## 部署指南

### 后端部署

推荐方案：Nginx + Uvicorn + Systemd

详细部署步骤请参考：[后端部署文档.md](docs/后端部署文档.md)

```bash
# 核心命令
pip install -r requirements.txt
uvicorn app:app --host 127.0.0.1 --port 8000
```

### 小程序发布

详细发布流程请参考：[上线准备清单与发布流程.md](docs/上线准备清单与发布流程.md)

```
1. 填写 AppID → project.config.json
2. 切换生产环境 → utils/config.js
3. 配置服务器域名 → 微信公众平台
4. 真机调试 → 微信开发者工具
5. 上传代码 → 微信开发者工具
6. 提交审核 → 微信公众平台
7. 发布上线 → 全量发布
```

---

## 功能模块详解

### 商品价格体系

采用 SPU + SKU + SKUPrice 三层结构：

```
SPU（标准产品单元）—— 商品本身（如：Chanel Classic Flap）
  ├── SKU 1 —— 具体规格（如：中号/黑色/金扣）
  │     ├── 中国价格
  │     ├── 日本价格
  │     ├── 法国价格
  │     └── ...
  ├── SKU 2 —— 具体规格（如：小号/棕色/银扣）
  │     ├── 中国价格
  │     └── ...
  └── ...
```

### 开屏广告

- 后台配置广告内容（图片、时长、跳转链接）
- 支持启用/禁用开关
- 每日展示次数限制，避免骚扰用户
- 展示/点击数据统计

### 订单流程

```
创建订单 → 待支付 → 支付成功 → 待发货 → 已发货 → 待收货 → 确认收货 → 已完成
               ↓                        ↓
            取消订单                  申请退款
```

---

## 开发规范

### 命名规范

- 文件名：小写 + 连字符（`user-profile.js`）
- 变量名：小驼峰（`userName`）
- 常量名：大写 + 下划线（`MAX_COUNT`）
- API 路径：小写 + 下划线（`/api/user/my_coupons`）

### 提交规范

```
feat: 新功能
fix: 修复bug
docs: 文档更新
style: 代码格式调整
refactor: 重构
perf: 性能优化
test: 测试相关
chore: 构建/工具/依赖
```

---

## 常见问题

### Q：小程序请求接口报 "request:fail timeout"？
A：检查后端服务是否启动，以及 `utils/config.js` 中的 BASE_URL 是否正确。开发工具中需要勾选「不校验合法域名」。

### Q：微信登录返回 mock 数据？
A：未配置 `WECHAT_APPID` 和 `WECHAT_SECRET` 时，登录接口会返回模拟数据。在 `server/.env` 中填入真实配置即可。

### Q：后台管理登录失败？
A：默认账号 `admin/admin123`，如无法登录请检查后端服务是否正常运行，以及 API 地址是否正确。

### Q：如何切换生产环境？
A：编辑 `utils/config.js`，将 `ENV` 改为 `'production'`，并填入生产服务器域名。

更多问题请参考：[管理员使用说明书.md](docs/管理员使用说明书.md)

---

## 许可证

MIT License

---

<div align="center">

如果觉得这个项目对你有帮助，欢迎点个 ⭐ Star 支持一下！

</div>