import { describe, it, expect, afterEach } from 'vitest';
import { setMeta, resetMeta, injectJsonLd } from '../src/composables/useMeta';

afterEach(() => {
  document.head.innerHTML = '';
});

describe('useMeta', () => {
  it('sets title, meta tags and canonical/prev/next', () => {
    setMeta({
      title: 'Hello',
      description: 'desc',
      image: 'img.png',
      url: 'https://x.com/a#frag',
      prevUrl: 'https://x.com/p',
      nextUrl: 'https://x.com/n',
    });
    expect(document.title).toBe('Hello - Flask Blog');
    expect(document.querySelector('meta[property="og:title"]')?.getAttribute('content')).toBe('Hello');
    expect(document.querySelector('meta[name="twitter:title"]')?.getAttribute('content')).toBe('Hello');
    expect(document.querySelector('meta[name="description"]')?.getAttribute('content')).toBe('desc');
    expect(document.querySelector('meta[property="og:image"]')?.getAttribute('content')).toBe('img.png');
    expect(document.querySelector('meta[name="twitter:card"]')?.getAttribute('content')).toBe('summary_large_image');
    expect(document.querySelector('meta[property="og:type"]')?.getAttribute('content')).toBe('article');
    expect(document.querySelector('link[rel="canonical"]')?.getAttribute('href')).toBe('https://x.com/a');
    expect(document.querySelector('link[rel="prev"]')?.getAttribute('href')).toBe('https://x.com/p');
    expect(document.querySelector('link[rel="next"]')?.getAttribute('href')).toBe('https://x.com/n');
  });

  it('removes prev/next when not provided', () => {
    setMeta({ title: 'A' });
    expect(document.querySelector('link[rel="prev"]')).toBeNull();
  });

  it('injectJsonLd writes script tag', () => {
    injectJsonLd({ name: 'test', count: 2 });
    const script = document.querySelector('script[data-jsonld="dynamic"]');
    expect(script).not.toBeNull();
    expect(JSON.parse(script!.textContent || '')).toEqual({ name: 'test', count: 2 });
  });

  it('resetMeta sets homepage defaults', () => {
    resetMeta();
    expect(document.title).toBe('首页 - Flask Blog');
    expect(document.querySelector('meta[property="og:type"]')?.getAttribute('content')).toBe('website');
  });
});
