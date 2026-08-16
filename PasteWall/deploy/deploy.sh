#!/usr/bin/env bash
# PasteWall 部署脚本 —— 在 Windows 的 Git Bash 中运行
#
#   bash deploy/deploy.sh                          # 免密 sudo 模式
#   SUDO_PASS=xxx bash deploy/deploy.sh            # 密码模式(SSH 密码也可用于 sudo)
#   SSH_ASKPASS=<脚本> SSH_ASKPASS_REQUIRE=force bash deploy/deploy.sh   # ssh 用密码登录时
#
# 环境变量:
#   SSH_HOST=<服务器IP>    (必填;本仓库不内置服务器地址)
#   SSH_USER=<你的用户名>     (本机 $USER 为空时必须显式指定)
#   PORT=3002
#   SUDO_PASS=<sudo密码>      (可选;设置后以密码方式执行远端 sudo,不写盘)
#
# 前置条件:
#   - 本机能 ssh/tar 到远端(Git Bash 自带)
#   - 远端已安装 Node.js v22+、systemd
#   - ssh 可登录(密钥或 SSH_ASKPASS 密码),sudo 可用(免密或 SUDO_PASS)
set -euo pipefail

SSH_HOST="${SSH_HOST:-}"
SSH_USER="${SSH_USER:-${USER:-}}"
PORT="${PORT:-3002}"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT="$(dirname "$HERE")"

GREEN=$'\033[1;32m'; YELLOW=$'\033[1;33m'; RED=$'\033[1;31m'; NC=$'\033[0m'
step(){ printf "${GREEN}\n==> %s${NC}\n" "$*"; }
warn(){ printf "${YELLOW}警告: %s${NC}\n" "$*"; }
die(){ printf "${RED}[deploy] 错误: %s${NC}\n" "$*" >&2; exit 1; }
[ -n "$SSH_HOST" ] || die "未指定 SSH_HOST(仓库不内置服务器地址)。请设置: SSH_HOST=<服务器IP>"
[ -n "$SSH_USER" ] || die "未指定 SSH_USER(本机 \$USER 为空)。请设置: SSH_USER=<你的用户名>"
DEST="${SSH_USER}@${SSH_HOST}"

rssh(){ ssh -o ConnectTimeout=8 -o StrictHostKeyChecking=accept-new "$DEST" "$@"; }
# sudo 执行:密码模式用 sudo -S 从 stdin 取密码(无 tty 不共享缓存,故每条都喂);否则免密 sudo -n
rssh_sudo(){
  if [ -n "${SUDO_PASS:-}" ]; then
    printf '%s\n' "$SUDO_PASS" | rssh "sudo -S -p '' $*"
  else
    rssh "sudo -n $*"
  fi
}

command -v ssh >/dev/null || die "本机缺少 ssh"
command -v tar >/dev/null || die "本机缺少 tar"

step "1/6 构建前端(本地)"
command -v npm >/dev/null || die "本机缺少 npm"
(cd "$PROJECT/frontend" && npm ci && npm run build) || die "前端构建失败"
echo "  前端已构建到 frontend/dist"

