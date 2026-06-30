@echo off
REM 奢侈品比价小程序 - 本地开发启动脚本 (Windows)

chcp 65001 >nul
setlocal enabledelayedexpansion

set SCRIPT_DIR=%~dp0
set SERVER_DIR=%SCRIPT_DIR%server

echo ==========================================
echo   奢侈品比价小程序 - 本地开发环境启动
echo ==========================================
echo.

cd /d "%SERVER_DIR%"

REM 1. 检查 Python
where python >nul 2>nul
if errorlevel 1 (
    echo ❌ 未找到 python，请先安装 Python 3.8+
    pause
    exit /b 1
)

REM 2. 检查 .env 文件
if not exist ".env" (
    echo 📝 未找到 .env 文件，正在从 .env.example 创建...
    copy .env.example .env >nul
    echo ✅ .env 文件已创建，可根据需要修改配置
    echo.
)

REM 3. 安装依赖
echo 📦 检查并安装 Python 依赖...
pip install -r requirements.txt -q
echo ✅ 依赖安装完成
echo.

REM 4. 初始化数据库
echo 🗄️  初始化数据库...
python init_data.py
echo.

REM 5. 创建管理员账号
echo 👤 创建管理员账号...
python create_admin.py
echo.

REM 6. 启动服务
echo 🚀 启动后端服务...
echo.
echo ==========================================
echo   服务启动成功！
echo.
echo   API 地址:   http://localhost:8000
echo   管理后台:   http://localhost:8000/admin/
echo   接口文档:   http://localhost:8000/docs
echo.
echo   管理员账号: admin / admin123
echo ==========================================
echo.

python app.py

pause
