#!/bin/bash
# 齐谐科技 — SSL 证书初始化脚本
# 首次运行: bash infra/ssl/setup.sh
# 证书续期: docker compose exec certbot certbot renew
set -euo pipefail

DOMAINS=(
  "felix2026.cc.cd"
  "openclaw.qixie.tech"
)
EMAIL="${SSL_EMAIL:-admin@qixie.tech}"

echo "=== 创建 Certbot 所需目录 ==="
mkdir -p ./infra/ssl/certbot/conf ./infra/ssl/certbot/www

echo "=== 启动临时 Nginx 用于 HTTP 验证 ==="
docker compose up -d nginx-proxy
sleep 3

for domain in "${DOMAINS[@]}"; do
  echo "=== 申请证书: $domain ==="
  docker compose run --rm certbot certonly \
    --webroot \
    --webroot-path=/var/www/certbot \
    --email "$EMAIL" \
    --agree-tos \
    --no-eff-email \
    --force-renewal \
    -d "$domain"
done

echo "=== 重启 Nginx 加载新证书 ==="
docker compose restart nginx-proxy

echo "=== 完成 ==="
echo "证书位置: ./infra/ssl/certbot/conf/live/"
echo "自动续期: docker-compose 中 certbot 每 12h 自动检查续期"
