# PasteWall · 局域网共享剪贴板

家庭局域网内共享文字与图片的便签板。任何设备把文字或图片"贴"上去,其他设备打开同一网址即可复制/下载。后端零第三方依赖,前端 Vue3 工程化构建。

## 功能

- **文字共享**:向输入框**粘贴文字自动发布**,输入文字则按 Ctrl+Enter 发布;其他设备一键复制(存储与显示字节级保留,含首尾空格与换行)。
- **图片共享**:三种提交方式——`Ctrl+V` 粘贴截图、拖拽图片、点击选择文件。缩略图列表 + 点击查看大图 + 复制图片 / 下载。
- **当前剪贴板区**:顶部展示最近一条文字与最近一张图片(**各自取最新**,互不影响)。
- **多设备一致**:每 5 秒自动轮询 + 手动刷新 + 窗口聚焦/回到前台即刷新。
- **支持删除**任意记录(二次确认弹层)。
- **手机友好**:响应式布局,触控目标 ≥44px;文字一键复制、图片长按保存。
- **数据持久化**:文字与图片保存在服务器 `data/` 目录,重启不丢。

## 技术栈

| 层 | 选型 |
|---|---|
| 后端 | Node.js(≥22),仅内置 `http`/`fs`/`path`/`crypto`,无框架、无第三方依赖 |
| 前端 | Vue 3 + TypeScript + Vite |
| UI | Element Plus(交互组件:Message / Popconfirm / Empty)+ shadcn-vue(基础原子:Button / Card / Badge / Textarea)+ Tailwind CSS v4(布局与主题) |
| 存储 | 纯文件:`data/items.json`(索引)+ `data/images/`(图片文件),原子写(临时文件 + rename) |

## 目录结构

```
PasteWall/
├── server.js            # 后端:API + 静态托管 frontend/dist
├── lib/store.js         # 数据层
├── frontend/            # Vue3 工程
│   ├── src/api.ts       # REST API 封装
│   ├── src/composables/ # usePolling / useClipboard / useLightbox
│   ├── src/components/  # CurrentClipboard / Composer / HistoryList / Lightbox
│   └── src/components/ui/  # shadcn-vue 基础组件
├── deploy/              # systemd 单元 + 一键部署脚本
└── data/                # 运行时数据(gitignore)
```

## 本地开发

```bash
# 后端(任意终端)
node server.js                    # 默认 3002

# 前端(Vite 开发服务器,代理 /api 到后端)
cd frontend
npm install
VITE_API_TARGET=http://localhost:3201 npm run dev   # 后端在其他端口时设置代理目标
```

生产式本地运行:构建后由后端托管。

```bash
cd frontend && npm run build     # 产出 frontend/dist
node server.js                   # 打开 http://localhost:3002
```

> Windows 注意:若端口落在系统排除范围(`netsh interface ipv4 show excludedportrange protocol=tcp`),绑定报 `EACCES`,换一个端口即可。部署到 Linux 服务器不受影响。

## API

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/items` | 全部记录(最新在前)+ `serverTime` |
| POST | `/api/items` | `{"type":"text","text":"…"}` 或 `{"type":"image","mimeType":"image/png","dataBase64":"…"}` |
| DELETE | `/api/items/:id` | 删除一条记录(连带删除图片文件) |
| GET | `/images/:file` | 图片文件 |

请求体上限 64MB(`PASTEWALL_MAX_BODY_MB` 可调)。

## 部署到局域网服务器

前置条件:

- 服务器已安装 Node.js v22+ 与 systemd。
- 本机(Git Bash)可 `ssh` 到服务器,并有 `npm`(用于本地构建)。
- 服务器登录用户已配置**免密 sudo**(`visudo` 添加 `<用户> ALL=(ALL) NOPASSWD: ALL`);若未配置,请用下方手动步骤。

一键部署(脚本会自动**本地构建前端**后连同 `dist` 上传):

```bash
cd PasteWall
bash deploy/deploy.sh
# 可选:SSH_USER=xxx SSH_HOST=<服务器IP> PORT=3002 bash deploy/deploy.sh
```

脚本会:本地 `npm ci && npm run build` → 检测远端 Node → 创建服务用户(或适配 nvm)→ 同步到 `/opt/pastewall`(保留 `data/`)→ 安装启用 systemd → 放行端口 → 验证 API。

部署完成,局域网内访问 `http://<服务器IP>:3002`。