step "2/6 检查远端(${DEST})"
rssh 'command -v node >/dev/null' || die "远端未安装 Node.js"
NODE_BIN="$(rssh 'command -v node')"
NODE_VER="$(rssh 'node -v')"
echo "  远端 Node: ${NODE_BIN} (${NODE_VER})"
NODE_HOME=0
case "$NODE_BIN" in
  /home/*|/Users/*)
    NODE_HOME=1
    echo "  → Node 位于用户 home 目录(nvm 等),将用现有用户运行并放宽 ProtectHome 加固"
    ;;
esac
if [ -n "${SUDO_PASS:-}" ]; then
  printf '%s\n' "$SUDO_PASS" | rssh "sudo -S -p '' -v" >/dev/null 2>&1 \
    || die "SUDO_PASS 验证失败(密码不正确?),或远端拒绝该用户 sudo"
  echo "  已确认密码模式 sudo 可用"
else
  rssh "sudo -n true" >/dev/null 2>&1 \
    || die "远端 sudo 需要密码。请设置 SUDO_PASS 环境变量,或配置免密 sudo(visudo 添加 NOPASSWD)。"
fi

step "3/6 确定服务用户"
if [ "$NODE_HOME" = 1 ]; then
  SERVICE_USER="$SSH_USER"
else
  SERVICE_USER="pastewall"
  if ! rssh 'id -u pastewall >/dev/null 2>&1'; then
    rssh_sudo "useradd --system --no-create-home --shell /usr/sbin/nologin pastewall"
    echo "  已创建系统用户 pastewall"
  fi
fi
echo "  服务将以用户 ${SERVICE_USER} 运行"

step "4/6 同步代码到 /opt/pastewall(保留 data/ 数据)"
tar czf - --exclude='./data' --exclude='./.git' --exclude='./node_modules' --exclude='./frontend/node_modules' --exclude='*.log' -C "$PROJECT" . \
  | rssh "cat > /tmp/pastewall.tgz"
rssh_sudo "mkdir -p /opt/pastewall"
rssh_sudo "tar xzf /tmp/pastewall.tgz -C /opt/pastewall"
rssh_sudo "rm /tmp/pastewall.tgz"
rssh_sudo "chown -R ${SERVICE_USER}:${SERVICE_USER} /opt/pastewall"
# 预建 data 目录:全新安装时 systemd 的 ReadWritePaths 需要该路径已存在,否则 NAMESPACE 报错
rssh_sudo "mkdir -p /opt/pastewall/data"
rssh_sudo "chown ${SERVICE_USER}:${SERVICE_USER} /opt/pastewall/data"
echo "  代码已部署(含构建产物 dist/,排除 data/ 与 node_modules,旧数据保留)"

step "5/6 写入并启用 systemd 服务"
UNIT=$(cat <<EOF
[Unit]
Description=PasteWall LAN shared clipboard
After=network.target

[Service]
Type=simple
User=${SERVICE_USER}
WorkingDirectory=/opt/pastewall
ExecStart=${NODE_BIN} server.js
Restart=always
RestartSec=3
Environment=NODE_ENV=production
Environment=PORT=${PORT}
NoNewPrivileges=yes
PrivateTmp=yes
ProtectSystem=full
$([ "$NODE_HOME" = 1 ] && echo "# ProtectHome 已禁用:nvm Node 位于用户 home 目录" || echo "ProtectHome=yes")
ReadWritePaths=/opt/pastewall/data

[Install]
WantedBy=multi-user.target
EOF
)
printf '%s\n' "$UNIT" | rssh "cat > /tmp/pastewall.service"
rssh_sudo "install -o root -g root -m 644 /tmp/pastewall.service /etc/systemd/system/pastewall.service"
rssh_sudo "rm /tmp/pastewall.service"

step "6/6 启动并验证"
rssh_sudo "systemctl daemon-reload"
rssh_sudo "systemctl enable pastewall >/dev/null 2>&1"
rssh_sudo "systemctl restart pastewall"
sleep 2
rssh "systemctl is-active pastewall" | grep -q active \
  || die "服务未激活。查看日志: ssh ${DEST} 'journalctl -u pastewall -n 30'"
rssh_sudo "ufw allow ${PORT}/tcp >/dev/null 2>&1" || warn "ufw 未启用或不可用,已跳过放行"
echo
BODY="$(curl -sS --max-time 5 "http://${SSH_HOST}:${PORT}/api/items")" \
  || die "远程 API 未响应,检查: ssh ${DEST} 'journalctl -u pastewall -n 30'"
echo "  远程 API 响应: ${BODY}"
step "部署完成: http://${SSH_HOST}:${PORT}"
