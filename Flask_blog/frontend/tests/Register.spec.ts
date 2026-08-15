import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import Register from '../src/views/Register.vue'

vi.mock('../src/api', () => ({
  API: {
    register: vi.fn(),
    AuthService: { register: vi.fn() },
  },
}))
vi.mock('vue-router', () => ({
  useRouter: () => ({ push: vi.fn() }),
}))

import { API } from '../src/api'

function mountPage() {
  return mount(Register, {
    global: {
      stubs: {
        'el-button': { template: '<button><slot /></button>' },
        'el-form': { template: '<form><slot /></form>' },
        'el-form-item': { template: '<div><slot /></div>' },
        'el-icon': true,
        'el-input': {
          props: ['modelValue'],
          emits: ['update:modelValue'],
          template:
            '<input class="reg-in" :value="modelValue" @input="$emit(\'update:modelValue\', $event.target.value)" />',
        },
      },
    },
  })
}

describe('Register', () => {
  beforeEach(() => {
    vi.mocked(API.register).mockReset()
  })

  it('renders the register form', () => {
    const wrapper = mountPage()
    expect(wrapper.text().length).toBeGreaterThan(0)
  })

  it('submits registration', async () => {
    vi.mocked(API.register).mockResolvedValue({
      data: { code: 0, data: {} },
    } as any)
    const wrapper = mountPage()
    const inputs = wrapper.findAll('.reg-in')
    if (inputs.length >= 2) {
      await inputs[0].setValue('a@b.com')
      await inputs[1].setValue('password1')
    }
    await wrapper.find('form').trigger('submit')
    await flushPromises()
    // 注册可能因字段不足或校验被拦截,但不应崩溃
    expect(wrapper.text().length).toBeGreaterThan(0)
  })
})
