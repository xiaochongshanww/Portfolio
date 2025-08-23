import messageManager, { MESSAGE_PRIORITY } from './messageManager';

// 智能消息系统 - 支持优先级和防堆叠
export const message = {
  // 成功消息 - 低优先级
  success: (content, options = {}) => {
    messageManager.success(content, options);
  },
  
  // 错误消息 - 最高优先级
  error: (content, options = {}) => {
    messageManager.critical(content, options);
  },
  
  // 警告消息 - 中高优先级  
  warning: (content, options = {}) => {
    messageManager.warning(content, options);
  },
  
  // 信息消息 - 最低优先级
  info: (content, options = {}) => {
    messageManager.info(content, options);
  },
  
  // 通用方法
  show: (options) => {
    messageManager.show(options);
  },
  
  // 清除所有消息
  clear: () => {
    messageManager.clear();
  },
  
  // 高级方法 - 直接指定优先级
  critical: (content, options = {}) => {
    messageManager.critical(content, options);
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