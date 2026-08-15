import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import { mount } from '@vue/test-utils';
import ScrollToTop from '../src/components/ScrollToTop.vue';

function setScrollY(value: number) {
  Object.defineProperty(window, 'scrollY', { value, configurable: true });
}

describe('ScrollToTop', () => {
  beforeEach(() => {
    setScrollY(0);
  });

  afterEach(() => {
    document.body.innerHTML = '';
  });

  it('renders and is hidden below threshold', () => {
    const wrapper = mount(ScrollToTop);
    const btn = wrapper.find('.scroll-to-top-btn');
    expect(btn.exists()).toBe(true);
    // v-show display:none when not scrolled
    expect(btn.element.style.display).toBe('none');
  });

  it('becomes visible after scrolling past threshold', async () => {
    const wrapper = mount(ScrollToTop, { props: { threshold: 300 } });
    setScrollY(600);
    window.dispatchEvent(new Event('scroll'));
    // 等待节流定时器(16ms)
    await new Promise((r) => setTimeout(r, 40));
    const btn = wrapper.find('.scroll-to-top-btn');
    expect(btn.element.style.display).not.toBe('none');
    expect(btn.isVisible()).toBe(true);
  });

  it('accepts custom duration and easing props', () => {
    const wrapper = mount(ScrollToTop, {
      props: { duration: 500, easing: 'linear' },
    });
    expect(wrapper.props('duration')).toBe(500);
    expect(wrapper.props('easing')).toBe('linear');
  });
});
