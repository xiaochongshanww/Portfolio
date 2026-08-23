const DEFAULT_BASE_URL = 'http://127.0.0.1:8000'
const DEFAULT_API_KEY_ENV = 'STRUCTURAL_KB_API_KEY'
const DEFAULT_TIMEOUT_MS = 120000

export const name = 'dsh-structural-kb'
export const inject = ['tools']

const jsonString = (description) => ({ type: 'string', description })
const jsonInteger = (description) => ({ type: 'integer', description })
const jsonBoolean = (description) => ({ type: 'boolean', description })

const pageAssetSchema = {
  type: 'object',
  additionalProperties: false,
  properties: {
    kind: jsonString('资产类型。'),
    path: jsonString('服务内相对路径。'),
    url: jsonString('可直接访问的短期地址（已补齐 baseUrl）。'),
    source_file: jsonString('来源 PDF 文件名。'),
    page: { type: 'integer', description: 'PDF 页码。' },
  },
  required: ['kind', 'path', 'url', 'source_file'],
}

const resultSchema = {
  type: 'object',
  additionalProperties: false,
  properties: {
    rank: jsonInteger('结果排名，从 1 开始。'),
    source_kind: jsonString('retrieval 或 structured_table。'),
    source_file: jsonString('来源 PDF 文件名。'),
    standard_code: jsonString('规范编号。'),
    standard_name: jsonString('规范名称。'),
    version: jsonString('规范版本。'),
    section_type: jsonString('正文、正文表格、条文说明、附录等。'),
    authority_level: jsonInteger('来源权威等级，数值越高越优先。'),
    is_table: jsonBoolean('是否为表格依据。'),
    clause_number: jsonString('条文号。'),
    table_id: jsonString('表号。'),
    table_name: jsonString('表名。'),
    pages: { type: 'array', items: { type: 'integer' }, description: '来源 PDF 页码。' },
    excerpt: jsonString('有限长度的检索原文。'),
    score: { type: 'number', description: '服务端排序分数，仅用于辅助判断。' },
    reason: jsonString('命中原因。'),
    retrieval_sources: { type: 'array', items: jsonString('召回来源。') },
    matched_terms: { type: 'array', items: jsonString('结构化表格命中的词。') },
    structured_row: {
      description: '结构化表格行数据；非表格结果为 null，表格命中时为对象。',
      oneOf: [
        { type: 'object', additionalProperties: true },
        { type: 'null' },
      ],
    },
    assets: { type: 'array', items: pageAssetSchema, description: '页面截图证据（include_assets: true 时返回，可配合 get_structural_spec_page 展示）。' },
  },
  required: [
    'rank',
    'source_kind',
    'source_file',
    'standard_code',
    'standard_name',
    'version',
    'section_type',
    'authority_level',
    'is_table',
    'clause_number',
    'table_id',
    'table_name',
    'pages',
    'excerpt',
    'score',
    'reason',
    'retrieval_sources',
    'matched_terms',
    'structured_row',
    'assets',
  ],
}

const searchOutputSchema = {
  type: 'object',
  additionalProperties: false,
  properties: {
    query: jsonString('原始问题。'),
    normalized_query: jsonString('服务端规范化后的问题。'),
    mode: jsonString('实际使用的检索模式。'),
    data_version_hash: jsonString('当前知识库数据版本。'),
    result_count: jsonInteger('结果数量。'),
    results: { type: 'array', items: resultSchema },
    warnings: { type: 'array', items: jsonString('警告信息。') },
  },
  required: ['query', 'normalized_query', 'mode', 'data_version_hash', 'result_count', 'results', 'warnings'],
}

const readyOutputSchema = {
  type: 'object',
  additionalProperties: false,
  properties: {
    ready: jsonBoolean('知识库是否可查询。'),
    service: jsonString('服务名称。'),
    api_version: jsonString('集成 API 版本。'),
    data_version_hash: jsonString('当前知识库数据版本。'),
  },
  required: ['ready', 'service', 'api_version', 'data_version_hash'],
}

const imageValueSchema = {
  type: 'object',
  additionalProperties: false,
  properties: {
    attachmentId: jsonString('附件库中的图片 ID。'),
    mediaType: {
      type: 'string',
      enum: ['image/png', 'image/jpeg', 'image/webp', 'image/gif'],
      description: '图片媒体类型。',
    },
    bytes: jsonInteger('图片字节数。'),
    width: jsonInteger('图片宽度（像素）。'),
    height: jsonInteger('图片高度（像素）。'),
    name: jsonString('图片名称。'),
  },
  required: ['attachmentId', 'mediaType', 'bytes', 'width', 'height'],
}

