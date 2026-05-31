import { describe, it, expect, vi } from 'vitest';
import { permission } from '../src/directives/permission';
import { setActivePinia, createPinia } from 'pinia';
import { useUserStore } from '../src/stores/user.js';

// Mock ROLE_MATRIX via jest-like manual override (the directive imports from governance/index.js)
vi.mock('../src/governance/index.js', ()=>({
  ROLE_MATRIX: { 'articles:create': ['author','editor'] }
}));

describe('permission directive', ()=>{
  setActivePinia(createPinia());
  const user = useUserStore();
  user.setAuth('t','author');

  it('allows element for permitted role', ()=>{
    const el:any = document.createElement('div');
  (permission as any).beforeMount(el, { value: 'articles:create' });
    expect(el.style.display).not.toBe('none');
  });

  it('hides element for not permitted role', ()=>{
    user.setAuth('t','guest');
    const el:any = document.createElement('div');
  (permission as any).beforeMount(el, { value: 'articles:create' });
    expect(el.style.display).toBe('none');
  });
});
