import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 60000,
})

export function health() {
  return api.get('/health')
}

export function listJobs(includeExpired = false) {
  return api.get('/jobs', { params: { include_expired: includeExpired } })
}

export function matchJobs(user, limit = 10, useLlm = false) {
  return api.post('/match', { user, limit, use_llm: useLlm })
}
