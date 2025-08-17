import { onCLS, onINP, onLCP, onFCP, onTTFB } from 'web-vitals';

interface MetricPayload {
  name: string;
  value: number;
  id: string;
  url: string;
  ts: number;
}

const queue: MetricPayload[] = [];
let flushTimer: any = null;

function push(metric:{name:string; value:number; id:string}){
  queue.push({ name: metric.name, value: metric.value, id: metric.id, url: location.pathname, ts: Date.now() });
  if(!flushTimer) flushTimer = setTimeout(flush, 5000);
}

async function flush(){
  const batch = queue.splice(0, queue.length);
  flushTimer = null;
  if(!batch.length) return;
  try {
    await fetch('/api/v1/rum/metrics', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({ metrics: batch }) });
  } catch{}
}

export function initRUM(){
  if((window as any).__RUM_INIT) return; (window as any).__RUM_INIT = true;
  onCLS(push); onINP(push); onLCP(push); onFCP(push); onTTFB(push);
  window.addEventListener('beforeunload', ()=>{ if(queue.length) navigator.sendBeacon && navigator.sendBeacon('/api/v1/rum/metrics', JSON.stringify({ metrics: queue })); });
}

if(typeof window !== 'undefined'){
  if(document.readyState === 'complete') initRUM(); else window.addEventListener('load', ()=> setTimeout(initRUM, 0));
}
