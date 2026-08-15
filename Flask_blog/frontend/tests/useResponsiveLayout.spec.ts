import { describe, it, expect, beforeAll } from 'vitest';
import { mount } from '@vue/test-utils';
import { defineComponent } from 'vue';
import {
  useResponsiveLayout,
  useSimpleResponsive,
} from '../src/composables/useResponsiveLayout';

// jsdom 无 ResizeObserver,提供桩
beforeAll(() => {
  if (typeof (globalThis as any).ResizeObserver === 'undefined') {
    (globalThis as any).ResizeObserver = class {
      observe() {}
      unobserve() {}
      disconnect() {}
    };
  }
});

function host() {
  const wrapper = mount(
    defineComponent({
      setup() {
        return { layout: useResponsiveLayout() };
      },
      template: '<div/>',
    })
  );
  // @ts-ignore
  return wrapper.vm.layout;
}

describe('useResponsiveLayout', () => {
  it('computes layout based on window width (jsdom default 1024)', () => {
    const layout = host();
    // requiredWidth = 550+30+320+60+0 = 960; jsdom innerWidth=1024 -> est container 960
    expect(layout.requiredWidth.value).toBe(960);
    expect(layout.windowWidth.value).toBeGreaterThan(0);
    expect(typeof layout.containerWidth.value).toBe('number');
    expect(layout.canShowSidebar.value).toBeTypeOf('boolean');
    expect(layout.isMobile.value).toBe(!layout.canShowSidebar.value);
    expect(layout.isDesktop.value).toBe(layout.canShowSidebar.value);
    expect(layout.layoutMode.value).toBe(
      layout.isMobile.value ? 'mobile' : 'desktop'
    );
  });

  it('updateContainerWidth runs without container element', () => {
    const layout = host();
    expect(() => layout.updateContainerWidth()).not.toThrow();
  });

  it('debugInfo exposes state', () => {
    const layout = host();
    const info = layout.debugInfo.value;
    expect(info.windowWidth).toBeGreaterThan(0);
    expect(info.layoutRequirements).toBeTypeOf('object');
  });
});

describe('useSimpleResponsive', () => {
  it('returns isMobile/isDesktop/windowWidth', () => {
    const wrapper = mount(
      defineComponent({
        setup() {
          return { s: useSimpleResponsive() };
        },
        template: '<div/>',
      })
    );
    // @ts-ignore
    const s = wrapper.vm.s;
    expect(s.isMobile.value).toBeTypeOf('boolean');
    expect(s.isDesktop.value).toBeTypeOf('boolean');
    expect(s.windowWidth.value).toBeGreaterThan(0);
  });
});
