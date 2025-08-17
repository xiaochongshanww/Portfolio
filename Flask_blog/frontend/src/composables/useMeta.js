// 运行时动态 Meta/OG 注入工具
// setMeta 在数据加载后调用即可
const ensureTag = (selector, create) => {
  let el = document.head.querySelector(selector);
  if(!el){
    el = create();
    document.head.appendChild(el);
  }
  return el;
};

export function setMeta({
  title,
  description,
  image,
  url = window.location.href,
  type = 'article',
  siteName = 'Flask Blog',
  prevUrl,
  nextUrl
}={}){
  try {
    if(title){
      document.title = siteName ? `${title} - ${siteName}` : title;
      ensureTag('meta[name="twitter:title"]', ()=>{ const m=document.createElement('meta'); m.name='twitter:title'; return m; }).setAttribute('content', title);
      ensureTag('meta[property="og:title"]', ()=>{ const m=document.createElement('meta'); m.setAttribute('property','og:title'); return m; }).setAttribute('content', title);
    }
    if(description){
      ensureTag('meta[name="description"]', ()=>{ const m=document.createElement('meta'); m.name='description'; return m; }).setAttribute('content', description);
      ensureTag('meta[property="og:description"]', ()=>{ const m=document.createElement('meta'); m.setAttribute('property','og:description'); return m; }).setAttribute('content', description);
      ensureTag('meta[name="twitter:description"]', ()=>{ const m=document.createElement('meta'); m.name='twitter:description'; return m; }).setAttribute('content', description);
    }
    if(image){
      ensureTag('meta[property="og:image"]', ()=>{ const m=document.createElement('meta'); m.setAttribute('property','og:image'); return m; }).setAttribute('content', image);
      ensureTag('meta[name="twitter:image"]', ()=>{ const m=document.createElement('meta'); m.name='twitter:image'; return m; }).setAttribute('content', image);
      ensureTag('meta[name="twitter:card"]', ()=>{ const m=document.createElement('meta'); m.name='twitter:card'; return m; }).setAttribute('content', 'summary_large_image');
    }
    ensureTag('meta[property="og:type"]', ()=>{ const m=document.createElement('meta'); m.setAttribute('property','og:type'); return m; }).setAttribute('content', type);
    ensureTag('meta[property="og:url"]', ()=>{ const m=document.createElement('meta'); m.setAttribute('property','og:url'); return m; }).setAttribute('content', url);
    ensureTag('meta[property="og:site_name"]', ()=>{ const m=document.createElement('meta'); m.setAttribute('property','og:site_name'); return m; }).setAttribute('content', siteName);
    // canonical
    let link = document.head.querySelector('link[rel="canonical"]');
    if(!link){ link = document.createElement('link'); link.rel='canonical'; document.head.appendChild(link); }
    link.href = url.split('#')[0];
    // rel prev/next
    const setRel = (rel, href)=>{
      let l = document.head.querySelector(`link[rel="${rel}"]`);
      if(!href){ if(l) l.remove(); return; }
      if(!l){ l=document.createElement('link'); l.rel=rel; document.head.appendChild(l); }
      l.href = href;
    };
    setRel('prev', prevUrl);
    setRel('next', nextUrl);
  } catch(e){ /* ignore */ }
}

export function injectJsonLd(obj){
  try {
    let script = document.head.querySelector('script[data-jsonld="dynamic"]');
    if(!script){ script = document.createElement('script'); script.type='application/ld+json'; script.dataset.jsonld='dynamic'; document.head.appendChild(script); }
    script.textContent = JSON.stringify(obj);
  }catch(e){ /* ignore */ }
}

export function resetMeta(){
  setMeta({ title: '首页', description: '现代化内容平台', type: 'website' });
}
