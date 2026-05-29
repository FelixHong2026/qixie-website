#!/bin/bash
# 齐谐科技 — 数据库备份脚本
# 在 PostgreSQL 容器运行后，通过 cron 定时调用
#
# 安装 cron:
#   0 3 * * * /home/felix/qixie/scripts/backup-db.sh
#
# 前提: docker compose 中 db 服务已启用 (CMP-129 完成后)

set -euo pipefail

BACKUP_DIR="${BACKUP_DIR:-./backups}"
DB_CONTAINER="${DB_CONTAINER:-qixie-db}"
DB_USER="${DB_USER:-qixie}"
DB_NAME="${DB_NAME:-qixie}"
RETENTION_DAYS="${RETENTION_DAYS:-30}"

mkdir -p "$BACKUP_DIR"

timestamp=$(date '+%Y%m%d_%H%M%S')
backup_file="${BACKUP_DIR}/${DB_NAME}_${timestamp}.sql.gz"

echo "=== 数据库备份: $(date) ==="

# 检查容器是否运行
if docker inspect --format='{{.State.Status}}' "$DB_CONTAINER" 2>/dev/null | grep -q running; then
  echo "备份: $DB_NAME → $backup_file"
  docker compose exec -T db pg_dump -U "$DB_USER" "$DB_NAME" | gzip > "$backup_file"
  echo "完成: $(ls -lh "$backup_file" | awk '{print $5}')"

  # 清理旧备份
  echo "清理 ${RETENTION_DAYS} 天前的备份..."
  find "$BACKUP_DIR" -name "${DB_NAME}_*.sql.gz" -mtime "+$RETENTION_DAYS" -delete
else
  echo "跳过: $DB_CONTAINER 未运行"
fi

echo "=== 备份完成 ==="
