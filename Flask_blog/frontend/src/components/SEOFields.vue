<template>
  <div class="seo-fields">
    <el-form-item label="SEO 标题" prop="seo_title">
      <el-input
        :model-value="seoTitle"
        placeholder="自定义搜索引擎显示的标题（可选）"
        :maxlength="70"
        show-word-limit
        clearable
        @update:model-value="$emit('update:seoTitle', $event)"
      >
        <template #prepend>
          <el-icon><Search /></el-icon>
        </template>
      </el-input>
    </el-form-item>

    <el-form-item label="SEO 描述" prop="seo_desc">
      <el-input
        :model-value="seoDesc"
        type="textarea"
        :rows="3"
        placeholder="自定义搜索引擎显示的描述（可选）"
        :maxlength="200"
        show-word-limit
        clearable
        @update:model-value="$emit('update:seoDesc', $event)"
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
