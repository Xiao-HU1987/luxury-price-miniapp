#!/bin/bash
# 奢侈品比价小程序 - 本地开发启动脚本 (Mac/Linux)

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SERVER_DIR="$SCRIPT_DIR/server"

echo "=========================================="
echo "  奢侈品比价小程序 - 本地开发环境启动"
echo "=========================================="
echo ""

cd "$SERVER_DIR"

# 1. 检查 Python
if ! command -v python3 &> /dev/null; then
    echo "❌ 未找到 python3，请先安装 Python 3.8+"
    exit 1
fi

# 2. 检查 .env 文件，如果不存在则从模板创建
if [ ! -f ".env" ]; then
    echo "📝 未找到 .env 文件，正在从 .env.example 创建..."
    cp .env.example .env
    echo "✅ .env 文件已创建，可根据需要修改配置"
    echo ""
fi

# 3. 安装依赖
echo "📦 检查并安装 Python 依赖..."
pip3 install -r requirements.txt -q
echo "✅ 依赖安装完成"
echo ""

# 4. 初始化数据库
echo "🗄️  初始化数据库..."
python3 init_data.py
echo ""

# 5. 创建管理员账号
echo "👤 创建管理员账号..."
python3 create_admin.py
echo ""

# 6. 启动服务
echo "🚀 启动后端服务..."
echo ""
echo "=========================================="
echo "  服务启动成功！"
echo ""
echo "  API 地址:   http://localhost:8000"
echo "  管理后台:   http://localhost:8000/admin/"
echo "  接口文档:   http://localhost:8000/docs"
echo ""
echo "  管理员账号: admin / admin123"
echo "=========================================="
echo ""

python3 app.py
