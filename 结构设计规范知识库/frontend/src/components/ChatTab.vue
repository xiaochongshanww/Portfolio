<template>
  <div class="chat-workspace">
    <section class="panel chat-transcript">
      <div class="chat-header">
        <div>
          <div class="section-kicker">ANSWER VALIDATION</div>
          <h2>问答验证会话</h2>
          <p>验证当前活动知识库的检索依据、条文引用、公式和截图渲染。</p>
        </div>
        <button class="btn" type="button" :disabled="busy || !messages.length" @click="resetSession">清空会话</button>
      </div>

      <div ref="messageList" class="chat-messages" aria-live="polite">
        <div v-if="!messages.length" class="chat-empty-state">
          <div class="chat-empty-icon" aria-hidden="true">问</div>
          <strong>开始验证一条规范问答</strong>
          <p>发送问题后，这里会同时显示回答和可渲染的引用内容。</p>
          <div class="chat-examples">
            <button class="btn" type="button" @click="question = '办公楼楼面活荷载标准值取多少？'">办公楼楼面活荷载标准值取多少？</button>
            <button class="btn" type="button" @click="question = '抗震规范第 8.2.1 条是什么？'">抗震规范第 8.2.1 条是什么？</button>
          </div>
        </div>

        <article v-for="(message, index) in messages" :key="`${message.role}-${index}`" class="chat-message" :class="message.role === 'user' ? 'chat-message-user' : 'chat-message-assistant'">
          <div class="chat-message-meta">
            <span>{{ message.role === 'user' ? '提问' : '知识库回答' }}</span>
            <span v-if="message.pending" class="chat-pending">生成中</span>
          </div>
          <div v-if="message.pending" class="chat-thinking"><span></span><span></span><span></span><em>正在检索并生成回答</em></div>
          <div v-if="message.role === 'assistant'" class="chat-message-body markdown-preview answer-preview" v-html="renderMessage(message.content)"></div>
          <div v-else class="chat-message-body">{{ message.content }}</div>
          <div v-if="message.role === 'assistant' && message.content" class="chat-message-footer">
            <span>{{ citationCount(message.content) }} 个截图引用</span>
            <button class="text-button" type="button" @click="copyMessage(message.content)">{{ copiedIndex === index ? '已复制' : '复制回答' }}</button>
          </div>
        </article>
      </div>

      <form class="chat-composer" @submit.prevent="send">
        <input v-model="question" class="field" :disabled="busy" placeholder="例如：办公楼楼面活荷载标准值取多少？" aria-label="验证问题">
        <button class="btn btn-primary" type="submit" :disabled="busy || !question.trim()">{{ busy ? '检索中...' : '发送' }}</button>
      </form>
      <p v-if="error" class="chat-error" role="alert">{{ error }}</p>
    </section>

    <aside class="panel chat-settings">
      <div class="section-kicker">REQUEST SETTINGS</div>
      <h2>验证参数</h2>
      <p class="chat-settings-intro">参数只影响当前验证请求，不会修改知识库配置。</p>
      <label class="setting-field"><span>模型</span><input v-model="model" class="field" :disabled="busy"></label>
      <label class="setting-field"><span>Temperature</span><div class="setting-number"><input v-model.number="temperature" class="field" type="number" min="0" max="1" step="0.1" :disabled="busy"><span>0 - 1</span></div></label>
      <div class="chat-proof">
        <div class="section-kicker">VALIDATION SCOPE</div>
        <h3>本次验证关注</h3>
        <ul>
          <li>规范正文和条文来源</li>
          <li>公式与 Markdown 渲染</li>
          <li>引用截图访问路径</li>
        </ul>
      </div>
      <div class="chat-session-status"><span class="status-dot" :class="busy ? 'status-dot-busy' : ''"></span><div><strong>{{ busy ? '请求进行中' : '会话已就绪' }}</strong><small>{{ messages.length ? `${messages.length} 条消息` : '尚未发送问题' }}</small></div></div>
    </aside>
  </div>
</template>

<script setup lang="ts">
import { nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import MarkdownIt from 'markdown-it'
import { errorMessage, getApiKey } from '../api'

type ChatMessage = { role: 'user' | 'assistant', content: string, pending?: boolean }

const question = ref('')
const messages = ref<ChatMessage[]>([])
const error = ref('')
const busy = ref(false)
const model = ref('mimo-v2.5')
const temperature = ref(0.2)
const copiedIndex = ref<number | null>(null)
const messageList = ref<HTMLElement | null>(null)
const markdown = new MarkdownIt({ html: false, breaks: true, linkify: true })

function renderMessage(content: string) {
  return markdown.render(content || '')
}

function citationCount(content: string) {
  return (content.match(/!\[[^\]]*\]\([^)]*\)/g) || []).length
}

async function send() {
  const prompt = question.value.trim()
  if (!prompt || busy.value) return
  busy.value = true
  error.value = ''
  copiedIndex.value = null
  question.value = ''
  messages.value.push({ role: 'user', content: prompt })
  const assistant: ChatMessage = { role: 'assistant', content: '', pending: true }
  messages.value.push(assistant)
  await scrollToLatest()

  try {
    const key = getApiKey()
    const response = await fetch('/v1/chat/completions', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...(key ? { Authorization: `Bearer ${key}` } : {}) },
      body: JSON.stringify({ model: model.value, temperature: temperature.value, stream: false, messages: [{ role: 'user', content: prompt }] }),
    })
    const data = await response.json().catch(() => null)
    if (!response.ok) {
      const detail = data && typeof data === 'object' ? (data.detail || data.message) : ''
      throw new Error(detail ? String(detail) : `${response.status} ${response.statusText}`)
    }
    assistant.content = extractContent(data)
    if (!assistant.content) assistant.content = JSON.stringify(data, null, 2)
  } catch (err: unknown) {
    assistant.content = `请求失败：${errorMessage(err)}`
    error.value = errorMessage(err)
  } finally {
    assistant.pending = false
    busy.value = false
    await scrollToLatest()
  }
}

function extractContent(data: unknown) {
  if (!data || typeof data !== 'object') return ''
  const choices = (data as Record<string, unknown>).choices
  if (!Array.isArray(choices) || !choices[0] || typeof choices[0] !== 'object') return ''
  const message = (choices[0] as Record<string, unknown>).message
  if (!message || typeof message !== 'object') return ''
  const content = (message as Record<string, unknown>).content
  return typeof content === 'string' ? content : ''
}

function resetSession() {
  if (busy.value) return
  messages.value = []
  error.value = ''
  copiedIndex.value = null
}

async function copyMessage(content: string) {
  try {
    await navigator.clipboard.writeText(content)
    copiedIndex.value = messages.value.findIndex(item => item.content === content)
  } catch {
    error.value = '当前浏览器不允许复制回答。'
  }
}

async function scrollToLatest() {
  await nextTick()
  if (messageList.value) messageList.value.scrollTop = messageList.value.scrollHeight
}

function handlePageAction(event: Event) {
  const detail = (event as CustomEvent<{ key?: string }>).detail
  if (detail?.key === 'chat') resetSession()
}

onMounted(() => window.addEventListener('admin-page-action', handlePageAction))
onBeforeUnmount(() => window.removeEventListener('admin-page-action', handlePageAction))
</script>
