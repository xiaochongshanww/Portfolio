import { ElMessage } from 'element-plus';

// 消息优先级常量
export const MESSAGE_PRIORITY = {
  CRITICAL: 4,    // 🚨 阻塞性错误
  WARNING: 3,     // ⚠️ 功能受限警告
  SUCCESS: 2,     // ✅ 操作成功确认
  INFO: 1         // ℹ️ 状态信息
};

/** @typedef {{ content: string, priority: number, type: string, timestamp: number, icon?: string, showClose?: boolean, duration?: number, details?: string[], merged?: boolean, instance?: any, close?: () => void }} MsgInfo */
/** @typedef {{ message?: string, content?: string, priority?: number, type?: string, showClose?: boolean, duration?: number, icon?: string }} ShowOptions */

// 消息类型配置
/** @type {Record<number, { duration: number, maxCount: number, color: string, showClose: boolean }>} */
const MESSAGE_CONFIG = {
  [MESSAGE_PRIORITY.CRITICAL]: {
    duration: 8000,
    maxCount: 99,  // 不限制关键错误数量
    color: '#dc2626',
    showClose: true
  },
  [MESSAGE_PRIORITY.WARNING]: {
    duration: 5000,
    maxCount: 2,   // 最多2条警告
    color: '#d97706',
    showClose: true
  },
  [MESSAGE_PRIORITY.SUCCESS]: {
    duration: 3000,
    maxCount: 1,   // 最多1条成功消息
    color: '#059669',
    showClose: false
  },
  [MESSAGE_PRIORITY.INFO]: {
    duration: 2500,
    maxCount: 1,   // 最多1条信息消息
    color: '#2563eb',
    showClose: false
  }
};

class MessageManager {
  constructor() {
    // 活跃消息队列，按优先级分组
    /** @type {Record<number, MsgInfo[]>} */
    this.activeMessages = {
      [MESSAGE_PRIORITY.CRITICAL]: [],
      [MESSAGE_PRIORITY.WARNING]: [],
      [MESSAGE_PRIORITY.SUCCESS]: [],
      [MESSAGE_PRIORITY.INFO]: []
    };
    
    // 消息去重缓存 (内容 -> 时间戳)
    /** @type {Map<string, number>} */
    this.messageCache = new Map();
    
    // 批处理缓冲区
    /** @type {MsgInfo[]} */
    this.batchBuffer = [];
    /** @type {ReturnType<typeof setTimeout> | null} */
    this.batchTimeout = null;
    
    // 默认消息配置
    /** @type {{ customClass: string, offset: number, center: boolean }} */
    this.defaultConfig = {
      customClass: 'enhanced-message',
      offset: 90,
      center: false
    };
  }

  /**
   * 显示消息 - 主要入口方法
   * @param {string | ShowOptions} options
   */
  show(options) {
    const message = this._normalizeMessage(options);
    
    // 检查重复消息
    if (this._isDuplicateMessage(message)) {
      console.log('🔄 重复消息已忽略:', message.content);
      return null;
    }
    
    // 加入批处理缓冲区
    this.batchBuffer.push(message);
    
    // 如果是关键消息，立即处理
    if (message.priority === MESSAGE_PRIORITY.CRITICAL) {
      this._flushBatch();
      return;
    }
    
    // 延迟批处理，允许同时到达的消息一起处理
    this._scheduleBatchProcess();
  }

  /**
   * 标准化消息对象
   * @param {string | ShowOptions} options
   * @returns {MsgInfo}
   */
  _normalizeMessage(options) {
    if (typeof options === 'string') {
      return {
        content: options,
        priority: MESSAGE_PRIORITY.INFO,
        type: 'info',
        timestamp: Date.now()
      };
    }
    
    return {
      content: /** @type {string} */ (options.message || options.content),
      priority: options.priority || MESSAGE_PRIORITY.INFO,
      type: options.type || 'info',
      timestamp: Date.now(),
      showClose: options.showClose,
      duration: options.duration,
      icon: options.icon || this._getDefaultIcon(options.type)
    };
  }

