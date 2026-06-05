<template>
  <div class="seo-fields">
    <el-form-item label="SEO 标题" prop="seo_title">
      <el-input
        :model-value="seoTitle"
        @update:model-value="$emit('update:seoTitle', $event)"
        placeholder="自定义搜索引擎显示的标题（可选）"
        :maxlength="70"
        show-word-limit
        clearable
      >
        <template #prepend>
          <el-icon><Search /></el-icon>
        </template>
      </el-input>
    </el-form-item>

    <el-form-item label="SEO 描述" prop="seo_desc">
      <el-input
        :model-value="seoDesc"
        @update:model-value="$emit('update:seoDesc', $event)"
        type="textarea"
        :rows="3"
        placeholder="自定义搜索引擎显示的描述（可选）"
        :maxlength="200"
        show-word-limit
        clearable
      />
    </el-form-item>
  </div>
</template>

<script setup lang="ts">
import { Search } from '@element-plus/icons-vue'

defineProps<{
  seoTitle: string
  seoDesc: string
}>()

defineEmits<{
  'update:seoTitle': [value: string]
  'update:seoDesc': [value: string]
}>()
</script>
