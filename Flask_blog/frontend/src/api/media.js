/**
 * @deprecated 请使用 `import { API } from '@/api'` 替代。
 * 例如: API.getMediaList(params) 代替 mediaApi.getMediaList(params)
 */
import API from './index'

const deprecate = (name) =>
  console.warn(`[deprecated] mediaApi.${name}() — 请改用 API.${name}()`)

const api = new Proxy({}, {
  get(_, method) {
    deprecate(method)
    return (...args) => API[method]?.(...args)
  },
})

export const mediaApi = api
export default mediaApi
