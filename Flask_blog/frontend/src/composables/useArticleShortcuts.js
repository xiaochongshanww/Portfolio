import { ElMessage } from 'element-plus';
import message from '../utils/message';

/**
 * 文章编辑器键盘快捷键(05 §25 配套)
 * 从 NewArticle 抽出:Ctrl+S 保存、Ctrl+Enter 发布、Ctrl+K/F1 帮助、Esc 清错。
 *
 * @param {Object} deps
 * @param {() => void} deps.saveDraft
 * @param {() => void} deps.submit
 * @param {import('vue').Ref<boolean>} deps.loading
 * @param {import('vue').Ref<string>} deps.error 页面级错误信息(Esc 清除)
 */
export function useArticleShortcuts({ saveDraft, submit, loading, error }) {
  // 显示快捷键帮助
  function showKeyboardShortcuts() {
    const shortcuts = [
      { key: 'Ctrl+S', desc: '保存草稿到本地' },
      { key: 'Ctrl+Enter', desc: '发布文章' },
      { key: 'Ctrl+Shift+I', desc: '上传封面图片' },
      { key: 'Ctrl+Shift+L', desc: '在编辑器中插入链接' },
      { key: 'Ctrl+K / F1', desc: '显示此帮助' },
      { key: 'Escape', desc: '清除错误信息' }
    ];

    const shortcutText = shortcuts.map(s => `${s.key}: ${s.desc}`).join('\n');

    ElMessage({
      message: `键盘快捷键:\n\n${shortcutText}`,
      type: 'info',
      duration: 0,
      showClose: true,
      dangerouslyUseHTMLString: false,
      customClass: 'keyboard-shortcuts-message'
    });
  }

  /** @param {KeyboardEvent} e */
  function handleKeyDown(e) {
    // Ctrl/Cmd 组合键
    const isCtrlOrCmd = e.ctrlKey || e.metaKey;

    if (isCtrlOrCmd) {
      switch (e.key.toLowerCase()) {
        case 's':
          // Ctrl+S: 保存草稿
          e.preventDefault();
          saveDraft();
          break;

        case 'enter':
          // Ctrl+Enter: 发布文章
          e.preventDefault();
          if (!loading.value) {
            submit();
          }
          break;

        case 'k':
          // Ctrl+K: 显示快捷键帮助
          e.preventDefault();
          showKeyboardShortcuts();
          break;

        case 'i':
          // Ctrl+I: 插入图片
          if (e.shiftKey) {
            e.preventDefault();
            // 触发图片上传
            /** @type {HTMLElement | null} */
            const uploadInput = document.querySelector('.cover-uploader input[type="file"]');
            if (uploadInput) {
              uploadInput.click();
            }
          }
          break;

        case 'l':
          // Ctrl+L: 插入链接
          if (e.shiftKey) {
            e.preventDefault();
            // 聚焦到编辑器区域
            /** @type {HTMLElement | null} */
            const editorElement = document.querySelector('.editor-content');
            if (editorElement) {
              editorElement.focus();
              message.info('已聚焦到编辑器，请使用编辑器工具栏插入链接');
            }
          }
          break;

        case '/':
          // Ctrl+/: 切换预览模式
          e.preventDefault();
          message.info('预览请使用页头上方的「预览」按钮');
          break;
      }
    }

    // 其他快捷键
    switch (e.key) {
      case 'Escape':
        // ESC: 清除错误信息
        if (error.value) {
          error.value = '';
        }
        break;

      case 'F1':
        // F1: 显示帮助
        e.preventDefault();
        showKeyboardShortcuts();
        break;
    }
  }

  return { handleKeyDown, showKeyboardShortcuts };
}
