<template>
  <div class="grid h-full min-h-[680px] grid-cols-[minmax(0,1fr)_340px] gap-5">
    <section class="panel flex min-h-0 flex-col">
      <div class="flex items-center justify-between border-b border-slate-200 p-4">
        <div>
          <h2 class="panel-title">问答验证</h2>
          <p class="muted mt-1">轻量验证检索链路；正式日常聊天建议继续使用 Open WebUI。</p>
        </div>
        <button class="btn" @click="answer = ''">清空</button>
      </div>
      <div class="min-h-0 flex-1 overflow-auto p-5">
        <div v-if="answer" class="max-w-5xl whitespace-pre-wrap rounded-md bg-slate-50 p-4 leading-7 text-slate-800">{{ answer }}</div>
        <div v-else class="flex h-full items-center justify-center text-slate-500">输入问题后发送。</div>
      </div>
      <form class="flex gap-2 border-t border-slate-200 p-4" @submit.prevent="send">
        <input v-model="question" class="field h-11 flex-1" placeholder="例如：抗震规范第 8.2.1 条是什么？">
        <button class="btn btn-primary h-11 px-6" :disabled="busy || !question.trim()">发送</button>
      </form>
    </section>

    <aside class="panel p-5">
      <h2 class="panel-title">请求参数</h2>
      <div class="mt-4 space-y-3">
        <label class="block text-sm">
          <span class="mb-1 block text-xs font-medium text-slate-500">模型</span>
          <input v-model="model" class="field" />
        </label>
        <label class="block text-sm">
          <span class="mb-1 block text-xs font-medium text-slate-500">Temperature</span>
          <input v-model.number="temperature" class="field" type="number" min="0" max="1" step="0.1" />
        </label>
      </div>
      <p v-if="error" class="mt-4 rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">{{ error }}</p>
    </aside>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { getApiKey } from '../api'

const question = ref('')
const answer = ref('')
const error = ref('')
const busy = ref(false)
const model = ref('mimo-v2.5')
const temperature = ref(0.2)

async function send() {
  busy.value = true
  error.value = ''
  answer.value = ''
  try {
    const key = getApiKey()
    const response = await fetch('/v1/chat/completions', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(key ? { Authorization: `Bearer ${key}` } : {}),
      },
      body: JSON.stringify({
        model: model.value,
        temperature: temperature.value,
        stream: false,
        messages: [{ role: 'user', content: question.value }],
      }),
    })
    if (!response.ok) throw new Error(`${response.status} ${response.statusText}`)
    const data = await response.json()
    answer.value = data.choices?.[0]?.message?.content || JSON.stringify(data, null, 2)
  } catch (err: any) {
    error.value = err.message || String(err)
  } finally {
    busy.value = false
  }
}
</script>
