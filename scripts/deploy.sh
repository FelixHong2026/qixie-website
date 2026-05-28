#!/bin/bash
# 齐谐科技 — 生产部署脚本
# 在目标服务器上执行：bash scripts/deploy.sh
set -euo pipefail

cd "$(dirname "$0")/.."

echo "=== 拉取最新代码 ==="
git pull origin main

echo "=== 构建并启动服务 ==="
docker compose build
docker compose up -d

echo "=== 清理旧镜像 ==="
docker image prune -f

echo "=== 查看运行状态 ==="
docker compose ps

echo "=== 部署完成 ==="
