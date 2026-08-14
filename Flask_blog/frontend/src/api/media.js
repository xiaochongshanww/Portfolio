/**
 * @deprecated 请使用 `import { API } from '@/api'` 替代。
 * 例如: API.getMediaList(params) 代替 mediaApi.getMediaList(params)
 */
import API from './index'

/**
 * @param {string} name
 */
const deprecate = (name) =>
  console.warn(`[deprecated] mediaApi.${name}() — 请改用 API.${name}()`)

/**
 * @type {Record<string, (...args: any[]) => Promise<any>>}
 */
const api = new Proxy({}, {
  /** @param {any} method */
  get(_, method) {
    deprecate(method)
    return (/** @type {any[]} */ ...args) => API[method]?.(...args)
  },
})

export const mediaApi = api
export default mediaApi
