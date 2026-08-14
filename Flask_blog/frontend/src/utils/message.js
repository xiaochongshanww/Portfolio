import messageManager, { MESSAGE_PRIORITY } from './messageManager';

// 智能消息系统 - 支持优先级和防堆叠
/**
 * @typedef {string | { message?: string, content?: string, duration?: number, icon?: string, showClose?: boolean }} MsgContent
 */

/**
 * 归一化消息参数：兼容字符串与对象两种调用形式。
 * @param {MsgContent} content
 * @param {object} [options]
 * @returns {object}
 */
function normalizeArgs(content, options) {
  if (typeof content === 'object' && content !== null) {
    return { ...content, ...options };
  }
  return { message: content, ...options };
}

export const message = {
  // 成功消息 - 低优先级
  /** @param {MsgContent} content @param {object} [options] */
  success: (content, options = {}) => {
    messageManager.show({ ...normalizeArgs(content, options), type: 'success', priority: MESSAGE_PRIORITY.SUCCESS });
  },
  
  // 错误消息 - 最高优先级
  /** @param {MsgContent} content @param {object} [options] */
  error: (content, options = {}) => {
    messageManager.show({ ...normalizeArgs(content, options), type: 'error', priority: MESSAGE_PRIORITY.CRITICAL });
  },
  
  // 警告消息 - 中高优先级  
  /** @param {MsgContent} content @param {object} [options] */
  warning: (content, options = {}) => {
    messageManager.show({ ...normalizeArgs(content, options), type: 'warning', priority: MESSAGE_PRIORITY.WARNING });
  },
  
  // 信息消息 - 最低优先级
  /** @param {MsgContent} content @param {object} [options] */
  info: (content, options = {}) => {
    messageManager.show({ ...normalizeArgs(content, options), type: 'info', priority: MESSAGE_PRIORITY.INFO });
  },
  
  // 通用方法
  /** @param {object} options */
  show: (options) => {
    messageManager.show(options);
  },
  
  // 清除所有消息
  clear: () => {
    messageManager.clear();
  },
  
  // 高级方法 - 直接指定优先级
  /** @param {MsgContent} content @param {object} [options] */
  critical: (content, options = {}) => {
    messageManager.show({ ...normalizeArgs(content, options), type: 'error', priority: MESSAGE_PRIORITY.CRITICAL });
  },
  
  // 批量消息测试方法 (开发时使用)
  testBatch: () => {
    console.log('🧪 测试批量消息处理');
    messageManager.info('编辑器初始化中...');
    messageManager.success('草稿数据加载完成');  
    messageManager.warning('未找到匹配的分类');
    messageManager.critical('网络连接失败');
    messageManager.info('自动保存已开启');
  }
};

// 导出优先级常量，供其他组件使用
export { MESSAGE_PRIORITY };

// 导出默认的智能消息方法
export default message;