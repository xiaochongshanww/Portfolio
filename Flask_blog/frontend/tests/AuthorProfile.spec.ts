import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import AuthorProfile from '../src/views/AuthorProfile.vue'

vi.mock('../src/api', () => ({
  API: { getPublicUserStats: vi.fn() },
}))
vi.mock('../src/generated', () => ({
  UsersService: {
    getApiV1UsersPublic: vi.fn(),
    getApiV1UsersPublicArticles: vi.fn(),
  },
}))
vi.mock('vue-router', () => ({
  useRoute: () => ({ params: { id: '5' } }),
}))

import { API } from '../src/api'
import { UsersService } from '../src/generated'

const linkStub = { template: '<a><slot /></a>' }

describe('AuthorProfile', () => {
  beforeEach(() => {
    vi.mocked(API.getPublicUserStats).mockReset()
    vi.mocked(UsersService.getApiV1UsersPublic).mockReset()
    vi.mocked(UsersService.getApiV1UsersPublicArticles).mockReset()
  })

  it('loads and renders author profile and articles', async () => {
    vi.mocked(UsersService.getApiV1UsersPublic).mockResolvedValue({
      data: { id: 5, nickname: 'Author X', bio: 'bio here' },
    } as any)
    vi.mocked(API.getPublicUserStats).mockResolvedValue({
      data: { data: { total_articles: 1 } },
    } as any)
    vi.mocked(UsersService.getApiV1UsersPublicArticles).mockResolvedValue({
      data: {
        list: [{ id: 1, title: 'Authored Article', slug: 'au' }],
        total: 1,
      },
    } as any)
    const wrapper = mount(AuthorProfile, {
      global: { stubs: { 'el-icon': true, 'router-link': linkStub } },
    })
    await flushPromises()
    await wrapper.vm.$nextTick()
    expect(vi.mocked(UsersService.getApiV1UsersPublic)).toHaveBeenCalledWith(5)
    expect(wrapper.text()).toContain('Author X')
    expect(wrapper.text()).toContain('Authored Article')
  })

  it('shows fallback when profile missing', async () => {
    vi.mocked(UsersService.getApiV1UsersPublic).mockRejectedValue(new Error('x'))
    vi.mocked(API.getPublicUserStats).mockResolvedValue({ data: {} } as any)
    vi.mocked(UsersService.getApiV1UsersPublicArticles).mockResolvedValue({
      data: { list: [], total: 0 },
    } as any)
    const wrapper = mount(AuthorProfile, {
      global: { stubs: { 'el-icon': true, 'router-link': linkStub } },
    })
    await flushPromises()
    await wrapper.vm.$nextTick()
    expect(wrapper.text().length).toBeGreaterThan(0)
  })
})
