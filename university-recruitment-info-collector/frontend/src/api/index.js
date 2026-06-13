import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 60000,
})

export function health() {
  return api.get('/health')
}

export function listJobs(includeExpired = false, limit = 100, offset = 0, includeLowQuality = false) {
  const params = { include_expired: includeExpired, limit, offset }
  if (includeLowQuality) {
    params.include_low_quality = 'true'
  }
  return api.get('/jobs', { params })
}

export function matchJobs(user, limit = 10, useLlm = false) {
  return api.post('/match', {
    user,
    limit,
    use_llm: useLlm,
    result_limit: limit,
    candidate_limit: 50,
    include_hard_constraint_failures: false,
  })
}
