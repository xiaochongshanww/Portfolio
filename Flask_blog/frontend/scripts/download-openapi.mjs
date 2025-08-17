import fs from 'fs';
import http from 'http';
import https from 'https';
import { URL } from 'url';

// 默认改为后端当前可用的 /spec
const DEFAULT_URL = 'http://localhost:5000/spec';
const urlStr = process.env.OPENAPI_URL || DEFAULT_URL;
console.log('[download-openapi] URL =', urlStr);
const u = new URL(urlStr);

function download(url){
  return new Promise((resolve,reject)=>{
    const lib = url.startsWith('https:') ? https : http;
    lib.get(url, res => {
      if(res.statusCode!==200){ reject(new Error('HTTP '+res.statusCode)); return; }
      const chunks=[];
      res.on('data',c=>chunks.push(c));
      res.on('end',()=>resolve(Buffer.concat(chunks).toString('utf-8')));
    }).on('error',reject);
  });
}

async function withRetry(fn, times=3, delay=800){
  let last;
  for(let i=1;i<=times;i++){
    try { return await fn(); } catch(e){
      last = e;
      console.warn(`[download-openapi] attempt ${i} failed:`, e.message);
      if(i<times) await new Promise(r=>setTimeout(r, delay));
    }
  }
  throw last;
}

(async () => {
  console.log('[download-openapi] cwd =', process.cwd());
  try {
    const json = await withRetry(()=>download(urlStr), 3, 700);
    // 简单校验
    let parsed;
    try { parsed = JSON.parse(json); } catch(e){
      throw new Error('Invalid JSON received from spec endpoint');
    }
    if(!parsed.openapi){
      console.warn('[download-openapi] Warning: missing openapi field');
    }
    fs.writeFileSync('openapi.json', JSON.stringify(parsed,null,2));
    try { fs.copyFileSync('openapi.json','../openapi.json'); } catch(_){}
    console.log('Downloaded OpenAPI spec to openapi.json (and copied to parent)');
  } catch(e){
    console.error('Failed to download OpenAPI spec:', e && e.stack || e && e.message || e);
    let success = false;
    try {
      const candidates = ['../backend/openapi.json','../../backend/openapi.json'];
      for(const rel of candidates){
        const abs = new URL(rel, 'file://' + process.cwd().replace(/\\/g,'/') + '/').pathname.replace(/^\//,'');
        console.log('[download-openapi] probe fallback rel=', rel, 'abs=', abs);
        if (fs.existsSync(rel)) {
            const content = fs.readFileSync(rel, 'utf-8');
            console.log('[download-openapi] Using local fallback', rel);
            fs.writeFileSync('openapi.json', content);
            try { fs.copyFileSync('openapi.json','../openapi.json'); } catch(_){ }
            success = true; break;
        }
      }
      if(!success) console.warn('[download-openapi] no fallback candidate found');
    } catch(e2){
      console.warn('[download-openapi] fallback error', e2 && e2.message);
    }
    if(!success){
      if(fs.existsSync('../openapi.json')){
        console.warn('[download-openapi] using existing parent openapi.json as cached spec');
        try { fs.copyFileSync('../openapi.json','openapi.json'); success = true; } catch(_){ }
      }
    }
    process.exit(success ? 0 : 1);
  }
})();
