import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 60000,
})

export function health() {
  return api.get('/health')
}

export function listJobs(includeExpired = false, limit = 100, offset = 0, includeLowQuality = false, filters = {}) {
  const params = { include_expired: includeExpired, limit, offset }
  if (includeLowQuality) {
    params.include_low_quality = 'true'
  }
  if (filters.school) params.school = filters.school
  if (filters.location) params.location = filters.location
  return api.get('/jobs', { params })
}

export function matchJobs(user, options = {}) {
  const {
    resultLimit = 10,
    useLlm = false,
    candidateLimit = 50,
    includeHardConstraintFailures = false,
  } = options

  return api.post('/match', {
    user,
    limit: resultLimit,
    use_llm: useLlm,
    result_limit: resultLimit,
    candidate_limit: candidateLimit,
    include_hard_constraint_failures: includeHardConstraintFailures,
  })
}
