import { ref, watch, type Ref } from 'vue';
import { useRoute, useRouter } from 'vue-router';

export interface PagedQueryOptions<T> {
  fetcher: (params: { page: number; page_size: number; [k:string]: any }) => Promise<T>;
  initialPageSize?: number;
  extraParams?: () => Record<string, any>;
}

export function usePagedQuery<TData>(opts: PagedQueryOptions<TData>) {
  const route = useRoute();
  const router = useRouter();
  const loading = ref(false);
  const error = ref<string>('');
  const data = ref<TData | null>(null);
  const pageSize = ref(Number(route.query.page_size) || opts.initialPageSize || 20);

  async function load() {
    loading.value = true; error.value='';
    try {
      const page = Number(route.query.page) || 1;
      const base: any = { page, page_size: pageSize.value };
      const extra = opts.extraParams ? opts.extraParams() : {};
      data.value = await opts.fetcher({ ...base, ...extra });
    } catch(e:any){
      error.value = e?.message || '加载失败';
    } finally { loading.value=false; }
  }

  function buildQuery(newQuery: any){
    const q: any = { ...route.query, ...newQuery };
    Object.keys(q).forEach(k=>{ if(q[k]===''||q[k]==null) delete q[k]; });
    return q;
  }
  function goPage(p:number){ if(p<1) return; router.push({ query: buildQuery({ page: p })}); }
  function setPageSize(ps:number){ router.push({ query: buildQuery({ page_size: ps, page: 1 })}); }

  watch(()=>route.query, ()=>{
    if(route.query.page_size && Number(route.query.page_size)!==pageSize.value){
      pageSize.value = Number(route.query.page_size);
    }
    load();
  }, { immediate: true });

  return { loading, error, data, pageSize, load, goPage, setPageSize };
}
