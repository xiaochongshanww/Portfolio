import fs from 'fs';

const SPEC_PATH = 'openapi.json';
const OUT_PATH = 'src/errorCodes.js';

function gen(){
  const spec = JSON.parse(fs.readFileSync(SPEC_PATH,'utf-8'));
  const list = spec['x-error-codes'] || [];
  const lines = [];
  lines.push('// 自动生成: 请勿手工编辑');
  lines.push('export const ERROR_CODE_MAP = new Map([');
  for(const item of list){
    const msg = (item.description || item.message || '').replace(/'/g, "\\'");
    lines.push(`  [${item.code}, '${msg || item.message}'],`);
  }
  lines.push(']);');
  lines.push('\nexport function translateError(code, fallback){');
  lines.push("  return ERROR_CODE_MAP.get(code) || fallback || '操作失败';");
  lines.push('}');
  fs.writeFileSync(OUT_PATH, lines.join('\n'));
  console.log('Generated', OUT_PATH, 'with', list.length, 'error codes');
}

try { gen(); } catch(e){
  console.error('Failed to generate error codes:', e.message);
  process.exit(1);
}