  /**
   * 获取默认图标
   * @param {string | undefined} type
   * @returns {string}
   */
  _getDefaultIcon(type) {
    /** @type {Record<string, string>} */
    const icons = {
      'error': '🚨',
      'warning': '⚠️',
      'success': '✅',
      'info': 'ℹ️'
    };
    return icons[type ?? ''] || '';
  }

  /**
   * 检查重复消息
   * @param {MsgInfo} message
   * @returns {boolean}
   */
  _isDuplicateMessage(message) {
    const cacheKey = message.content;
    const lastTime = this.messageCache.get(cacheKey);
    const now = message.timestamp;
    
    // 如果3秒内有相同内容的消息，认为是重复
    if (lastTime && (now - lastTime) < 3000) {
      return true;
    }
    
    this.messageCache.set(cacheKey, now);
    return false;
  }

  /**
   * 调度批处理
   */
  _scheduleBatchProcess() {
    if (this.batchTimeout) {
      clearTimeout(this.batchTimeout);
    }
    
    // 200ms 内的消息会被批处理
    this.batchTimeout = setTimeout(() => {
      this._flushBatch();
    }, 200);
  }

  /**
   * 处理批处理缓冲区
   */
  _flushBatch() {
    if (this.batchBuffer.length === 0) return;
    
    console.log('📦 处理消息批次，数量:', this.batchBuffer.length);
    
    // 按优先级排序
    const sortedMessages = [...this.batchBuffer].sort((a, b) => b.priority - a.priority);
    
    // 检查是否需要合并相似消息
    const processedMessages = this._mergeSimilarMessages(sortedMessages);
    
    // 逐个处理消息
    processedMessages.forEach((message, index) => {
      // 高优先级消息立即显示，低优先级消息延迟显示避免堆叠
      const delay = message.priority >= MESSAGE_PRIORITY.WARNING ? 0 : index * 100;
      
      setTimeout(() => {
        this._displayMessage(message);
      }, delay);
    });
    
    // 清空缓冲区
    this.batchBuffer = [];
    this.batchTimeout = null;
  }

  /**
   * 合并相似消息
   * @param {MsgInfo[]} messages
   * @returns {MsgInfo[]}
   */
  _mergeSimilarMessages(messages) {
    /** @type {Record<string, MsgInfo[]>} */
    const grouped = {};
    
    messages.forEach(message => {
      // 按类型和优先级分组
      const key = `${message.type}-${message.priority}`;
      
      if (!grouped[key]) {
        grouped[key] = [];
      }
      grouped[key].push(message);
    });
    
    /** @type {MsgInfo[]} */
    const result = [];
    
    Object.values(grouped).forEach(group => {
      if (group.length === 1) {
        result.push(group[0]);
      } else if (group.length > 1) {
        // 合并多条相似消息
        const merged = this._createMergedMessage(group);
        result.push(merged);
      }
    });
    
    return result;
  }

  /**
   * 创建合并消息
   * @param {MsgInfo[]} messages
   * @returns {MsgInfo}
   */
  _createMergedMessage(messages) {
    const first = messages[0];
    const count = messages.length;
    
    // 如果是成功消息，只显示最新的一条
    if (first.priority === MESSAGE_PRIORITY.SUCCESS) {
      return messages[messages.length - 1];
    }
    
    // 其他情况创建合并消息
    return {
      ...first,
      content: `${first.icon} ${count}条${this._getPriorityName(first.priority)}消息`,
      details: messages.map(m => m.content),
      merged: true,
      timestamp: Math.max(...messages.map(m => m.timestamp))
    };
  }

