import { ref } from 'vue';

/**
 * 文章表单状态与校验(05 §24/§25)
 * 从 NewArticle 抽出的纯表单逻辑:字段模型、逐字段/整表校验、错误清理。
 */
export function useArticleForm() {
  /** @type {import('vue').Ref<{ title: string, content_md: string, tags_raw: string, seo_title: string, seo_desc: string, slug: string, summary: string, featured_image: string, featured_focal_x: number | null, featured_focal_y: number | null, enable_schedule: boolean, scheduled_at: string, category_id: number | null }>} */
  const form = ref({
    title: '',
    content_md: '',
    tags_raw: '',
    seo_title: '',
    seo_desc: '',
    slug: '',
    summary: '',
    featured_image: '',
    featured_focal_x: null,
    featured_focal_y: null,
    enable_schedule: false,
    scheduled_at: '',
    category_id: null
  });

  /** @type {import('vue').Ref<Record<string, string>>} */
  const formErrors = ref({});
  const showValidation = ref(false);

  const validationRules = {
    title: [
      { required: true, message: '请输入文章标题', trigger: 'blur' },
      { min: 2, max: 200, message: '标题长度应在2-200个字符之间', trigger: 'blur' }
    ],
    content_md: [
      { required: true, message: '请输入文章内容', trigger: 'blur' },
      { min: 1, message: '请输入文章内容', trigger: 'blur' }
    ],
    summary: [
      { max: 500, message: '摘要不能超过500个字符', trigger: 'blur' }
    ],
    seo_title: [
      { max: 60, message: 'SEO标题不能超过60个字符', trigger: 'blur' }
    ],
    seo_desc: [
      { max: 160, message: 'Meta描述不能超过160个字符', trigger: 'blur' }
    ],
    slug: [
      { pattern: /^[a-zA-Z0-9-_]+$/, message: 'Slug只能包含字母、数字、连字符和下划线', trigger: 'blur' }
    ],
    featured_image: [
      {
        pattern: /^(https?:\/\/.+\.(jpg|jpeg|png|gif|webp)(\?.+)?$|\/uploads\/.+\.(jpg|jpeg|png|gif|webp)(\?.+)?$)/i,
        message: '请输入有效的图片URL或上传图片',
        trigger: 'blur'
      }
    ],
    category_id: [
      { type: 'number', message: '请选择有效的分类', trigger: 'change' }
    ]
  };

  /** @param {string} fieldName @param {unknown} value */
  function validateField(fieldName, value) {
    const rules = /** @type {Array<{ required?: boolean, min?: number, max?: number, message?: string, trigger?: string, pattern?: RegExp, type?: string }>} */ ((/** @type {Record<string, unknown>} */ (validationRules))[fieldName]);
    if (!rules) return null;

    for (const rule of rules) {
      if (rule.required && (!value || !value.toString().trim())) {
        return rule.message;
      }

      if (rule.min && value && value.toString().length < rule.min) {
        return rule.message;
      }

      if (rule.max && value && value.toString().length > rule.max) {
        return rule.message;
      }

      if (rule.pattern && value && !rule.pattern.test(value.toString())) {
        return rule.message;
      }
    }

    return null;
  }

  function validateForm() {
    /** @type {Record<string, string>} */
    const errors = {};
    let hasErrors = false;

    Object.keys(validationRules).forEach(fieldName => {
      /** @type {Record<string, unknown>} */
      const formData = form.value;
      const value = formData[fieldName];
      const error = validateField(fieldName, value);
      if (error) {
        errors[fieldName] = error;
        hasErrors = true;
      }
    });

    // 特殊验证：定时发布
    if (form.value.enable_schedule && !form.value.scheduled_at) {
      errors.scheduled_at = '请选择发布时间';
      hasErrors = true;
    }

    if (form.value.enable_schedule && form.value.scheduled_at) {
      const scheduleTime = new Date(form.value.scheduled_at);
      const now = new Date();
      if (scheduleTime <= now) {
        errors.scheduled_at = '发布时间必须大于当前时间';
        hasErrors = true;
      }
    }

    formErrors.value = errors;
    return !hasErrors;
  }

  /** @param {string} fieldName */
  function clearFieldError(fieldName) {
    if (formErrors.value[fieldName]) {
      delete formErrors.value[fieldName];
      formErrors.value = { ...formErrors.value };
    }
  }

  // 实时验证
  /** @param {string} fieldName @param {unknown} value */
  function handleFieldBlur(fieldName, value) {
    if (showValidation.value) {
      const error = validateField(fieldName, value);
      if (error) {
        formErrors.value[fieldName] = error;
      } else {
        clearFieldError(fieldName);
      }
    }
  }

  return {
    form,
    formErrors,
    showValidation,
    validationRules,
    validateField,
    validateForm,
    clearFieldError,
    handleFieldBlur,
  };
}
