# 奢侈品比价小程序 - 本地开发指南

## 📁 项目结构

```
.
├── pages/                  # 微信小程序页面
├── utils/                  # 小程序工具函数
│   └── request.js          # API 请求封装
├── server/                 # 后端服务 (FastAPI)
│   ├── app.py              # 服务入口
│   ├── config.py           # 配置文件
│   ├── database.py         # 数据库连接
│   ├── models/             # 数据模型
│   ├── routers/            # API 路由
│   │   ├── admin.py        # 管理端 CRUD API
│   │   ├── admin_auth.py   # 管理员登录认证
│   │   ├── auth.py         # 小程序用户认证
│   │   ├── product.py      # 商品相关 API
│   │   └── ...
│   ├── init_data.py        # 数据库初始化脚本
│   ├── create_admin.py     # 管理员账号创建脚本
│   ├── requirements.txt    # Python 依赖
│   └── .env.example        # 环境变量模板
├── admin/                  # 管理后台前端 (纯 HTML/JS)
│   ├── index.html
│   └── app.js
├── start.sh                # Mac/Linux 启动脚本
├── start.bat               # Windows 启动脚本
├── app.json                # 小程序配置
├── project.config.json     # 小程序开发者工具配置
└── README.md               # 本文件
```

## 🚀 快速开始

### 前置要求

- Python 3.8+
- 微信开发者工具（用于调试小程序）
- 浏览器（用于访问管理后台）

### 方式一：一键启动（推荐）

**Mac/Linux:**
```bash
./start.sh
```

**Windows:**
```
双击 start.bat
```

脚本会自动完成：
1. 检查 Python 环境
2. 创建 .env 配置文件
3. 安装 Python 依赖
4. 初始化数据库和示例数据
5. 创建管理员账号
6. 启动后端服务

### 方式二：手动启动

#### 1. 安装依赖

```bash
cd server
pip install -r requirements.txt
```

#### 2. 配置环境变量

```bash
cd server
cp .env.example .env
```

编辑 `.env` 文件，根据需要修改配置（本地开发可保持默认）。

#### 3. 初始化数据库

```bash
cd server
python init_data.py
python create_admin.py
```

#### 4. 启动后端服务

```bash
cd server
python app.py
```

## 🌐 访问地址

启动成功后，可通过以下地址访问：

| 服务 | 地址 | 说明 |
|------|------|------|
| API 服务 | http://localhost:8000 | 后端接口服务 |
| 管理后台 | http://localhost:8000/admin/ | 数据管理后台 |
| 接口文档 | http://localhost:8000/docs | Swagger 自动生成的 API 文档 |
| 健康检查 | http://localhost:8000/health | 服务健康状态 |

### 管理后台默认账号

- 账号：`admin`
- 密码：`admin123`

> ⚠️ 请在生产环境及时修改默认密码！

## 📱 小程序调试

### 1. 打开微信开发者工具

- 选择「导入项目」
- 项目目录选择本项目根目录
- AppID 可选择「测试号」（本地开发无需真实 AppID）

### 2. 配置说明

- 小程序的 API 地址默认为 `http://localhost:8000`
- 已关闭域名校验（`urlCheck: false`），本地开发可直接使用 http
- 请求日志默认开启，可在调试器 Console 中查看

### 3. 切换环境

在 `utils/request.js` 中修改 `currentEnv`：

```javascript
const currentEnv = 'development';  // 本地开发
// const currentEnv = 'production'; // 生产环境
```

## 🔧 管理后台功能

管理后台支持以下数据模块的增删改查：

- 📊 **仪表盘** - 数据统计概览
- 🛍️ **商品管理** - SPU + SKU + 价格管理
- 🏷️ **品牌管理** - 品牌信息维护
- 📂 **品类管理** - 商品分类管理
- 🏪 **门店管理** - 线下门店信息
- 🎟️ **优惠券管理** - 优惠券活动
- 👤 **买手管理** - 代购买手信息
- 📋 **需求管理** - 用户求购需求
- 💎 **返点管理** - 返点活动配置
- 💱 **汇率管理** - 多国货币汇率
- 👥 **用户管理** - 小程序用户管理

## 🗄️ 数据库说明

本地开发使用 SQLite 数据库，文件位于：
```
server/database.db
```

如需重置数据库，删除该文件后重新运行初始化脚本即可。

## ⚙️ 环境变量配置

| 变量 | 默认值 | 说明 |
|------|--------|------|
| HOST | 0.0.0.0 | 服务监听地址 |
| PORT | 8000 | 服务端口 |
| DEBUG | true | 调试模式 |
| DATABASE_URL | sqlite:///./database.db | 数据库连接地址 |
| SECRET_KEY | ... | JWT 签名密钥（生产环境务必修改） |
| WECHAT_APPID | （空） | 微信小程序 AppID（留空则使用 mock） |
| WECHAT_SECRET | （空） | 微信小程序 Secret（留空则使用 mock） |
| ADMIN_USERNAME | admin | 管理员默认账号 |
| ADMIN_PASSWORD | admin123 | 管理员默认密码 |

## 🔌 API 接口

所有接口统一返回格式：
```json
{
  "code": 0,
  "message": "success",
  "data": {}
}
```

- `code = 0` 表示成功
- `code != 0` 表示失败，`message` 为错误信息

### 小程序端主要接口

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /api/auth/login | 微信登录 |
| GET | /api/product/search | 商品搜索 |
| GET | /api/product/product-detail/:id | 商品详情 |
| GET | /api/exchange/rates | 汇率查询 |
| GET | /api/coupon/list | 优惠券列表 |
| GET | /api/store/list | 门店列表 |
| GET | /api/rebate/list | 返点列表 |
| GET | /api/buyer/list | 买手列表 |
| GET/POST | /api/demand/... | 需求管理 |

### 管理端接口

所有管理端接口需在 Header 中携带 Token：
```
Authorization: Bearer <token>
```

## 🧪 本地开发技巧

### 查看数据库

推荐使用以下工具查看 SQLite 数据库：
- DB Browser for SQLite
- VS Code 插件：SQLite Viewer

### 热重载

本地开发时后端服务开启了热重载（`reload=True`），修改代码后会自动重启。

### 调试接口

访问 `http://localhost:8000/docs` 可以直接在浏览器中测试所有 API 接口。

## 📦 部署到生产

1. 修改 `.env` 中的配置：
   - `DEBUG=false`
   - `SECRET_KEY` 设置为强随机字符串
   - `DATABASE_URL` 可改为 MySQL/PostgreSQL 等
   - 配置 `WECHAT_APPID` 和 `WECHAT_SECRET`

2. 修改小程序 `utils/request.js` 中的 `currentEnv` 为 `production`，并设置正确的 `baseUrl`

3. 部署后端服务（推荐使用 uvicorn + gunicorn + nginx）

## ❓ 常见问题

### 1. 小程序请求失败？

- 确保后端服务已启动
- 检查 `utils/request.js` 中的 `baseUrl` 是否正确
- 确认开发者工具中「不校验合法域名」已开启

### 2. 管理后台无法登录？

- 确认管理员账号已创建（运行 `python create_admin.py`）
- 检查密码是否正确（默认 admin123）

### 3. 如何重置数据库？

```bash
cd server
rm database.db
python init_data.py
python create_admin.py
```

### 4. 微信登录失败？

本地开发未配置 AppID 时，系统会自动使用 mock 模式，可正常登录使用。
如需真实微信登录，请在 `.env` 中配置 `WECHAT_APPID` 和 `WECHAT_SECRET`。
