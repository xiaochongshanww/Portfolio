import MarkdownIt from 'markdown-it';
import Turndown from 'turndown';

const md = new MarkdownIt({ html: true, linkify: true, breaks: false });

// 短代码与视频支持
const VIDEO_HOSTS = ['youtu.be','www.youtube.com','youtube.com','vimeo.com','www.vimeo.com','player.vimeo.com','player.bilibili.com','www.bilibili.com','bilibili.com'];

function buildVideoIframe(url){
  try { const u = new URL(url); if(!VIDEO_HOSTS.includes(u.hostname)) return ''; }
  catch { return ''; }
  const host = new URL(url).hostname;
  let embed = '';
  if(host==='youtu.be'){ const id = url.split('/').pop(); embed = `https://www.youtube.com/embed/${id}`; }
  else if(host.endsWith('youtube.com')){ const u = new URL(url); const id = u.searchParams.get('v'); if(id) embed = `https://www.youtube.com/embed/${id}`; }
  else if(host.includes('bilibili')){ const m = url.match(/(BV[0-9A-Za-z]+)/); if(m) embed = `https://player.bilibili.com/player.html?bvid=${m[1]}&page=1`; }
  else if(host.includes('vimeo')){ const m = url.match(/(\d+)/); if(m) embed = `https://player.vimeo.com/video/${m[1]}`; }
  if(!embed) return '';
  return `<div class="video-embed"><iframe src="${embed}" loading="lazy" allowfullscreen frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" referrerpolicy="no-referrer-when-downgrade"></iframe></div>`;
}

const SHORTCODE_RE = /^:::(video|gist)\s+(\S+)\s*:::$/;
function preprocessShortcodes(raw){
  return raw.split(/\r?\n/).map(line=>{
    const m = line.trim().match(SHORTCODE_RE);
    if(!m) return line;
    const kind = m[1]; const url = m[2];
    if(kind==='video'){ const html = buildVideoIframe(url); return html || line; }
    if(kind==='gist'){ return `<div class="embed-gist" data-gist="${url}"></div>`; }
    return line;
  }).join('\n');
}

const turndown = new Turndown({ headingStyle: 'atx', codeBlockStyle: 'fenced' });
// 保留视频与 gist 节点（以 HTML 形式 round-trip）
['div','iframe'].forEach(tag=>turndown.keep([tag]));

turndown.addRule('preserveVideoEmbed', {
  filter: node => node.nodeName==='DIV' && node.classList?.contains('video-embed'),
  replacement: (content, node) => `\n${node.outerHTML}\n`
});

turndown.addRule('preserveGistEmbed', {
  filter: node => node.nodeName==='DIV' && node.classList?.contains('embed-gist'),
  replacement: (content, node) => `\n${node.outerHTML}\n`
});

export function mdToHtml(markdown){ if(!markdown) return ''; return md.render(preprocessShortcodes(markdown)); }
export function htmlToMd(html){ if(!html) return ''; return turndown.turndown(html); }
export function roundTrip(markdown){ return htmlToMd(mdToHtml(markdown)); }

export default { mdToHtml, htmlToMd, roundTrip };
