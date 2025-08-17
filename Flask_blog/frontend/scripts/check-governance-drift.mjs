import fs from 'fs';
import path from 'path';
const spec = JSON.parse(fs.readFileSync(path.resolve('openapi.json'),'utf-8'));
let exitCode = 0;

function readIfExists(p){ return fs.existsSync(p) ? fs.readFileSync(p,'utf-8') : null; }

// Error codes
{
  const errGen = path.resolve('src/governance/errorCodes.generated.ts');
  const content = readIfExists(errGen);
  if(content){
    const codesInGen = [...content.matchAll(/\[(\d+),/g)].map(m=>Number(m[1]));
    const codesInSpec = (spec['x-error-codes']||[]).map(e=>e.code).sort();
    const missing = codesInSpec.filter(c=>!codesInGen.includes(c));
    const extra = codesInGen.filter(c=>!codesInSpec.includes(c));
    if(missing.length || extra.length){
      console.warn('[governance:check] error codes drift: missing', missing, 'extra', extra); exitCode=1;
    } else { console.log('[governance:check] error codes OK'); }
  } else { console.warn('[governance:check] generated error codes file missing'); exitCode=1; }
}

// Role matrix
{
  const file = path.resolve('src/governance/roleMatrix.generated.ts');
  const content = readIfExists(file);
  if(content){
    const entriesGen = [...content.matchAll(/"([^"]+)": \[([^\]]*)\]/g)].map(m=>[m[1], m[2].split(',').map(s=>s.trim().replace(/['" ]/g,'')).filter(Boolean)]);
    const objGen = Object.fromEntries(entriesGen);
    const objSpec = spec['x-role-matrix'] || {};
    const keys = new Set([...Object.keys(objGen), ...Object.keys(objSpec)]);
    for(const k of keys){
      const a = (objGen[k]||[]).slice().sort();
      const b = (objSpec[k]||[]).slice().sort();
      if(a.join(',')!==b.join(',')){
        console.warn('[governance:check] role matrix drift at', k, 'gen=', a, 'spec=', b); exitCode=1;
      }
    }
    if(exitCode===0) console.log('[governance:check] role matrix OK');
  } else { console.warn('[governance:check] role matrix file missing'); exitCode=1; }
}

// Workflow transitions
{
  const file = path.resolve('src/governance/workflowTransitions.generated.ts');
  const content = readIfExists(file);
  if(content){
    const entriesGen = [...content.matchAll(/"([^"]+)": \[([^\]]*)\]/g)].map(m=>[m[1], m[2].split(',').map(s=>s.trim().replace(/['" ]/g,'')).filter(Boolean)]);
    const objGen = Object.fromEntries(entriesGen);
    const objSpec = spec['x-workflow-transitions'] || {};
    const keys = new Set([...Object.keys(objGen), ...Object.keys(objSpec)]);
    for(const k of keys){
      const a = (objGen[k]||[]).slice().sort();
      const b = (objSpec[k]||[]).slice().sort();
      if(a.join(',')!==b.join(',')){
        console.warn('[governance:check] workflow transitions drift at', k, 'gen=', a, 'spec=', b); exitCode=1;
      }
    }
    if(exitCode===0) console.log('[governance:check] workflow transitions OK');
  } else { console.warn('[governance:check] workflow transitions file missing'); exitCode=1; }
}

process.exit(exitCode);
