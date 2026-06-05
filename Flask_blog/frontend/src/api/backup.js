/**
 * @deprecated 请使用 `import { API } from '@/api'` 替代。
 * 例如: API.getBackupRecords(params) 代替 backupApi.getBackupRecords(params)
 */
import API from './index'

const deprecate = (name) =>
  console.warn(`[deprecated] backupApi.${name}() — 请改用 API.${name}()`)

const api = new Proxy({}, {
  get(_, method) {
    deprecate(method)
    return (...args) => API[method]?.(...args)
  },
})

export const backupApi = api
export default backupApi
