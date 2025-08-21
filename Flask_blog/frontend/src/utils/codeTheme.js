// 全局代码主题管理器
import { ref, reactive } from 'vue';

// 主题配置
export const codeThemes = [
  { label: 'GitHub Dark', value: 'github-dark', preview: 'linear-gradient(45deg, #0d1117 0%, #161b22 100%)' },
  { label: 'GitHub Light', value: 'github-light', preview: 'linear-gradient(45deg, #ffffff 0%, #f6f8fa 100%)' },
  { label: 'VS Code Dark', value: 'vs-code-dark', preview: 'linear-gradient(45deg, #1e1e1e 0%, #252526 100%)' },
  { label: 'Atom One Dark', value: 'atom-one-dark', preview: 'linear-gradient(45deg, #282c34 0%, #21252b 100%)' },
  { label: 'Nord', value: 'nord', preview: 'linear-gradient(45deg, #2e3440 0%, #3b4252 100%)' },
];

// 全局主题状态
export const currentTheme = ref('github-dark');

// 主题颜色配置
export const getThemeColors = (theme) => {
  const themes = {
    'github-dark': {
      background: '#0d1117',
      color: '#f0f6fc',
      border: '#30363d',
      comment: '#8b949e',
      keyword: '#ff7b72',
      string: '#a5d6ff',
      function: '#d2a8ff',
      number: '#79c0ff',
      variable: '#ffa657',
    },
    'github-light': {
      background: '#ffffff',
      color: '#24292f',
      border: '#d0d7de',
      comment: '#6e7781',
      keyword: '#cf222e',
      string: '#0a3069',
      function: '#8250df',
      number: '#0550ae',
      variable: '#953800',
    },
    'vs-code-dark': {
      background: '#1e1e1e',
      color: '#d4d4d4',
      border: '#3e3e42',
      comment: '#6a9955',
      keyword: '#569cd6',
      string: '#ce9178',
      function: '#dcdcaa',
      number: '#b5cea8',
      variable: '#9cdcfe',
    },
    'atom-one-dark': {
      background: '#282c34',
      color: '#abb2bf',
      border: '#3e4451',
      comment: '#5c6370',
      keyword: '#c678dd',
      string: '#98c379',
      function: '#61afef',
      number: '#d19a66',
      variable: '#e06c75',
    },
    'nord': {
      background: '#2e3440',
      color: '#d8dee9',
      border: '#3b4252',
      comment: '#616e88',
      keyword: '#81a1c1',
      string: '#a3be8c',
      function: '#88c0d0',
      number: '#b48ead',
      variable: '#bf616a',
    }
  };
  
  return themes[theme] || themes['github-dark'];
};

// 动态更新主题样式
export const updateGlobalCodeTheme = (theme, targetContainer = 'body') => {
  const themeColors = getThemeColors(theme);
  const styleId = 'global-code-theme';
  let styleElement = document.getElementById(styleId);
  
  if (!styleElement) {
    styleElement = document.createElement('style');
    styleElement.id = styleId;
    document.head.appendChild(styleElement);
  }
  
  const cssContent = `
    /* 仅针对文章详情页的代码块主题 - ${theme} 主题 */
    
    /* 文章详情页代码块背景和边框 */
    .article-content pre {
      background: ${themeColors.background} !important;
      border-color: ${themeColors.border} !important;
    }
    
    .article-content pre code,
    .article-content .hljs {
      color: ${themeColors.color} !important;
    }
    
    /* 仅针对文章详情页的语法高亮颜色 */
    .article-content .hljs-comment,
    .article-content .hljs-quote {
      color: ${themeColors.comment} !important;
      font-style: italic !important;
    }
    
    .article-content .hljs-keyword,
    .article-content .hljs-selector-tag,
    .article-content .hljs-type {
      color: ${themeColors.keyword} !important;
    }
    
    .article-content .hljs-string,
    .article-content .hljs-regexp {
      color: ${themeColors.string} !important;
    }
    
    .article-content .hljs-class,
    .article-content .hljs-function,
    .article-content .hljs-title {
      color: ${themeColors.function} !important;
    }
    
    .article-content .hljs-number,
    .article-content .hljs-literal {
      color: ${themeColors.number} !important;
    }
    
    .article-content .hljs-variable,
    .article-content .hljs-template-variable,
    .article-content .hljs-params,
    .article-content .hljs-built_in {
      color: ${themeColors.variable} !important;
    }
  `;
  
  styleElement.textContent = cssContent;
};

// 切换主题
export const switchTheme = (theme) => {
  currentTheme.value = theme;
  localStorage.setItem('codeTheme', theme);
  updateGlobalCodeTheme(theme);
};

// 从 localStorage 加载主题
export const loadThemeFromStorage = () => {
  const savedTheme = localStorage.getItem('codeTheme');
  if (savedTheme && codeThemes.some(t => t.value === savedTheme)) {
    currentTheme.value = savedTheme;
    updateGlobalCodeTheme(savedTheme);
  } else {
    updateGlobalCodeTheme('github-dark');
  }
};

// 初始化主题
export const initTheme = () => {
  loadThemeFromStorage();
};