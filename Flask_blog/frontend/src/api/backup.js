/**
 * @deprecated 请使用 `import { API } from '@/api'` 替代。
 * 例如: API.getBackupRecords(params) 代替 backupApi.getBackupRecords(params)
 */
import API from './index'

/** @param {string} name */
const deprecate = (name) =>
  console.warn(`[deprecated] backupApi.${name}() — 请改用 API.${name}()`)

/**
 * @type {Record<string, (...args: any[]) => Promise<any>>}
 */
const api = new Proxy({}, {
  /**
   * @param {object} _target
   * @param {string | symbol} method
   */
  get(_target, method) {
    const name = String(method)
    deprecate(name)
    /** @type {(...args: unknown[]) => any} */
    return (...args) => API[name]?.(...args)
  },
})

export const backupApi = api
export default backupApi
