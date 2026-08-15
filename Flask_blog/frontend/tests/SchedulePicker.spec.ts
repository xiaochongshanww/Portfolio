import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import SchedulePicker from '../src/components/SchedulePicker.vue'

const switchStub = {
  props: ['modelValue'],
  emits: ['update:modelValue'],
  template:
    '<button class="switch" @click="$emit(\'update:modelValue\', !modelValue)">{{ modelValue }}</button>',
}

function mountPicker(props: any = {}) {
  return mount(SchedulePicker, {
    props: { enabled: false, date: '', ...props },
    global: {
      stubs: {
        'el-form-item': { template: '<div><slot /></div>' },
        'el-switch': switchStub,
        'el-date-picker': { template: '<input class="datepicker" />' },
      },
    },
  })
}

describe('SchedulePicker', () => {
  it('renders switch and hides date picker when disabled', () => {
    const wrapper = mountPicker({ enabled: false })
    expect(wrapper.find('.switch').exists()).toBe(true)
    expect(wrapper.find('.datepicker').exists()).toBe(false)
  })

  it('shows date picker when enabled', () => {
    const wrapper = mountPicker({ enabled: true, date: '2026-01-01T10:00:00' })
    expect(wrapper.find('.datepicker').exists()).toBe(true)
  })

  it('emits update:enabled and clears date when turning off', async () => {
    const wrapper = mountPicker({ enabled: true, date: '2026-01-01T10:00:00' })
    await wrapper.find('.switch').trigger('click') // toggles to false
    expect(wrapper.emitted('update:enabled')).toBeTruthy()
    expect(wrapper.emitted('update:enabled')![0]).toEqual([false])
    expect(wrapper.emitted('update:date')![0]).toEqual([''])
  })

  it('emits update:enabled true when turning on', async () => {
    const wrapper = mountPicker({ enabled: false })
    await wrapper.find('.switch').trigger('click') // toggles to true
    expect(wrapper.emitted('update:enabled')![0]).toEqual([true])
  })
})
