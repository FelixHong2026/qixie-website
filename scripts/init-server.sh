#!/bin/bash
# 齐谐科技 — 服务器首次初始化脚本
# 在新服务器上首次部署时运行: bash scripts/init-server.sh
set -euo pipefail

cd "$(dirname "$0")/.."
PROJECT_DIR=$(pwd)
echo "=== 齐谐科技 — 服务器初始化 ==="
echo "目标目录: $PROJECT_DIR"

# 1. 检查环境
echo ""
echo "=== Step 1/6: 检查环境 ==="
command -v docker >/dev/null 2>&1 || { echo "错误: 未安装 Docker"; exit 1; }
docker info --format 'Docker {{.ServerVersion}}' 2>/dev/null || { echo "错误: Docker 未运行"; exit 1; }
echo "环境检查通过"

# 2. 创建 .env (如不存在)
echo ""
echo "=== Step 2/6: 环境变量 ==="
if [ ! -f .env ]; then
  cp .env.example .env
  echo "已创建 .env，请编辑填入实际值:"
  echo "  vi .env"
  echo "  # 至少需要设置: SSL_EMAIL, DB_PASSWORD"
  echo ""
  echo -n "是否继续? (y/N) "
  read -r answer
  if [ "$answer" != "y" ] && [ "$answer" != "Y" ]; then
    echo "退出: 请先配置 .env"
    exit 1
  fi
else
  echo ".env 已存在"
fi

# 3. 创建 SSL 证书目录
echo ""
echo "=== Step 3/6: SSL 证书 ==="
mkdir -p infra/ssl/certbot/conf infra/ssl/certbot/www

# 4. 初始化 SSL (首次申请)
echo ""
echo "=== Step 4/6: 申请 SSL 证书 ==="
echo "注意: 域名 DNS 需已指向本机 IP，且 80 端口可访问"
echo -n "是否立即申请 SSL 证书? (y/N) "
read -r answer
if [ "$answer" = "y" ] || [ "$answer" = "Y" ]; then
  bash infra/ssl/setup.sh
else
  echo "跳过 SSL 申请，可使用 --profile ssl 启动 certbot 稍后申请"
fi

# 5. 启动全栈
echo ""
echo "=== Step 5/6: 启动服务 ==="
echo "启动核心服务..."
docker compose up -d nginx-proxy qixie-site
echo "核心服务已启动"

# 6. 验证
echo ""
echo "=== Step 6/6: 验证 ==="
sleep 5
echo "--- 容器状态 ---"
docker compose ps

echo ""
echo "--- 健康检查 ---"
if curl -sf http://localhost/health > /dev/null 2>&1; then
  echo "✓ 健康检查通过"
else
  echo "✗ 健康检查失败，请检查日志: docker compose logs"
fi

echo ""
echo "=== 初始化完成 ==="
echo "网站: http://felix2026.cc.cd (DNS 配置后)"
echo "管理: http://localhost:9000 (Portainer)"
echo ""
echo "后续操作:"
echo "- 编辑 .env 完成配置"
echo "- 如果未申请 SSL: bash infra/ssl/setup.sh"
echo "- 查看日志: docker compose logs -f"
