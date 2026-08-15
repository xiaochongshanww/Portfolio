import { describe, it, expect } from 'vitest';
import { mount } from '@vue/test-utils';
import GlobalNotify from '../src/components/GlobalNotify.vue';
import { useNotify } from '../src/composables/useNotify';

describe('GlobalNotify', () => {
  it('renders nothing when queue is empty', () => {
    const wrapper = mount(GlobalNotify);
    expect(wrapper.find('.notice').exists()).toBe(false);
  });

  it('renders pushed messages with type class', async () => {
    const { pushError } = useNotify();
    const wrapper = mount(GlobalNotify);
    pushError('boom');
    await wrapper.vm.$nextTick();
    expect(wrapper.find('.notice').exists()).toBe(true);
    expect(wrapper.find('.notice').text()).toBe('boom');
    expect(wrapper.find('.notice.error').exists()).toBe(true);
  });

  it('renders success type', async () => {
    const { pushSuccess } = useNotify();
    const wrapper = mount(GlobalNotify);
    pushSuccess('ok');
    await wrapper.vm.$nextTick();
    expect(wrapper.find('.notice.success').exists()).toBe(true);
  });
});