const pageOutputSchema = {
  type: 'object',
  additionalProperties: false,
  properties: {
    source_file: jsonString('来源 PDF 文件名。'),
    page: { type: 'integer', description: 'PDF 页码。' },
    path: jsonString('服务内相对路径。'),
    url: jsonString('可直接访问的短期地址（已补齐 baseUrl）。'),
    image: Object.assign({}, imageValueSchema, {
      description: '页面截图附件；仅当当前模型支持图片输入且附件服务可用时存在，否则为 undefined。',
    }),
  },
  required: ['source_file', 'page', 'path', 'url'],
}

function normalizedConfig(config = {}) {
  const baseUrl = String(config.baseUrl || process.env.STRUCTURAL_KB_BASE_URL || DEFAULT_BASE_URL)
    .trim()
    .replace(/\/+$/, '')
  if (!/^https?:\/\//i.test(baseUrl)) {
    throw new Error('结构规范知识库 baseUrl 必须是 http 或 https 地址')
  }

  const timeoutMs = Number(config.requestTimeoutMs || DEFAULT_TIMEOUT_MS)
  if (!Number.isInteger(timeoutMs) || timeoutMs < 1000 || timeoutMs > 300000) {
    throw new Error('结构规范知识库 requestTimeoutMs 必须在 1000 到 300000 之间')
  }

  const apiKeyEnv = String(config.apiKeyEnv || DEFAULT_API_KEY_ENV).trim()
  const apiKey = String(config.apiKey || process.env[apiKeyEnv] || '').trim()
  return { baseUrl, timeoutMs, apiKey }
}

async function requestJson(config, path, init, exec) {
  const controller = new AbortController()
  const upstreamSignal = exec?.signal
  const abort = () => controller.abort(upstreamSignal?.reason)
  if (upstreamSignal?.aborted) abort()
  else upstreamSignal?.addEventListener('abort', abort, { once: true })

  const timer = setTimeout(() => controller.abort(new Error('request timeout')), config.timeoutMs)
  try {
    const headers = new Headers(init?.headers || {})
    headers.set('accept', 'application/json')
    if (init?.body !== undefined) headers.set('content-type', 'application/json')
    if (config.apiKey) headers.set('authorization', `Bearer ${config.apiKey}`)

    const response = await fetch(`${config.baseUrl}${path}`, {
      ...init,
      headers,
      signal: controller.signal,
    })
    const body = await response.text()
    let payload
    try {
      payload = body ? JSON.parse(body) : null
    } catch {
      throw new Error(`知识库返回了无效 JSON（HTTP ${response.status}）`)
    }
    if (!response.ok) {
      const message = payload?.error?.message || payload?.detail || `HTTP ${response.status}`
      throw new Error(`规范知识库请求失败：${message}`)
    }
    return payload
  } finally {
    clearTimeout(timer)
    upstreamSignal?.removeEventListener('abort', abort)
  }
}

