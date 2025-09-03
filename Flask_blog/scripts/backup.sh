#!/bin/bash
# 生产环境自动备份脚本

set -euo pipefail

# 配置变量
BACKUP_DIR="/app/backups"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
RETENTION_DAYS=${BACKUP_RETENTION_DAYS:-30}
DB_NAME=${MYSQL_DATABASE:-blog}
DB_USER=${MYSQL_USER:-blog}
DB_PASSWORD=${MYSQL_PASSWORD}
DB_HOST=${DB_HOST:-db}

# 创建备份目录
mkdir -p "${BACKUP_DIR}/database"
mkdir -p "${BACKUP_DIR}/uploads"
mkdir -p "${BACKUP_DIR}/config"

echo "[$(date)] 开始备份流程..."

# 1. 数据库备份
echo "[$(date)] 备份MySQL数据库..."
mysqldump -h "${DB_HOST}" -u "${DB_USER}" -p"${DB_PASSWORD}" \
  --single-transaction \
  --routines \
  --triggers \
  --events \
  --hex-blob \
  --complete-insert \
  "${DB_NAME}" | gzip > "${BACKUP_DIR}/database/mysql_${DB_NAME}_${TIMESTAMP}.sql.gz"

# 验证数据库备份文件
if [ ! -s "${BACKUP_DIR}/database/mysql_${DB_NAME}_${TIMESTAMP}.sql.gz" ]; then
  echo "[$(date)] 错误: 数据库备份文件为空"
  exit 1
fi

# 2. 文件上传备份
echo "[$(date)] 备份上传文件..."
if [ -d "/app/backend/uploads_store" ]; then
  tar -czf "${BACKUP_DIR}/uploads/uploads_${TIMESTAMP}.tar.gz" -C /app/backend uploads_store/
  
  # 验证上传文件备份
  if [ ! -s "${BACKUP_DIR}/uploads/uploads_${TIMESTAMP}.tar.gz" ]; then
    echo "[$(date)] 警告: 上传文件备份为空"
  fi
else
  echo "[$(date)] 警告: 上传目录不存在，跳过文件备份"
fi

# 3. 配置文件备份
echo "[$(date)] 备份配置文件..."
if [ -f "/app/.env" ]; then
  # 脱敏处理敏感信息
  sed 's/=.*PASSWORD.*/=***REDACTED***/g; s/=.*SECRET.*/=***REDACTED***/g; s/=.*KEY.*/=***REDACTED***/g' \
    /app/.env > "${BACKUP_DIR}/config/env_${TIMESTAMP}.txt"
fi

# 备份docker-compose文件
if [ -f "/app/docker-compose.prod.yml" ]; then
  cp /app/docker-compose.prod.yml "${BACKUP_DIR}/config/docker-compose_${TIMESTAMP}.yml"
fi

# 4. Redis数据备份 (如果可用)
echo "[$(date)] 备份Redis数据..."
if command -v redis-cli >/dev/null 2>&1; then
  redis-cli --rdb "${BACKUP_DIR}/database/redis_${TIMESTAMP}.rdb" 2>/dev/null || echo "Redis备份失败，继续..."
fi

# 5. 创建备份清单
echo "[$(date)] 创建备份清单..."
cat > "${BACKUP_DIR}/manifest_${TIMESTAMP}.json" << EOF
{
  "backup_time": "${TIMESTAMP}",
  "backup_type": "full",
  "files": {
    "database": "database/mysql_${DB_NAME}_${TIMESTAMP}.sql.gz",
    "uploads": "uploads/uploads_${TIMESTAMP}.tar.gz",
    "config": "config/env_${TIMESTAMP}.txt",
    "redis": "database/redis_${TIMESTAMP}.rdb"
  },
  "retention_days": ${RETENTION_DAYS},
  "cleanup_date": "$(date -d "+${RETENTION_DAYS} days" +%Y-%m-%d)"
}
EOF

# 6. 清理过期备份
echo "[$(date)] 清理过期备份..."
find "${BACKUP_DIR}" -name "*.sql.gz" -mtime +${RETENTION_DAYS} -delete 2>/dev/null || true
find "${BACKUP_DIR}" -name "*.tar.gz" -mtime +${RETENTION_DAYS} -delete 2>/dev/null || true
find "${BACKUP_DIR}" -name "*.rdb" -mtime +${RETENTION_DAYS} -delete 2>/dev/null || true
find "${BACKUP_DIR}" -name "manifest_*.json" -mtime +${RETENTION_DAYS} -delete 2>/dev/null || true

# 7. 备份验证
echo "[$(date)] 验证备份完整性..."
DB_BACKUP_SIZE=$(stat -c%s "${BACKUP_DIR}/database/mysql_${DB_NAME}_${TIMESTAMP}.sql.gz" 2>/dev/null || echo 0)
if [ "${DB_BACKUP_SIZE}" -lt 1024 ]; then
  echo "[$(date)] 错误: 数据库备份文件过小 (${DB_BACKUP_SIZE} bytes)"
  exit 1
fi

# 8. 可选: 上传到云存储
if [ "${BACKUP_TO_CLOUD:-false}" = "true" ]; then
  echo "[$(date)] 上传备份到云存储..."
  # AWS S3 示例
  # aws s3 cp "${BACKUP_DIR}/database/mysql_${DB_NAME}_${TIMESTAMP}.sql.gz" \
  #   "s3://your-backup-bucket/blog-backups/database/"
  
  # 阿里云OSS示例
  # ossutil64 cp "${BACKUP_DIR}/database/mysql_${DB_NAME}_${TIMESTAMP}.sql.gz" \
  #   "oss://your-backup-bucket/blog-backups/database/"
fi

# 9. 备份报告
BACKUP_SIZE=$(du -sh "${BACKUP_DIR}" | cut -f1)
echo "[$(date)] 备份完成!"
echo "备份位置: ${BACKUP_DIR}"
echo "备份大小: ${BACKUP_SIZE}"
echo "备份清单: manifest_${TIMESTAMP}.json"

# 10. 可选: 发送通知
if [ "${BACKUP_NOTIFY:-false}" = "true" ]; then
  # 邮件通知示例
  # echo "备份完成 - ${TIMESTAMP}" | mail -s "Flask Blog 备份报告" admin@yourdomain.com
  
  # Slack通知示例
  # curl -X POST -H 'Content-type: application/json' \
  #   --data '{"text":"Flask Blog 备份完成: '${TIMESTAMP}'"}' \
  #   YOUR_SLACK_WEBHOOK_URL
fi

echo "[$(date)] 备份流程结束"