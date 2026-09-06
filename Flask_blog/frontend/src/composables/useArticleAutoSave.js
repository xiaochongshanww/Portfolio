import { ref } from 'vue';
import { nextTick } from 'vue';
import { ElMessageBox } from 'element-plus';
import message from '../utils/message';

/**
 * 文章自动保存与本地草稿(05 §25 Save Draft)
 * 从 NewArticle 抽出:防抖自动保存、草稿持久化/清理/恢复、离开页守卫状态。
 *
 * @typedef {import('../views/NewArticle.vue').ArticleForm} ArticleForm
 * @param {{ form: import('vue').Ref<ArticleForm>, blockEditorRef: import('vue').Ref<{ syncContent?: () => string, setContent?: (content: string) => void } | null> }} deps
 */
export function useArticleAutoSave({ form, blockEditorRef }) {
  const autoSaving = ref(false);
  /** @type {import('vue').Ref<Date | null>} */
  const lastSaveTime = ref(null);
  /** @type {import('vue').Ref<ReturnType<typeof setTimeout> | null>} */
  const autoSaveInterval = ref(null);
  const hasUnsavedChanges = ref(false);
  const isRestoringDraft = ref(false); // 标记是否正在恢复草稿
  const AUTOSAVE_DELAY = 3000; // 3秒后自动保存

  // 格式化保存时间
  /** @param {Date | string | null} time */
  function formatSaveTime(time) {
    if (!time) return '';

    const now = new Date();
    const diff = now.getTime() - new Date(time).getTime();
    const minutes = Math.floor(diff / (1000 * 60));
    const hours = Math.floor(diff / (1000 * 60 * 60));

    if (minutes < 1) return '刚刚';
    if (minutes < 60) return `${minutes}分钟前`;
    if (hours < 24) return `${hours}小时前`;

    const date = new Date(time);
    return date.toLocaleDateString() + ' ' + date.toLocaleTimeString();
  }

  // 保存草稿
  async function saveDraft() {
    try {
      autoSaving.value = true;

      // 检查必要字段
      if (!form.value.title?.trim() && !form.value.content_md?.trim()) {
        message.warning('请至少填写标题或内容后再保存草稿');
        return;
      }

      // 构建草稿数据
      /** @type {Record<string, unknown>} */
      const draftData = {
        title: form.value.title?.trim() || '未命名草稿',
        content_md: form.value.content_md || '',
        summary: form.value.summary?.trim() || '',
        featured_image: form.value.featured_image?.trim() || '',
        tags_raw: form.value.tags_raw?.trim() || '',
        seo_title: form.value.seo_title?.trim() || '',
        seo_desc: form.value.seo_desc?.trim() || '',
        slug: form.value.slug?.trim() || '',
        status: 'draft' // 标记为草稿状态
      };

      // 焦点坐标
      if (form.value.featured_focal_x != null && form.value.featured_focal_y != null) {
        draftData.featured_focal_x = form.value.featured_focal_x;
        draftData.featured_focal_y = form.value.featured_focal_y;
      }

      // 保存到本地存储
      const draftKey = 'article_draft_' + Date.now();
      localStorage.setItem(draftKey, JSON.stringify({
        ...draftData,
        savedAt: new Date().toISOString(),
        id: draftKey
      }));

      // 清理旧草稿（保留最近5个）
      cleanupOldDrafts();

      lastSaveTime.value = new Date();
      hasUnsavedChanges.value = false;

      message.success('💾 草稿已保存到本地');

    } catch (e) {
      console.error('Draft save error:', e);
      message.critical('草稿保存失败');
    } finally {
      autoSaving.value = false;
    }
  }

  // 清理旧草稿
  function cleanupOldDrafts() {
    try {
      const draftKeys = Object.keys(localStorage).filter(key => key.startsWith('article_draft_'));
      if (draftKeys.length > 5) {
        // 按时间排序，删除最旧的
        const draftsWithTime = draftKeys.map(key => {
          const draft = JSON.parse(localStorage.getItem(key) || '{}');
          return { key, savedAt: draft.savedAt || '1970-01-01' };
        }).sort((a, b) => new Date(b.savedAt).getTime() - new Date(a.savedAt).getTime());

        // 删除超过5个的旧草稿
        draftsWithTime.slice(5).forEach(draft => {
          localStorage.removeItem(draft.key);
        });
      }
    } catch (e) {
      console.error('Cleanup drafts error:', e);
    }
  }

  // 自动保存功能
  function triggerAutoSave() {
    // 如果正在恢复草稿，忽略触发
    if (isRestoringDraft.value) {
      return;
    }

    // 清除之前的定时器
    if (autoSaveInterval.value) {
      clearTimeout(autoSaveInterval.value);
    }

    // 标记有未保存的更改
    hasUnsavedChanges.value = true;

    // 设置新的定时器
    autoSaveInterval.value = setTimeout(() => {
      if (hasUnsavedChanges.value && !isRestoringDraft.value) {
        saveDraft();
      }
    }, AUTOSAVE_DELAY);
  }

  // 恢复草稿
  async function loadLatestDraft() {
    try {
      const draftKeys = Object.keys(localStorage).filter(key => key.startsWith('article_draft_'));
      if (draftKeys.length === 0) return;

      // 找到最新的草稿
      const latestDraftKey = draftKeys.reduce((latest, key) => {
        const current = JSON.parse(localStorage.getItem(key) || '{}');
        const latestData = JSON.parse(localStorage.getItem(latest) || '{}');
        return new Date(current.savedAt || 0) > new Date(latestData.savedAt || 0) ? key : latest;
      });

      const draftData = JSON.parse(localStorage.getItem(latestDraftKey) || '{}');
      const saveTime = new Date(draftData.savedAt);
      const now = new Date();
      const hoursDiff = (now.getTime() - saveTime.getTime()) / (1000 * 60 * 60);

      // 如果草稿是24小时内的，显示统一的卡片对话框询问是否恢复
      if (hoursDiff < 24) {
        // 添加草稿对话框样式
        const styleId = 'draft-dialog-style';
        if (!document.getElementById(styleId)) {
          const style = document.createElement('style');
          style.id = styleId;
          style.textContent = `
            .draft-restore-dialog.el-message-box {
              position: fixed !important;
              top: 50% !important;
              left: 50% !important;
              transform: translate(-50%, -50%) !important;
              margin: 0 !important;
              z-index: 3000 !important;
              background: #ffffff !important;
              border-radius: 16px !important;
              box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04) !important;
              border: 1px solid #f1f5f9 !important;
              width: 440px !important;
              max-width: 90vw !important;
              padding: 0 !important;
              overflow: hidden !important;
            }
            .draft-restore-dialog.el-message-box .el-message-box__header {
              background: #f1f5f9;
              padding: 32px 24px 16px !important;
              text-align: center !important;
              border-bottom: 1px solid #e5e7eb !important;
            }
            .draft-restore-dialog.el-message-box .el-message-box__title {
              font-size: 24px !important;
              font-weight: 700 !important;
              color: #1f2937 !important;
            }
            .draft-restore-dialog.el-message-box .el-message-box__content {
              padding: 24px 32px !important;
              background: #ffffff !important;
            }
            .draft-restore-dialog.el-message-box .el-message-box__message {
              font-size: 16px !important;
              line-height: 1.6 !important;
              color: #374151 !important;
              text-align: left !important;
              white-space: pre-line !important;
            }
            .draft-restore-dialog.el-message-box .el-message-box__btns {
              padding: 0 32px 32px !important;
              background: #ffffff !important;
              display: flex !important;
              justify-content: center !important;
              gap: 16px !important;
            }
            .draft-restore-dialog.el-message-box .dialog-restore-btn {
              background: #f1f5f9;
              border: none !important;
              border-radius: 12px !important;
              color: #ffffff !important;
              font-weight: 600 !important;
              padding: 14px 28px !important;
              font-size: 15px !important;
              min-width: 120px !important;
              box-shadow: 0 4px 12px rgba(59, 130, 246, 0.3) !important;
            }
            .draft-restore-dialog.el-message-box .dialog-skip-btn {
              background: #f8fafc !important;
              border: 1px solid #e2e8f0 !important;
              border-radius: 12px !important;
              color: #64748b !important;
              font-weight: 500 !important;
              padding: 14px 28px !important;
              font-size: 15px !important;
              min-width: 120px !important;
            }
          `;
          document.head.appendChild(style);
        }

        try {
          await ElMessageBox.confirm(
            `发现 ${Math.floor(hoursDiff)} 小时前的草稿\n\n标题：${draftData.title || '未命名草稿'}\n内容：${(draftData.content_md || '').substring(0, 100)}${(draftData.content_md || '').length > 100 ? '...' : ''}\n\n是否恢复这个草稿继续编辑？`,
            '📝 发现草稿',
            {
              confirmButtonText: '恢复草稿',
              cancelButtonText: '跳过',
              type: 'info',
              center: true,
              customClass: 'draft-restore-dialog',
              distinguishCancelAndClose: true,
              showClose: false,
              closeOnClickModal: false,
              closeOnPressEscape: true,
              showCancelButton: true,
              cancelButtonClass: 'dialog-skip-btn',
              confirmButtonClass: 'dialog-restore-btn'
            }
          );

          try {
            // 立即设置恢复标志
            isRestoringDraft.value = true;
            hasUnsavedChanges.value = false;

            // 清除任何自动保存定时器
            if (autoSaveInterval.value) {
              clearTimeout(autoSaveInterval.value);
              autoSaveInterval.value = null;
            }

            // 同步恢复基础表单数据（不包含content_md，避免触发编辑器更新）
            Object.keys(draftData).forEach(key => {
              /** @type {Record<string, unknown>} */
              const formData = form.value;
              if (key !== 'savedAt' && key !== 'id' && key !== 'status' &&
                  key !== 'content_md' && formData.hasOwnProperty(key)) {
                formData[key] = draftData[key];
              }
            });

            // 单独处理content_md，使用更安全的方式
            await nextTick();

            // 使用Vue的批量更新机制，避免响应式冲突
            await nextTick(() => {
              // 在下一个微任务中安全地更新content_md
              form.value.content_md = draftData.content_md || '';
            });

            // 等待两个渲染周期确保状态完全稳定
            await nextTick();
            await nextTick();

            // 将编辑器内容设置延迟到宏任务队列，完全避开Vue的更新周期
            setTimeout(async () => {
              try {
                // 再次确认编辑器引用存在且有效
                if (blockEditorRef.value &&
                    typeof blockEditorRef.value.setContent === 'function') {

                  // 在设置内容前再等待一个tick，确保DOM完全稳定
                  await nextTick();

                  blockEditorRef.value.setContent(draftData.content_md || '');
                } else {
                  console.warn('编辑器引用无效或组件已卸载，跳过内容设置');
                }
              } catch (e) {
                console.warn('设置编辑器内容失败:', e);
                // 不影响整个恢复流程
              }
            }, 100);

            // 最终状态重置 - 使用更长延迟确保编辑器稳定
            setTimeout(() => {
              isRestoringDraft.value = false;
              hasUnsavedChanges.value = false;

              // 显示成功消息，并提示用户现在可以安全导航
              message.success('📝 草稿已恢复！现在可以安全导航到其他页面。');
            }, 1000);

          } catch (error) {
            const err = /** @type {{ message?: string }} */ (error);

            // 检查是否是Vue响应式系统的错误（这种情况下数据可能已经恢复成功）
            const isVueRenderError = err.message && err.message.includes('__vnode');

            if (isVueRenderError) {
              // 延迟检查恢复状态，避免立即显示错误
              setTimeout(() => {
                // 检查草稿数据是否已实际恢复
                const hasContent = form.value.title || form.value.content_md;
                if (hasContent) {
                  // 正常完成恢复流程
                  isRestoringDraft.value = false;
                  hasUnsavedChanges.value = false;
                  message.success({
                    message: '📝 草稿已恢复！',
                    duration: 3000
                  });
                } else {
                  // 真正的恢复失败
                  isRestoringDraft.value = false;
                  hasUnsavedChanges.value = false;
                  message.critical('草稿恢复失败，请重试');
                }
              }, 500);
            } else {
              // 其他类型的错误
              isRestoringDraft.value = false;
              hasUnsavedChanges.value = false;
              message.critical('草稿恢复失败，请重试');
            }
          }

        } catch (action) {
          // 用户选择跳过或关闭：保持安静
        }
      }
    } catch (e) {
      console.error('Load draft error:', e);
      // 确保状态重置，避免用户界面卡住
      if (isRestoringDraft.value) {
        isRestoringDraft.value = false;
        hasUnsavedChanges.value = false;
      }
    }
  }

  // 页面离开守卫(beforeunload 用)
  /** @param {BeforeUnloadEvent} e */
  function handleBeforeUnload(e) {
    // 如果正在恢复草稿，不阻止导航
    if (isRestoringDraft.value) {
      return;
    }

    if (hasUnsavedChanges.value) {
      e.preventDefault();
      e.returnValue = '您有未保存的更改，确定要离开页面吗？';
      return '您有未保存的更改，确定要离开页面吗？';
    }
  }

  return {
    autoSaving,
    lastSaveTime,
    autoSaveInterval,
    hasUnsavedChanges,
    isRestoringDraft,
    formatSaveTime,
    saveDraft,
    triggerAutoSave,
    cleanupOldDrafts,
    loadLatestDraft,
    handleBeforeUnload,
  };
}