### Node 位置说明

- **系统级 Node**(如 `/usr/bin/node`):安全加固运行——专用用户 `pastewall`、`ProtectSystem=full`、`ProtectHome=yes`,仅数据目录可写。
- **nvm 用户目录 Node**(`/home/<user>/.nvm/…`):自动改用现有用户运行并放宽 `ProtectHome`,保证服务可读 Node 二进制。若想用完整加固,建议服务器 `apt install nodejs` 后重跑。

### 手动部署(脚本异常时的替代)

```bash
cd PasteWall
cd frontend && npm ci && npm run build && cd ..
zip -r pastewall.zip . -x data -x .git -x frontend/node_modules
scp pastewall.zip <用户>@<服务器IP>:/tmp/
ssh <用户>@<服务器IP>
sudo mkdir -p /opt/pastewall && sudo unzip /tmp/pastewall.zip -d /opt/pastewall
sudo chown -R pastewall:pastewall /opt/pastewall   # 或你的用户
sudo cp /opt/pastewall/deploy/pastewall.service /etc/systemd/system/
# 若 Node 在 nvm 用户目录,编辑 unit:ExecStart 改为真实 node 路径,删除 ProtectHome=yes
sudo systemctl daemon-reload
sudo systemctl enable --now pastewall
sudo ufw allow 3002/tcp
curl http://127.0.0.1:3002/api/items
```

### 运维

```bash
ssh <用户>@<服务器IP>
systemctl status pastewall          # 状态
journalctl -u pastewall -f          # 实时日志
sudo systemctl restart pastewall    # 重启
sudo reboot                         # 重启后服务自动拉起
```

## 使用说明

1. Windows 复制一段文字 → 打开 `http://<服务器IP>:3002` → 粘贴到输入框(**自动发布**);或输入后按 Ctrl+Enter 发布。到 Mac 打开同一网址 → 点"复制"。
2. Windows 截图(如 Win+Shift+S)→ 直接 `Ctrl+V` 到页面 → 自动上传。到 Mac 打开页面 → 点缩略图看大图 → 下载或长按保存。
3. 手机上打开网址:查看/复制文字,长按图片保存。
4. 当前剪贴板区始终显示最近文字与最近图片;历史列表可回溯任意记录,误贴内容可删除(二次确认)。

## 安全边界

- 仅限信任的家庭局域网使用,无登录/鉴权。
- 数据不加密、不设过期清理(需求明确不做)。
- 图片文件名由服务器生成并做路径穿越防护;文字渲染仅用插值(`textContent`),防 XSS。
- 建议只在可信内网部署,不要暴露到公网。

## 验收对照(需求文档第 8 节)

| 验收项 | 状态 |
|---|---|
| Windows 贴文字 → Mac 一键复制 | ✅(已验证,存储/显示字节级一致;剪贴板按系统规范转 CRLF) |
| Windows 截图 Ctrl+V → Mac 看缩略图/放大/下载/复制 | ✅(粘贴/拖拽/文件选择三通道均验证) |
| 多设备同时打开内容一致 | ✅(5 秒内同步,双标签页验证一致) |
| 重启服务历史仍在 | ✅(崩溃安全:快速写入中途强杀后数据完好) |
| 手机浏览器可查看/复制/保存 | ✅(响应式,触控目标 ≥44px) |
| 开机自启常驻 | ✅(systemd,重启后自动拉起) |
