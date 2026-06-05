<template>
  <div class="tags-manager">
    <el-form-item label="文章标签">
      <div class="tags-selector">
        <el-select
          v-model="selected"
          multiple
          filterable
          allow-create
          default-first-option
          placeholder="选择或创建标签"
          class="tags-select"
          @change="onChange"
          :loading="loading"
        >
          <el-option
            v-for="tag in availableTags"
            :key="tag.id"
            :label="tag.name"
            :value="tag.name"
          >
            <span class="tag-option">
              <span class="tag-name">#{{ tag.name }}</span>
              <span class="tag-count" v-if="tag.article_count">({{ tag.article_count }})</span>
            </span>
          </el-option>
        </el-select>

        <div class="selected-tags" v-if="selected.length > 0">
          <el-tag
            v-for="tag in selected"
            :key="tag"
            closable
            @close="removeTag(tag)"
            class="selected-tag"
          >
            #{{ tag }}
          </el-tag>
        </div>

        <p class="tag-hint" v-if="!selected.length">
          从现有标签中选择或创建新标签，建议3-5个标签
        </p>
      </div>
    </el-form-item>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'

const props = defineProps<{
  modelValue: string[]
  availableTags?: { id: number; name: string; article_count?: number }[]
}>()

const emit = defineEmits<{
  'update:modelValue': [value: string[]]
}>()

const selected = ref<string[]>(props.modelValue || [])
const loading = ref(false)
const tags = ref<{ id: number; name: string; article_count?: number }[]>(props.availableTags || [])

onMounted(async () => {
  if (!tags.value.length) {
    loading.value = true
    try {
      const { API } = await import('@/api')
      const resp = await API.getTagsPublic?.() || await API.getTags?.()
      if (resp?.data?.data) {
        tags.value = resp.data.data.map((t: any) => ({ id: t.id, name: t.name, article_count: t.article_count }))
      } else if (resp?.data) {
        tags.value = Array.isArray(resp.data) ? resp.data : []
      }
    } catch (e) {
      console.error('Failed to load tags:', e)
    } finally {
      loading.value = false
    }
  }
})

function onChange(val: string[]) {
  selected.value = val
  emit('update:modelValue', val)
}

function removeTag(tag: string) {
  selected.value = selected.value.filter(t => t !== tag)
  emit('update:modelValue', selected.value)
}
</script>

<style scoped>
.tags-selector {
  width: 100%;
}
.tags-select {
  width: 100%;
}
.selected-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 12px;
}
.selected-tag {
  font-size: 13px;
}
.tag-option {
  display: flex;
  justify-content: space-between;
  width: 100%;
}
.tag-count {
  color: #999;
  font-size: 12px;
}
.tag-hint {
  color: #999;
  font-size: 12px;
  margin-top: 8px;
}
</style>
