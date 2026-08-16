'use strict';

const http = require('http');
const fs = require('fs');
const path = require('path');
const store = require('./lib/store');

const PORT = Number(process.env.PORT || 3002);
const MAX_BODY_BYTES = (Number(process.env.PASTEWALL_MAX_BODY_MB) || 64) * 1024 * 1024;
const PUBLIC_DIR = path.join(__dirname, 'frontend', 'dist');

const MIME = {
  '.html': 'text/html; charset=utf-8',
  '.css': 'text/css; charset=utf-8',
  '.js': 'text/javascript; charset=utf-8',
  '.svg': 'image/svg+xml',
  '.ico': 'image/x-icon',
  '.png': 'image/png',
  '.jpg': 'image/jpeg',
  '.gif': 'image/gif',
  '.webp': 'image/webp',
};

function sendJSON(res, status, payload) {
  const body = JSON.stringify(payload);
  res.writeHead(status, {
    'Content-Type': 'application/json; charset=utf-8',
    'Content-Length': Buffer.byteLength(body),
    'Cache-Control': 'no-store',
    'X-Content-Type-Options': 'nosniff',
  });
  res.end(body);
}

function sendError(res, status, message) {
  sendJSON(res, status, { error: message });
}

// 读取 JSON 请求体,带 64MB 上限(前置 Content-Length + 流式累计双保险)
function readJSONBody(req) {
  return new Promise((resolve, reject) => {
    const declared = Number(req.headers['content-length']);
    if (Number.isFinite(declared) && declared > MAX_BODY_BYTES) {
      const err = new Error('请求体过大');
      err.status = 413;
      reject(err);
      return;
    }
    const chunks = [];
    let total = 0;
    req.on('data', chunk => {
      total += chunk.length;
      if (total > MAX_BODY_BYTES) {
        const err = new Error('请求体过大');
        err.status = 413;
        reject(err);
        req.destroy();
        return;
      }
      chunks.push(chunk);
    });
    req.on('end', () => {
      try {
        resolve(JSON.parse(Buffer.concat(chunks).toString('utf8')));
      } catch (err) {
        const e = new Error('无效的 JSON');
        e.status = 400;
        reject(e);
      }
    });
    req.on('error', reject);
  });
}

async function handleAPI(req, res, url) {
  const pathname = url.pathname;

  if (req.method === 'GET' && pathname === '/api/items') {
    sendJSON(res, 200, { items: store.list(), serverTime: Date.now() });
    return;
  }

  if (req.method === 'POST' && pathname === '/api/items') {
    let body;
    try {
      body = await readJSONBody(req);
    } catch (err) {
      sendError(res, err.status || 400, err.message);
      return;
    }
    try {
      let item;
      if (body.type === 'text') {
        item = store.addText(body.text);
      } else if (body.type === 'image') {
        item = store.addImage(body.mimeType, body.dataBase64);
      } else {
        sendError(res, 400, 'type 必须是 text 或 image');
        return;
      }
      sendJSON(res, 201, { item });
    } catch (err) {
      sendError(res, err.status || 500, err.message);
    }
    return;
  }

  const delMatch = pathname.match(/^\/api\/items\/([^/]+)$/);
  if (req.method === 'DELETE' && delMatch) {
    const id = decodeURIComponent(delMatch[1]);
    try {
      store.remove(id);
      sendJSON(res, 200, { ok: true });
    } catch (err) {
      sendError(res, err.status || 500, err.message);
    }
    return;
  }

  sendError(res, 405, '方法不允许');
}

function handleImage(req, res, url) {
  const m = url.pathname.match(/^\/images\/([^/]+)$/);
  if (!m) {
    sendError(res, 404, 'not found');
    return;
  }
  const filename = decodeURIComponent(m[1]);
  // path 穿越防护:白名单 + resolve 后必须仍在 images/ 内
  if (!/^[A-Za-z0-9._-]+$/.test(filename)) {
    sendError(res, 400, '非法的文件名');
    return;
  }
  const filePath = path.resolve(store.IMAGES_DIR, filename);
  if (!filePath.startsWith(store.IMAGES_DIR + path.sep) || !fs.existsSync(filePath) || !fs.statSync(filePath).isFile()) {
    sendError(res, 404, 'not found');
    return;
  }
  const ext = path.extname(filePath).toLowerCase();
  res.writeHead(200, {
    'Content-Type': store.extToMime(ext.slice(1)) || 'application/octet-stream',
    'Content-Length': fs.statSync(filePath).size,
    'Cache-Control': 'public, max-age=86400',
    'X-Content-Type-Options': 'nosniff',
  });
  fs.createReadStream(filePath).pipe(res);
}

function handleStatic(req, res, url) {
  let rel = url.pathname === '/' ? '/index.html' : url.pathname;
  const filePath = path.resolve(PUBLIC_DIR, rel.slice(1));
  if (!filePath.startsWith(PUBLIC_DIR + path.sep) || !fs.existsSync(filePath) || !fs.statSync(filePath).isFile()) {
    sendError(res, 404, 'not found');
    return;
  }
  const ext = path.extname(filePath).toLowerCase();
  res.writeHead(200, {
    'Content-Type': MIME[ext] || 'application/octet-stream',
    'Content-Length': fs.statSync(filePath).size,
    'Cache-Control': 'no-store',
  });
  fs.createReadStream(filePath).pipe(res);
}

const server = http.createServer((req, res) => {
  const url = new URL(req.url, `http://${req.headers.host || 'localhost'}`);
  try {
    if (url.pathname.startsWith('/api/')) {
      handleAPI(req, res, url);
    } else if (url.pathname.startsWith('/images/')) {
      handleImage(req, res, url);
    } else {
      if (req.method !== 'GET' && req.method !== 'HEAD') {
        sendError(res, 405, '方法不允许');
        return;
      }
      handleStatic(req, res, url);
    }
  } catch (err) {
    console.error(`[server] ${new Date().toISOString()} 未捕获异常: ${err.stack}`);
    if (!res.headersSent) sendError(res, 500, '服务器内部错误');
    else res.destroy();
  }
});

store.init()
  .then(() => {
    server.on('error', err => {
      if (err.code === 'EADDRINUSE') {
        console.error(`[server] 端口 ${PORT} 已被占用,请改用其它端口(如 PASTEWALL_PORT 或 PORT 环境变量)`);
      } else {
        console.error(`[server] 启动失败: ${err.message}`);
      }
      process.exit(1);
    });
    server.listen(PORT, () => {
      console.log(`[server] PasteWall 已启动: http://0.0.0.0:${PORT}`);
      if (!fs.existsSync(path.join(PUBLIC_DIR, 'index.html'))) {
        console.warn(`[server] 警告: 前端未构建(${PUBLIC_DIR} 缺 index.html),请先运行: cd frontend && npm install && npm run build`);
      }
    });
  })
  .catch(err => {
    console.error(`[server] 初始化失败: ${err.message}`);
    process.exit(1);
  });

function shutdown() {
  console.log(`[server] 收到退出信号,正在关闭...`);
  server.close(() => {
    console.log('[server] 已关闭');
    process.exit(0);
  });
  // 保存队列极小且为同步写,给足时间落盘
  setTimeout(() => process.exit(0), 2000).unref();
}
process.on('SIGTERM', shutdown);
process.on('SIGINT', shutdown);
