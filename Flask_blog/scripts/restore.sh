#!/bin/bash
# 生产环境数据恢复脚本

set -euo pipefail

# 显示使用说明
show_usage() {
  cat << EOF
使用方法: $0 [选项] <备份时间戳>

选项:
  -d, --database-only    仅恢复数据库
  -f, --files-only       仅恢复文件
  -c, --config-only      仅恢复配置文件
  -y, --yes             跳过确认提示
  -h, --help            显示此帮助信息

示例:
  $0 20231201_143020                    # 完整恢复
  $0 -d 20231201_143020                 # 仅恢复数据库
  $0 -f 20231201_143020                 # 仅恢复文件
  $0 --yes 20231201_143020              # 跳过确认
EOF
}

# 解析命令行参数
RESTORE_DATABASE=true
RESTORE_FILES=true
RESTORE_CONFIG=true
SKIP_CONFIRM=false
TIMESTAMP=""

while [[ $# -gt 0 ]]; do
  case $1 in
    -d|--database-only)
      RESTORE_DATABASE=true
      RESTORE_FILES=false
      RESTORE_CONFIG=false
      shift
      ;;
    -f|--files-only)
      RESTORE_DATABASE=false
      RESTORE_FILES=true
      RESTORE_CONFIG=false
      shift
      ;;
    -c|--config-only)
      RESTORE_DATABASE=false
      RESTORE_FILES=false
      RESTORE_CONFIG=true
      shift
      ;;
    -y|--yes)
      SKIP_CONFIRM=true
      shift
      ;;
    -h|--help)
      show_usage
      exit 0
      ;;
    *)
      if [ -z "${TIMESTAMP}" ]; then
        TIMESTAMP="$1"
      else
        echo "错误: 未知参数 $1"
        show_usage
        exit 1
      fi
      shift
      ;;
  esac
done

# 检查必需参数
if [ -z "${TIMESTAMP}" ]; then
  echo "错误: 必须指定备份时间戳"
  show_usage
  exit 1
fi

# 配置变量
BACKUP_DIR="/app/backups"
DB_NAME=${MYSQL_DATABASE:-blog}
DB_USER=${MYSQL_USER:-blog}
DB_PASSWORD=${MYSQL_PASSWORD}
DB_HOST=${DB_HOST:-db}
MANIFEST_FILE="${BACKUP_DIR}/manifest_${TIMESTAMP}.json"

echo "[$(date)] 开始恢复流程 - 时间戳: ${TIMESTAMP}"

# 检查备份清单文件
if [ ! -f "${MANIFEST_FILE}" ]; then
  echo "错误: 找不到备份清单文件: ${MANIFEST_FILE}"
  echo "可用的备份:"
  ls -la "${BACKUP_DIR}"/manifest_*.json 2>/dev/null || echo "  没有可用的备份"
  exit 1
fi

# 读取备份清单
echo "[$(date)] 读取备份清单..."
if command -v jq >/dev/null 2>&1; then
  BACKUP_TYPE=$(jq -r '.backup_type' "${MANIFEST_FILE}")
  DB_BACKUP_FILE=$(jq -r '.files.database' "${MANIFEST_FILE}")
  UPLOADS_BACKUP_FILE=$(jq -r '.files.uploads' "${MANIFEST_FILE}")
  CONFIG_BACKUP_FILE=$(jq -r '.files.config' "${MANIFEST_FILE}")
else
  echo "警告: 未安装jq，使用简单解析"
  DB_BACKUP_FILE="database/mysql_${DB_NAME}_${TIMESTAMP}.sql.gz"
  UPLOADS_BACKUP_FILE="uploads/uploads_${TIMESTAMP}.tar.gz"
  CONFIG_BACKUP_FILE="config/env_${TIMESTAMP}.txt"
fi

# 验证备份文件存在
validate_backup_files() {
  local errors=0
  
  if [ "${RESTORE_DATABASE}" = "true" ] && [ ! -f "${BACKUP_DIR}/${DB_BACKUP_FILE}" ]; then
    echo "错误: 数据库备份文件不存在: ${BACKUP_DIR}/${DB_BACKUP_FILE}"
    errors=$((errors + 1))
  fi
  
  if [ "${RESTORE_FILES}" = "true" ] && [ ! -f "${BACKUP_DIR}/${UPLOADS_BACKUP_FILE}" ]; then
    echo "错误: 文件备份不存在: ${BACKUP_DIR}/${UPLOADS_BACKUP_FILE}"
    errors=$((errors + 1))
  fi
  
  if [ "${RESTORE_CONFIG}" = "true" ] && [ ! -f "${BACKUP_DIR}/${CONFIG_BACKUP_FILE}" ]; then
    echo "错误: 配置备份不存在: ${BACKUP_DIR}/${CONFIG_BACKUP_FILE}"
    errors=$((errors + 1))
  fi
  
  if [ $errors -gt 0 ]; then
    echo "发现 $errors 个备份文件缺失"
    exit 1
  fi
}

echo "[$(date)] 验证备份文件..."
validate_backup_files