  /**
   * 获取优先级名称
   * @param {number} priority
   * @returns {string}
   */
  _getPriorityName(priority) {
    /** @type {Record<number, string>} */
    const names = {
      [MESSAGE_PRIORITY.CRITICAL]: '错误',
      [MESSAGE_PRIORITY.WARNING]: '警告',
      [MESSAGE_PRIORITY.SUCCESS]: '成功',
      [MESSAGE_PRIORITY.INFO]: '信息'
    };
    return names[priority] || '消息';
  }

  /**
   * 显示单条消息
   * @param {MsgInfo} message
   */
  _displayMessage(message) {
    const config = MESSAGE_CONFIG[message.priority];
    const activeList = this.activeMessages[message.priority];
    
    // 检查是否超过最大数量限制
    if (activeList.length >= config.maxCount) {
      // 移除最旧的消息
      const oldestMessage = activeList.shift();
      if (oldestMessage && oldestMessage.close) {
        oldestMessage.close();
      }
      console.log('📤 移除旧消息为新消息腾出空间');
    }
    
    // 构建 ElMessage 配置
    const messageConfig = {
      ...this.defaultConfig,
      message: message.merged ? this._formatMergedMessage(message) : message.content,
      type: message.type,
      duration: message.duration || config.duration,
      showClose: message.showClose !== undefined ? message.showClose : config.showClose,
      dangerouslyUseHTMLString: message.merged,
      onClose: () => this._onMessageClose(message, activeList)
    };
    
    // 显示消息
    const instance = ElMessage(/** @type {any} */ (messageConfig));
    message.instance = instance;
    
    // 添加到活跃列表
    activeList.push(message);
    
    console.log(`📨 显示${this._getPriorityName(message.priority)}消息:`, message.content);
  }

  /**
   * 格式化合并消息
   * @param {MsgInfo} message
   * @returns {string}
   */
  _formatMergedMessage(message) {
    const detailsList = (message.details || []).map(detail => `• ${detail}`).join('<br>');
    
    return `
      <div style="line-height: 1.6;">
        <div style="font-weight: 600; margin-bottom: 8px;">
          ${message.content}
        </div>
        <div style="font-size: 13px; opacity: 0.9; padding-left: 12px;">
          ${detailsList}
        </div>
      </div>
    `;
  }

  /**
   * 消息关闭回调
   * @param {MsgInfo} message
   * @param {MsgInfo[]} activeList
   */
  _onMessageClose(message, activeList) {
    const index = activeList.indexOf(message);
    if (index > -1) {
      activeList.splice(index, 1);
    }
  }

  /**
   * 便捷方法
   * @param {string} content
   * @param {Object} [options]
   */
  critical(content, options = {}) {
    this.show({
      ...options,
      message: content,
      type: 'error',
      priority: MESSAGE_PRIORITY.CRITICAL
    });
  }

  /**
   * @param {string} content
   * @param {Object} [options]
   */
  warning(content, options = {}) {
    this.show({
      ...options,
      message: content,
      type: 'warning',  
      priority: MESSAGE_PRIORITY.WARNING
    });
  }

  /**
   * @param {string} content
   * @param {Object} [options]
   */
  success(content, options = {}) {
    this.show({
      ...options,
      message: content,
      type: 'success',
      priority: MESSAGE_PRIORITY.SUCCESS
    });
  }

  /**
   * @param {string} content
   * @param {Object} [options]
   */
  info(content, options = {}) {
    this.show({
      ...options,
      message: content,
      type: 'info',
      priority: MESSAGE_PRIORITY.INFO
    });
  }

  /**
   * 清除所有消息
   */
  clear() {
    Object.values(this.activeMessages).forEach(list => {
      list.forEach(message => {
        if (message.instance && message.instance.close) {
          message.instance.close();
        }
      });
      list.length = 0;
    });
    
    this.messageCache.clear();
    this.batchBuffer = [];
    
    if (this.batchTimeout) {
      clearTimeout(this.batchTimeout);
      this.batchTimeout = null;
    }
  }
}

// 创建全局单例
const messageManager = new MessageManager();

export default messageManager;
