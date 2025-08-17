import { reactive } from 'vue';

const state = reactive<{ queue: { id:number; text:string; type:'info'|'error'|'success'; ts:number }[] }>({ queue: [] });
let id = 1;
function push(text:string, type:'info'|'error'|'success'='info', ttl=3000){
  const item = { id: id++, text, type, ts: Date.now() };
  state.queue.push(item);
  setTimeout(()=>{
    const idx = state.queue.indexOf(item);
    if(idx>=0) state.queue.splice(idx,1);
  }, ttl);
}
export function useNotify(){
  return { queue: state.queue, pushInfo:(t:string)=>push(t,'info'), pushError:(t:string)=>push(t,'error'), pushSuccess:(t:string)=>push(t,'success') };
}
