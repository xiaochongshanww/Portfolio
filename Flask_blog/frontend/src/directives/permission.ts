import type { Directive } from 'vue';
// NodeNext 下需要显式 .js 扩展；统一从 barrel 引入，避免直接指向生成文件
import { ROLE_MATRIX } from '../governance/index.js';
import { useSessionStore } from '../stores/session.js';

function check(role: string, value: string | string[]): boolean {
  const list = Array.isArray(value) ? value : [value];
  return list.some(perm => (ROLE_MATRIX[perm]||[]).includes(role));
}

export const permission: Directive = {
  // beforeMount for testability & SSR safety
  beforeMount(el, binding){
    const required = binding.value; // string | string[]
    const role = useSessionStore().role;
    if(!check(role, required)){
      el.style.display = 'none';
    }
  },
  updated(el, binding){
    const required = binding.value;
    const role = useSessionStore().role;
    if(!check(role, required)){
      el.style.display = 'none';
    } else {
      el.style.display = '';
    }
  }
};

export default permission;
