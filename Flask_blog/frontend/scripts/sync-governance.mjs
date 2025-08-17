import fs from 'fs';
import path from 'path';

// 读取 openapi.json 的 x-error-codes / x-role-matrix / x-workflow-transitions 生成前端常量
const specPath = path.resolve('openapi.json');
if(!fs.existsSync(specPath)){
  console.error('[governance:sync] spec not found:', specPath);
  process.exit(1);
}
const spec = JSON.parse(fs.readFileSync(specPath,'utf-8'));

const outDir = path.resolve('src/governance');
fs.mkdirSync(outDir, { recursive: true });

function writeIfChanged(file, content){
  if(fs.existsSync(file) && fs.readFileSync(file,'utf-8') === content) return;
  fs.writeFileSync(file, content, 'utf-8');
  console.log('[governance:sync] wrote', path.relative(process.cwd(), file));
}

// Error codes -> map
if(Array.isArray(spec['x-error-codes'])){
  const lines = spec['x-error-codes'].map(ec => `  [${ec.code}, ${JSON.stringify(ec.message)}], // ${ec.description || ''}`);
  writeIfChanged(path.join(outDir,'errorCodes.generated.ts'), `export const ERROR_CODE_MAP = new Map<number, string>([\n${lines.join('\n')}\n]);\n`);
}

// Role matrix -> object of arrays
if(spec['x-role-matrix']){
  const entries = Object.entries(spec['x-role-matrix']).map(([k,v]) => `  ${JSON.stringify(k)}: ${JSON.stringify(v)},`);
  writeIfChanged(path.join(outDir,'roleMatrix.generated.ts'), `export const ROLE_MATRIX: Record<string,string[]> = {\n${entries.join('\n')}\n};\n`);
}

// Workflow transitions -> object
if(spec['x-workflow-transitions']){
  const entries = Object.entries(spec['x-workflow-transitions']).map(([k,v]) => `  ${JSON.stringify(k)}: ${JSON.stringify(v)},`);
  writeIfChanged(path.join(outDir,'workflowTransitions.generated.ts'), `export const WORKFLOW_TRANSITIONS: Record<string,string[]> = {\n${entries.join('\n')}\n};\n`);
}

console.log('[governance:sync] done');
