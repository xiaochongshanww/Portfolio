// Vditor配置修复：避免外部CDN依赖
// 在VditorEditor.vue中使用此配置

const vditorConfig = {
  // 基础配置
  height: 400,
  mode: 'wysiwyg',
  theme: 'classic',
  
  // 关键配置：禁用外部资源加载
  cdn: '/node_modules/vditor',  // 使用本地Vditor资源
  
  // 国际化配置
  lang: 'zh_CN',
  i18n: {
    // 直接内联中文配置，避免外部加载
    zh_CN: {
      'edit': '编辑',
      'preview': '预览',
      'both': '双栏',
      'upload': '上传',
      'record': '录音',
      'emoji': '表情',
      'headings': '标题',
      'bold': '粗体',
      'italic': '斜体',
      'strike': '删除线',
      'line': '分割线',
      'quote': '引用',
      'list': '无序列表',
      'ordered-list': '有序列表',
      'check': '任务列表',
      'code': '代码块',
      'inline-code': '行内代码',
      'link': '链接',
      'table': '表格',
      'undo': '撤销',
      'redo': '重做',
      'fullscreen': '全屏',
      'edit-mode': '编辑模式',
      'content-theme': '内容主题',
      'code-theme': '代码主题',
      'export': '导出',
      'outline': '大纲',
      'devtools': '开发工具',
    }
  },
  
  // 上传配置
  upload: {
    url: '/api/v1/upload/image',
    multiple: false,
    accept: 'image/*',
    headers: {
      'Authorization': `Bearer ${localStorage.getItem('access_token') || ''}`
    }
  },
  
  // 工具栏配置
  toolbar: [
    'headings',
    'bold', 
    'italic',
    'strike',
    '|',
    'line',
    'quote',
    '|', 
    'list',
    'ordered-list',
    'check',
    '|',
    'code',
    'inline-code',
    'link',
    'upload',
    '|',
    'undo',
    'redo',
    'fullscreen'
  ],
  
  // 缓存配置
  cache: {
    enable: false  // 禁用缓存避免外部请求
  },
  
  // 预览配置
  preview: {
    delay: 500,
    mode: 'both',
    url: '/api/v1/preview/markdown',
    parse: (element) => {
      // 本地预览解析，不依赖外部服务
      return element;
    }
  }
};

export default vditorConfig;