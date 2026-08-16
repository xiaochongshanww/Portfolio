'use strict';

const fs = require('fs');
const path = require('path');
const crypto = require('crypto');

const DATA_DIR = path.join(__dirname, '..', 'data');
const IMAGES_DIR = path.join(DATA_DIR, 'images');
const INDEX_FILE = path.join(DATA_DIR, 'items.json');
const VERSION = 1;

const ALLOWED_IMAGE_TYPES = {
  'image/png': { ext: 'png', magic: buf => buf.length >= 8 && buf.readUInt32BE(0) === 0x89504e47 && buf.readUInt32BE(4) === 0x0d0a1a0a },
  'image/jpeg': { ext: 'jpg', magic: buf => buf.length >= 3 && buf[0] === 0xff && buf[1] === 0xd8 && buf[2] === 0xff },
  'image/gif': { ext: 'gif', magic: buf => buf.length >= 4 && buf.toString('ascii', 0, 4) === 'GIF8' },
  'image/webp': { ext: 'webp', magic: buf => buf.length >= 12 && buf.toString('ascii', 0, 4) === 'RIFF' && buf.toString('ascii', 8, 12) === 'WEBP' },
};

let items = [];
let _chain = Promise.resolve();

function log(msg) {
  console.log(`[store] ${new Date().toISOString()} ${msg}`);
}

function logError(msg) {
  console.error(`[store] ${new Date().toISOString()} ${msg}`);
}

function generateId(prefix) {
  const rand = crypto.randomBytes(4).toString('hex');
  return `${prefix}_${Date.now().toString(36)}_${rand}`;
}

function _persist() {
  // 链保持可继续(下次保存仍执行),但返回的 Promise 向调用方拒绝,以便调用方清理孤儿
  const p = _chain
    .then(() => {
      const tmp = INDEX_FILE + '.tmp';
      fs.writeFileSync(tmp, JSON.stringify({ version: VERSION, items }));
      fs.renameSync(tmp, INDEX_FILE);
    })
    .catch(err => {
      logError(`保存 items.json 失败: ${err.message}`);
      throw err;
    });
  _chain = p.catch(() => {});
  return p;
}

async function init() {
  fs.mkdirSync(DATA_DIR, { recursive: true });
  fs.mkdirSync(IMAGES_DIR, { recursive: true });

  // 可写性探针:快速失败而非带病运行
  const probe = path.join(DATA_DIR, '.write-probe');
  try {
    fs.writeFileSync(probe, 'ok');
    fs.unlinkSync(probe);
  } catch (err) {
    throw new Error(`data 目录不可写(${DATA_DIR}): ${err.message}`);
  }

  if (!fs.existsSync(INDEX_FILE)) {
    fs.writeFileSync(INDEX_FILE, JSON.stringify({ version: VERSION, items: [] }));
    log('items.json 不存在,已创建空索引');
  } else {
    try {
      const parsed = JSON.parse(fs.readFileSync(INDEX_FILE, 'utf8'));
      items = Array.isArray(parsed.items) ? parsed.items : [];
      log(`已加载 ${items.length} 条记录`);
    } catch (err) {
      const backup = `${INDEX_FILE}.corrupt-${Date.now()}`;
      try { fs.renameSync(INDEX_FILE, backup); } catch { /* ignore */ }
      items = [];
      logError(`items.json 损坏,已备份到 ${backup},以空列表启动`);
    }
  }

  // 孤儿图片回收:清理未被索引引用的文件
  const referenced = new Set(items.filter(i => i.imageFile).map(i => i.imageFile));
  let removed = 0;
  for (const f of fs.readdirSync(IMAGES_DIR)) {
    if (f === '.gitkeep') continue;
    if (!referenced.has(f)) {
      try {
        fs.unlinkSync(path.join(IMAGES_DIR, f));
        removed++;
      } catch { /* ignore */ }
    }
  }
  if (removed > 0) log(`已回收 ${removed} 个孤儿图片文件`);
}

function list() {
  return items;
}

function get(id) {
  return items.find(i => i.id === id) || null;
}

function addText(text) {
  if (typeof text !== 'string' || text.trim().length === 0) {
    const err = new Error('text 不能为空');
    err.status = 400;
    throw err;
  }
  let id = generateId('t');
  while (items.some(i => i.id === id)) id = generateId('t');

  const item = {
    id,
    type: 'text',
    text,
    imageFile: null,
    createdAt: Date.now(),
    size: Buffer.byteLength(text, 'utf8'),
  };
  items.unshift(item);
  _persist();
  return item;
}

function addImage(mimeType, dataBase64) {
  const spec = ALLOWED_IMAGE_TYPES[mimeType];
  if (!spec) {
    const err = new Error(`不支持的图片类型: ${mimeType}`);
    err.status = 400;
    throw err;
  }
  let buf;
  try {
    buf = Buffer.from(dataBase64, 'base64');
  } catch (err) {
    const e = new Error('base64 解码失败');
    e.status = 400;
    throw e;
  }
  if (buf.length === 0 || !spec.magic(buf)) {
    const err = new Error('图片内容与声明的类型不符');
    err.status = 400;
    throw err;
  }

  let id = generateId('im');
  while (items.some(i => i.id === id)) id = generateId('im');
  const imageFile = `${id}.${spec.ext}`;

  const item = {
    id,
    type: 'image',
    text: null,
    imageFile,
    createdAt: Date.now(),
    size: buf.length,
  };
  fs.writeFileSync(path.join(IMAGES_DIR, imageFile), buf);

  items.unshift(item);
  _persist().catch(() => {
    // 索引写失败则尽力删掉刚写入的图片,孤儿 GC 兜底
    try { fs.unlinkSync(path.join(IMAGES_DIR, imageFile)); } catch { /* ignore */ }
  });
  return item;
}

function remove(id) {
  const idx = items.findIndex(i => i.id === id);
  if (idx === -1) {
    const err = new Error('记录不存在');
    err.status = 404;
    throw err;
  }
  const [item] = items.splice(idx, 1);
  _persist();
  if (item.imageFile) {
    try { fs.unlinkSync(path.join(IMAGES_DIR, item.imageFile)); } catch (err) {
      if (err.code !== 'ENOENT') logError(`删除图片 ${item.imageFile} 失败: ${err.message}`);
    }
  }
  return item;
}

function extToMime(ext) {
  switch (ext) {
    case 'png': return 'image/png';
    case 'jpg':
    case 'jpeg': return 'image/jpeg';
    case 'gif': return 'image/gif';
    case 'webp': return 'image/webp';
    default: return 'application/octet-stream';
  }
}

module.exports = {
  init,
  list,
  get,
  addText,
  addImage,
  remove,
  extToMime,
  DATA_DIR,
  IMAGES_DIR,
};