# 显示恢复信息并确认
echo "========================================"
echo "恢复信息:"
echo "备份时间戳: ${TIMESTAMP}"
echo "恢复数据库: ${RESTORE_DATABASE}"
echo "恢复文件: ${RESTORE_FILES}"
echo "恢复配置: ${RESTORE_CONFIG}"
echo "========================================"

if [ "${SKIP_CONFIRM}" = "false" ]; then
  read -p "确认要执行恢复操作吗? 这将覆盖当前数据 (y/N): " -r
  if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "恢复操作已取消"
    exit 0
  fi
fi

# 1. 恢复数据库
if [ "${RESTORE_DATABASE}" = "true" ]; then
  echo "[$(date)] 恢复MySQL数据库..."
  
  # 创建数据库备份 (预防措施)
  echo "创建当前数据库快照..."
  mysqldump -h "${DB_HOST}" -u "${DB_USER}" -p"${DB_PASSWORD}" \
    --single-transaction "${DB_NAME}" | gzip > "${BACKUP_DIR}/pre-restore-${TIMESTAMP}_$(date +%Y%m%d_%H%M%S).sql.gz"
  
  # 恢复数据库
  echo "开始数据库恢复..."
  gunzip -c "${BACKUP_DIR}/${DB_BACKUP_FILE}" | mysql -h "${DB_HOST}" -u "${DB_USER}" -p"${DB_PASSWORD}" "${DB_NAME}"
  
  if [ $? -eq 0 ]; then
    echo "数据库恢复完成"
  else
    echo "错误: 数据库恢复失败"
    exit 1
  fi
fi

# 2. 恢复文件
if [ "${RESTORE_FILES}" = "true" ]; then
  echo "[$(date)] 恢复上传文件..."
  
  # 备份当前文件 (预防措施)
  if [ -d "/app/backend/uploads_store" ]; then
    echo "创建当前文件快照..."
    tar -czf "${BACKUP_DIR}/pre-restore-uploads-${TIMESTAMP}_$(date +%Y%m%d_%H%M%S).tar.gz" -C /app/backend uploads_store/
  fi
  
  # 创建目标目录
  mkdir -p /app/backend
  
  # 恢复文件
  echo "开始文件恢复..."
  tar -xzf "${BACKUP_DIR}/${UPLOADS_BACKUP_FILE}" -C /app/backend/
  
  # 设置正确的权限
  chown -R 1000:1000 /app/backend/uploads_store/ 2>/dev/null || true
  chmod -R 755 /app/backend/uploads_store/ 2>/dev/null || true
  
  if [ $? -eq 0 ]; then
    echo "文件恢复完成"
  else
    echo "错误: 文件恢复失败"
    exit 1
  fi
fi

# 3. 恢复配置文件
if [ "${RESTORE_CONFIG}" = "true" ]; then
  echo "[$(date)] 恢复配置文件..."
  echo "注意: 配置文件包含脱敏信息，需要手动更新敏感数据"
  
  # 备份当前配置
  if [ -f "/app/.env" ]; then
    cp /app/.env "/app/.env.backup-$(date +%Y%m%d_%H%M%S)"
  fi
  
  # 显示配置文件内容 (供参考)
  echo "备份的配置文件内容 (敏感信息已脱敏):"
  cat "${BACKUP_DIR}/${CONFIG_BACKUP_FILE}"
  echo ""
  echo "请手动更新 /app/.env 文件中的敏感信息"
fi

# 4. 验证恢复结果
echo "[$(date)] 验证恢复结果..."

if [ "${RESTORE_DATABASE}" = "true" ]; then
  # 检查数据库连接
  mysql -h "${DB_HOST}" -u "${DB_USER}" -p"${DB_PASSWORD}" -e "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='${DB_NAME}';" > /dev/null
  if [ $? -eq 0 ]; then
    echo "✓ 数据库连接正常"
  else
    echo "✗ 数据库连接失败"
  fi
fi

if [ "${RESTORE_FILES}" = "true" ]; then
  # 检查文件目录
  if [ -d "/app/backend/uploads_store" ]; then
    FILE_COUNT=$(find /app/backend/uploads_store -type f | wc -l)
    echo "✓ 文件恢复完成，共 ${FILE_COUNT} 个文件"
  else
    echo "✗ 文件目录不存在"
  fi
fi

# 5. 生成恢复报告
echo "[$(date)] 生成恢复报告..."
cat > "${BACKUP_DIR}/restore_report_$(date +%Y%m%d_%H%M%S).txt" << EOF
========================================
Flask Blog 数据恢复报告
========================================
恢复时间: $(date)
备份时间戳: ${TIMESTAMP}
恢复类型:
  - 数据库: ${RESTORE_DATABASE}
  - 文件: ${RESTORE_FILES}
  - 配置: ${RESTORE_CONFIG}

恢复状态: 成功完成
========================================
EOF

echo "[$(date)] 恢复流程完成!"
echo ""
echo "重要提醒:"
echo "1. 如果恢复了配置文件，请检查并更新敏感信息"
echo "2. 建议重启应用服务以确保所有更改生效"
echo "3. 验证应用功能是否正常工作"
echo ""
echo "重启命令示例:"
echo "  docker compose -f docker-compose.prod.yml restart backend"
echo "  docker compose -f docker-compose.prod.yml restart celery_worker"