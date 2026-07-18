#!/bin/bash

set -e

echo "Starting Luxury Price Miniapp API..."

# 每次启动都执行 init_data.py（内部按 if count() == 0 幂等判断）
# - SQLite 首次启动会建表 + 灌测试数据
# - MySQL 已有数据时跳过，空库时建表 + 灌测试数据
# - 容器重启/横向扩容不会重复写入
echo "Ensuring database tables and seed data..."
python init_data.py || echo "WARN: init_data.py failed, continuing startup..."

uvicorn app:app --host 0.0.0.0 --port ${PORT:-8080}