/** 把服务端返回的相对地址补齐为可直接访问的绝对地址。 */
function toAbsolute(baseUrl, url) {
  if (typeof url !== 'string' || url.length === 0) return url
  if (/^https?:\/\//i.test(url)) return url
  return `${baseUrl}${url.startsWith('/') ? url : `/${url}`}`
}

/** 把输出 schema 中的图片元数据还原为内容块携带的附件引用。 */
function pageImageRef(image) {
  const ref = {
    attachmentId: image.attachmentId,
    mediaType: image.mediaType,
    bytes: image.bytes,
    width: image.width,
    height: image.height,
  }
  if (typeof image.name === 'string' && image.name.length > 0) ref.name = image.name
  return ref
}

/** 当前模型路由是否声明了图片输入能力（镜像 read_image 的路线门控）。 */
async function routeAcceptsImages(ctx, exec) {
  try {
    const routed = exec?.agent?.session?.requestHeader?.()?.config
    const provider = routed?.provider ?? exec?.agent?.options?.provider
    const model = routed?.model ?? exec?.agent?.options?.model
    const llm = ctx.get('llm')
    if (provider === undefined || model === undefined || llm === undefined) return false
    const active = await llm.resolveModelInfo(provider, model, exec.signal)
    return Array.isArray(active.inputModalities) && active.inputModalities.includes('image')
  } catch {
    return false
  }
}

/**
 * 取回页面截图并写入附件库。任何一步失败（模型不支持图片、附件服务缺失、
 * 类型/大小超限、网络错误）都返回 undefined，由调用方降级为仅提供证据地址。
 */
async function fetchPageImage(ctx, config, meta, exec) {
  const attachments = ctx.get('attachments')
  const path = typeof meta.path === 'string' && meta.path.length > 0 ? meta.path
    : typeof meta.url === 'string' && meta.url.length > 0 ? meta.url
      : ''
  if (attachments === undefined || path.length === 0) return undefined
  if (!(await routeAcceptsImages(ctx, exec))) return undefined

  const controller = new AbortController()
  const upstreamSignal = exec?.signal
  const abort = () => controller.abort(upstreamSignal?.reason)
  if (upstreamSignal?.aborted) abort()
  else upstreamSignal?.addEventListener('abort', abort, { once: true })
  const timer = setTimeout(() => controller.abort(new Error('request timeout')), config.timeoutMs)
  try {
    const response = await fetch(`${config.baseUrl}${path.startsWith('/') ? path : `/${path}`}`, {
      headers: config.apiKey ? { authorization: `Bearer ${config.apiKey}` } : undefined,
      signal: controller.signal,
    })
    if (!response.ok) return undefined
    const mediaType = String(response.headers.get('content-type') || '').split(';')[0].trim()
    if (!attachments.imageLimits.mediaTypes.includes(mediaType)) return undefined
    const data = new Uint8Array(await response.arrayBuffer())
    const byteCap = Math.min(attachments.imageLimits.maxImageBytes, attachments.imageLimits.maxMessageImageBytes)
    if (data.length === 0 || data.length > byteCap) return undefined
    const name = meta.source_file ? `${meta.source_file} 第 ${meta.page} 页` : undefined
    const ref = await attachments.saveImage({ data, mediaType, name })
    return {
      attachmentId: ref.attachmentId,
      mediaType: ref.mediaType,
      bytes: ref.bytes,
      width: ref.width,
      height: ref.height,
      ...(typeof ref.name === 'string' && ref.name.length > 0 ? { name: ref.name } : {}),
    }
  } catch {
    return undefined
  } finally {
    clearTimeout(timer)
    upstreamSignal?.removeEventListener('abort', abort)
  }
}

function renderReady(_args, value) {
  return [{ type: 'text', text: value.ready ? `规范知识库已就绪，数据版本 ${value.data_version_hash || 'unknown'}` : '规范知识库尚未就绪。' }]
}

function renderSearch(_args, value) {
  const lines = [`规范检索：${value.query}`, `数据版本：${value.data_version_hash || 'unknown'}`]
  if (!value.results.length) lines.push('未找到可用规范依据。')
  for (const result of value.results) {
    const source = [result.standard_code, result.standard_name].filter(Boolean).join(' ')
    const location = [result.clause_number && `条文 ${result.clause_number}`, result.table_id && `表 ${result.table_id}`, result.pages.length && `页 ${result.pages.join(',')}`].filter(Boolean).join(' · ')
    lines.push(`\n[${result.rank}] ${source || result.source_file}`)
    lines.push(`依据类型：${result.section_type || 'unknown'} · 权威等级：${result.authority_level} · ${location}`)
    if (result.table_name) lines.push(`表名：${result.table_name}`)
    lines.push(result.excerpt)
    for (const asset of result.assets || []) lines.push(`页面证据：${asset.url}`)
  }
  for (const warning of value.warnings || []) lines.push(`警告：${warning}`)
  return [{ type: 'text', text: lines.join('\n') }]
}

function renderPage(_args, value) {
  const blocks = [{ type: 'text', text: `规范来源：${value.source_file} 第 ${value.page} 页\n页面证据：${value.url}` }]
  if (value.image) blocks.push({ type: 'image', attachment: pageImageRef(value.image) })
  return blocks
}

function genericCall(title, kind) {
  return (args) => ({
    card: 'generic',
    kind,
    title: `${title}：${String(args?.query || args?.source_file || '').slice(0, 80)}`,
  })
}

export function apply(ctx, rawConfig = {}) {
  const config = normalizedConfig(rawConfig)

  ctx.tools.register({
    name: 'structural_kb_ready',
    description: '检查结构设计规范知识库是否就绪。知识库问答前可调用一次。',
    parameters: { type: 'object', properties: {}, required: [], additionalProperties: false },
    output: { schema: readyOutputSchema, render: renderReady },
    timeoutMs: config.timeoutMs,
    async execute(_args, exec) {
      return requestJson(config, '/integrations/deepseek-harness/ready', { method: 'GET' }, exec)
    },
    presentCall: genericCall('检查规范知识库', 'read'),
  })

  ctx.tools.register({
    name: 'search_structural_specs',
    description: '检索结构设计规范的正文、正文表格、条文和结构化表格数据。涉及规范取值、条文要求或表格时优先使用此工具；回答必须引用返回的规范编号、条文/表号和页码，不能把检索分数当作规范结论。展示页面截图证据时必须传 include_assets: true。',
    parameters: {
      type: 'object',
      properties: {
        query: { type: 'string', description: '自然语言规范问题。' },
        top_k: { type: 'integer', description: '返回数量，1 到 10，默认 5。' },
        document: { type: 'string', description: '可选规范编号或文件名筛选。' },
        mode: { type: 'string', enum: ['auto', 'table', 'clause', 'definition', 'general'], description: '检索意图，默认 auto。' },
        include_assets: { type: 'boolean', description: '是否返回页面截图证据地址，默认 false。' },
      },
      required: ['query'],
      additionalProperties: false,
    },
    output: { schema: searchOutputSchema, render: renderSearch },
    timeoutMs: config.timeoutMs,
    async execute(args, exec) {
      const query = String(args.query || '').trim()
      if (!query) throw new Error('规范检索 query 不能为空')
      const topK = Math.max(1, Math.min(10, Number.isInteger(args.top_k) ? args.top_k : 5))
      const payload = await requestJson(config, '/integrations/deepseek-harness/search', {
        method: 'POST',
        body: JSON.stringify({
          query,
          top_k: topK,
          document: String(args.document || '').trim(),
          mode: args.mode || 'auto',
          include_assets: args.include_assets === true,
        }),
      }, exec)
      // 把服务端返回的相对证据地址补齐为可直接访问的绝对地址。
      for (const result of payload.results || []) {
        for (const asset of result.assets || []) {
          if (typeof asset.url === 'string') asset.url = toAbsolute(config.baseUrl, asset.url)
        }
      }
      return payload
    },
    presentCall: genericCall('检索结构设计规范', 'search'),
  })

  ctx.tools.register({
    name: 'get_structural_spec_page',
    description: '获取结构设计规范指定 PDF 页面的受控证据，并在会话中展示该页截图。需要向用户展示原始页面、核对图表或公式时使用；当前模型支持图片输入且附件可用时直接返回页面截图，否则返回页面证据地址。',
    parameters: {
      type: 'object',
      properties: {
        source_file: { type: 'string', description: '来源 PDF 文件名，必须来自检索结果。' },
        page: { type: 'integer', description: 'PDF 页码，从 1 开始。' },
      },
      required: ['source_file', 'page'],
      additionalProperties: false,
    },
    output: { schema: pageOutputSchema, render: renderPage },
    timeoutMs: config.timeoutMs,
    async execute(args, exec) {
      const sourceFile = String(args.source_file || '').trim()
      const page = Number(args.page)
      if (!sourceFile || !Number.isInteger(page) || page < 1) {
        throw new Error('source_file 和 page 必须来自有效的规范来源')
      }
      const query = new URLSearchParams({ source_file: sourceFile, page: String(page) })
      const meta = await requestJson(config, `/integrations/deepseek-harness/page?${query}`, { method: 'GET' }, exec)
      const value = {
        source_file: typeof meta.source_file === 'string' ? meta.source_file : sourceFile,
        page: Number.isInteger(meta.page) ? meta.page : page,
        path: typeof meta.path === 'string' ? meta.path : '',
        url: toAbsolute(config.baseUrl, meta.url),
      }
      try {
        const image = await fetchPageImage(ctx, config, meta, exec)
        if (image !== undefined) value.image = image
      } catch {
        // 截图附加失败时降级为仅返回证据地址。
      }
      return value
    },
    presentCall: genericCall('获取规范页面', 'fetch'),
  })
}
