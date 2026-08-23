import assert from 'node:assert/strict'
import { test } from 'node:test'

import { apply } from '../src/index.mjs'

function registerTools(config = {}, overrides = {}) {
  const registered = []
  const ctx = { tools: { register(tool) { registered.push(tool) } }, ...overrides }
  apply(ctx, config)
  return registered
}

test('registers the read-only structural knowledge tools', () => {
  const tools = registerTools({ baseUrl: 'http://127.0.0.1:8000', requestTimeoutMs: 1000 })
  assert.deepEqual(tools.map(tool => tool.name), [
    'structural_kb_ready',
    'search_structural_specs',
    'get_structural_spec_page',
  ])
  assert.equal(tools.every(tool => tool.output?.schema), true)
})

test('calls the backend with the configured authorization header', async () => {
  const originalFetch = globalThis.fetch
  const requests = []
  globalThis.fetch = async (input, init) => {
    requests.push({ url: String(input), headers: new Headers(init?.headers) })
    const payload = String(input).endsWith('/ready')
      ? { ready: true, service: 'test', api_version: '1', data_version_hash: 'v1' }
      : {
          query: '办公楼楼面活荷载标准值',
          normalized_query: '办公楼楼面活荷载标准值',
          mode: 'table',
          data_version_hash: 'v1',
          result_count: 0,
          results: [],
          warnings: [],
        }
    return new Response(JSON.stringify(payload), {
      status: 200,
      headers: { 'content-type': 'application/json' },
    })
  }

  try {
    const tools = registerTools({
      baseUrl: 'http://127.0.0.1:8000',
      apiKey: 'test-key',
      requestTimeoutMs: 1000,
    })
    const signal = new AbortController().signal
    const ready = await tools[0].execute({}, { signal })
    const search = await tools[1].execute(
      { query: '办公楼楼面活荷载标准值', mode: 'table' },
      { signal },
    )

    assert.equal(ready.ready, true)
    assert.equal(search.mode, 'table')
    assert.equal(requests[0].url, 'http://127.0.0.1:8000/integrations/deepseek-harness/ready')
    assert.equal(requests[0].headers.get('authorization'), 'Bearer test-key')
    assert.equal(requests[1].url, 'http://127.0.0.1:8000/integrations/deepseek-harness/search')
    assert.equal(requests[1].headers.get('content-type'), 'application/json')
  } finally {
    globalThis.fetch = originalFetch
  }
})

test('rejects an invalid backend URL before registering tools', () => {
  assert.throws(
    () => registerTools({ baseUrl: 'file:///tmp/knowledge-base' }),
    /baseUrl 必须是 http 或 https 地址/,
  )
})

test('search output schema accepts structured_row as null or object', () => {
  const tools = registerTools({ baseUrl: 'http://127.0.0.1:8000', requestTimeoutMs: 1000 })
  const rowSchema = tools[1].output.schema.properties.results.items.properties.structured_row
  // 宿主侧 JSON Schema 子集不支持 type 数组；必须用 oneOf 同时接受对象与非表格结果的 null。
  assert.ok(Array.isArray(rowSchema.oneOf) && rowSchema.oneOf.length >= 2)
  assert.ok(rowSchema.oneOf.some(branch => branch.type === 'object'))
  assert.ok(rowSchema.oneOf.some(branch => branch.type === 'null'))
})

test('get_structural_spec_page attaches the page screenshot when the route accepts images', async () => {
  const originalFetch = globalThis.fetch
  const calls = []
  const png = new Uint8Array([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a])
  globalThis.fetch = async (input, init) => {
    const url = String(input)
    calls.push(url)
    if (url.includes('/integrations/deepseek-harness/page')) {
      return new Response(JSON.stringify({
        source_file: 'GB 50011-2010_建筑抗震设计规范_2016年版.pdf',
        page: 114,
        path: '/page-images/GB 50011.pdf/114',
        url: '/page-images/GB 50011.pdf/114',
      }), { status: 200, headers: { 'content-type': 'application/json' } })
    }
    return new Response(png, { status: 200, headers: { 'content-type': 'image/png' } })
  }
  const saved = []
  const overrides = {
    get(name) {
      if (name === 'attachments') {
        return {
          imageLimits: {
            mediaTypes: ['image/png', 'image/jpeg', 'image/webp', 'image/gif'],
            maxImageBytes: 10_000_000,
            maxMessageImageBytes: 5_000_000,
          },
          async saveImage({ data, mediaType, name }) {
            saved.push({ bytes: data.length, mediaType, name })
            return { attachmentId: 'att-1', mediaType, bytes: data.length, width: 100, height: 200, name }
          },
        }
      }
      if (name === 'llm') {
        return { async resolveModelInfo() { return { inputModalities: ['text', 'image'] } } }
      }
      return undefined
    },
  }
  try {
    const tools = registerTools({ baseUrl: 'http://127.0.0.1:8000', requestTimeoutMs: 1000 }, overrides)
    const exec = {
      signal: new AbortController().signal,
      agent: {
        options: { provider: 'test', model: 'vision-model' },
        session: { requestHeader: () => ({ config: { provider: 'test', model: 'vision-model' } }) },
      },
    }
    const value = await tools[2].execute(
      { source_file: 'GB 50011-2010_建筑抗震设计规范_2016年版.pdf', page: 114 },
      exec,
    )
    assert.equal(value.image.attachmentId, 'att-1')
    assert.equal(value.image.mediaType, 'image/png')
    assert.equal(value.url, 'http://127.0.0.1:8000/page-images/GB 50011.pdf/114')
    assert.equal(saved.length, 1)
    assert.equal(calls.length, 2)
    const blocks = tools[2].output.render({}, value)
    assert.equal(blocks[1].type, 'image')
    assert.equal(blocks[1].attachment.attachmentId, 'att-1')
  } finally {
    globalThis.fetch = originalFetch
  }
})

test('get_structural_spec_page falls back to the evidence URL when images cannot be attached', async () => {
  const originalFetch = globalThis.fetch
  globalThis.fetch = async (input) => {
    if (String(input).includes('/integrations/deepseek-harness/page?')) {
      return new Response(JSON.stringify({
        source_file: 'GB 50011-2010.pdf',
        page: 114,
        path: '/page-images/x/114',
        url: '/page-images/x/114',
      }), { status: 200, headers: { 'content-type': 'application/json' } })
    }
    throw new Error('should not fetch the page image')
  }
  try {
    const tools = registerTools({ baseUrl: 'http://127.0.0.1:8000', requestTimeoutMs: 1000 })
    const exec = { signal: new AbortController().signal }
    const value = await tools[2].execute({ source_file: 'GB 50011-2010.pdf', page: 114 }, exec)
    assert.equal(value.image, undefined)
    assert.equal(value.url, 'http://127.0.0.1:8000/page-images/x/114')
  } finally {
    globalThis.fetch = originalFetch
  }
})
