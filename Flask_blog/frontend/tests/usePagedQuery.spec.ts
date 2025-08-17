import { describe, it, expect, vi } from 'vitest';
import { usePagedQuery } from '../src/composables/usePagedQuery';
import { nextTick } from 'vue';

// Mock vue-router composables
vi.mock('vue-router', ()=>({
  useRoute: () => ({ query: {} }),
  useRouter: () => ({ push: (_:any)=>{} })
}));

function mountComposable(cb: any){ return cb(); }

describe('usePagedQuery', ()=>{
  it('loads data via fetcher', async ()=>{
    const calls: any[] = [];
    const { data, loading } = mountComposable(()=> usePagedQuery<{ list:number[] }>({
      async fetcher(){ calls.push(1); return { list:[1,2,3] } as any; }
    }));
    await nextTick();
    expect(data.value?.list).toEqual([1,2,3]);
    expect(calls.length).toBe(1);
    expect(loading.value).toBe(false);
  });
});
