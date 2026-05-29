#!/bin/bash
# 齐谐科技 — 生产健康检查脚本
# 用于监控告警，可被 cron 定时调用
# 失败时发送 Webhook 通知
#
# 用法:
#   bash scripts/health-check.sh                # 标准检查
#   bash scripts/health-check.sh --webhook URL   # 失败时通知 Webhook

set -euo pipefail

# 配置
DOMAIN="${DOMAIN:-felix2026.cc.cd}"
ALERT_WEBHOOK="${1:-}"

# 颜色
RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m'

failures=0
fail_msgs=""

check() {
  local name="$1"
  local result="$2"
  if [ "$result" -eq 0 ]; then
    echo -e "  ${GREEN}✓${NC} $name"
  else
    echo -e "  ${RED}✗${NC} $name"
    failures=$((failures + 1))
    fail_msgs="$fail_msgs\n  ✗ $name"
  fi
}

echo "=== 齐谐科技 — 健康检查 ==="
echo "时间: $(date '+%Y-%m-%d %H:%M:%S')"
echo ""

# 1. Docker 守护进程
echo "--- Docker 引擎 ---"
check "Docker 运行中" $(docker info --format '{{.ServerVersion}}' >/dev/null 2>&1; echo $?)

# 2. 核心容器
echo "--- 容器状态 ---"
for container in qixie-nginx qixie-site; do
  status=$(docker inspect --format='{{.State.Status}}' "$container" 2>/dev/null || echo "not_found")
  if [ "$status" = "running" ]; then
    check "容器 $container" 0
  else
    check "容器 $container (状态: $status)" 1
  fi
done

# 3. 健康检查端点
echo "--- HTTP 检查 ---"
http_code=$(curl -so /dev/null -w '%{http_code}' --connect-timeout 5 http://localhost/health 2>/dev/null || echo "000")
check "本地 /health (HTTP $http_code)" $( [ "$http_code" = "200" ] && echo 0 || echo 1 )

http_code=$(curl -so /dev/null -w '%{http_code}' --connect-timeout 5 http://localhost/ 2>/dev/null || echo "000")
check "本地首页 (HTTP $http_code)" $( [ "$http_code" = "200" ] && echo 0 || echo 1 )

# 4. SSL 证书到期检查
echo "--- SSL 检查 ---"
cert_file="infra/ssl/certbot/conf/live/$DOMAIN/fullchain.pem"
if [ -f "$cert_file" ]; then
  expiry=$(openssl x509 -enddate -noout -in "$cert_file" 2>/dev/null | cut -d= -f2)
  expiry_epoch=$(date -d "$expiry" +%s 2>/dev/null || echo 0)
  now_epoch=$(date +%s)
  days_left=$(( (expiry_epoch - now_epoch) / 86400 ))
  if [ "$days_left" -gt 30 ]; then
    check "SSL 证书 ($days_left 天后到期)" 0
  elif [ "$days_left" -gt 7 ]; then
    echo -e "  ${GREEN}✓${NC} SSL 证书 ($days_left 天后到期，即将续期)"
  else
    check "SSL 证书 ($days_left 天后到期，需要续期)" 1
  fi
else
  echo -e "  ${GREEN}∼${NC} SSL 证书尚未申请 (跳过)"
fi

# 5. 磁盘使用
echo "--- 磁盘检查 ---"
disk_usage=$(df / | tail -1 | awk '{print $5}' | sed 's/%//')
if [ "$disk_usage" -lt 80 ]; then
  check "磁盘使用率 ${disk_usage}%" 0
else
  check "磁盘使用率 ${disk_usage}% (超过 80%)" 1
fi

# 6. 内存
echo "--- 内存检查 ---"
mem_available=$(free | grep Mem | awk '{print $7}')
mem_total=$(free | grep Mem | awk '{print $2}')
mem_pct=$(( (mem_total - mem_available) * 100 / mem_total ))
if [ "$mem_pct" -lt 80 ]; then
  check "内存使用率 ${mem_pct}%" 0
else
  check "内存使用率 ${mem_pct}% (超过 80%)" 1
fi

# 结果
echo ""
if [ "$failures" -eq 0 ]; then
  echo -e "${GREEN}✓ 全部检查通过${NC}"
  exit 0
else
  echo -e "${RED}✗ $failures 项检查失败${NC}"
  echo -e "失败项:$fail_msgs"

  # Webhook 通知
  if [ -n "$ALERT_WEBHOOK" ]; then
    payload="{\"text\":\"齐谐科技 — 健康检查失败\n$fail_msgs\n时间: $(date '+%Y-%m-%d %H:%M:%S')\"}"
    curl -s -X POST -H "Content-Type: application/json" -d "$payload" "$ALERT_WEBHOOK" >/dev/null 2>&1 && \
      echo "Webhook 通知已发送" || echo "Webhook 发送失败"
  fi

  exit 1
fi
