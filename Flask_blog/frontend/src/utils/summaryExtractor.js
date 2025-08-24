/**
 * 智能摘要提取工具
 * 根据内容类型采用不同的摘要提取策略，确保摘要内容干净、可读
 */

import { ContentTypeDetector } from './contentTypeDetector.js';

export class SummaryExtractor {
  
  /**
   * 提取内容摘要
   * @param {string} htmlContent - HTML内容
   * @param {string} contentType - 内容类型 ('auto', 'markdown', 'html_source')
   * @param {number} maxLength - 最大长度
   * @param {Object} options - 提取选项
   * @returns {string} 提取的摘要
   */
  static extractSummary(htmlContent, contentType = 'auto', maxLength = 150, options = {}) {
    const defaultOptions = {
      preserveLineBreaks: false,      // 是否保留换行
      removeCodeBlocks: true,         // 是否移除代码块
      removeLinkTexts: false,         // 是否移除链接文本
      smartTruncation: true,          // 是否智能截断
      ...options
    };
    
    // 输入验证
    if (!htmlContent || typeof htmlContent !== 'string') {
      return '';
    }
    
    try {
      // 自动检测内容类型
      const detectedType = contentType === 'auto' ? 
        ContentTypeDetector.analyzeContent(htmlContent).type : contentType;
      
      let summary = '';
      
      if (detectedType === 'html_source') {
        summary = this.extractFromHTMLSource(htmlContent, maxLength, defaultOptions);
      } else {
        summary = this.extractFromMarkdown(htmlContent, maxLength, defaultOptions);
      }
      
      // 最终清理和验证
      return this.finalCleanup(summary, maxLength);
      
    } catch (error) {
      console.warn('SummaryExtractor: 摘要提取过程中出现错误', error);
      // 降级处理：简单的文本提取
      return this.fallbackExtraction(htmlContent, maxLength);
    }
  }
  
  /**
   * 从HTML源码内容提取摘要
   */
  static extractFromHTMLSource(htmlContent, maxLength, options) {
    // 方法1: 使用DOMParser（浏览器环境）
    if (typeof window !== 'undefined' && window.DOMParser) {
      return this.extractUsingDOMParser(htmlContent, maxLength, options);
    }
    
    // 方法2: 使用正则表达式（Node.js环境或降级）
    return this.extractUsingRegex(htmlContent, maxLength, options);
  }
  
  /**
   * 使用DOMParser提取HTML内容的文本
   */
  static extractUsingDOMParser(htmlContent, maxLength, options) {
    try {
      const parser = new DOMParser();
      const doc = parser.parseFromString(htmlContent, 'text/html');
      
      // 移除不需要的元素
      this.removeUnwantedElements(doc, options);
      
      // 获取文本内容
      const textContent = doc.body ? doc.body.textContent : '';
      
      return this.processExtractedText(textContent, maxLength, options);
      
    } catch (error) {
      console.warn('DOMParser提取失败，使用正则表达式降级', error);
      return this.extractUsingRegex(htmlContent, maxLength, options);
    }
  }
  
  /**
   * 使用正则表达式提取HTML内容的文本
   */
  static extractUsingRegex(htmlContent, maxLength, options) {
    let text = htmlContent;
    
    // 移除脚本和样式标签及其内容
    text = text.replace(/<(script|style)[^>]*>[\s\S]*?<\/\1>/gi, ' ');
    
    // 移除注释
    text = text.replace(/<!--[\s\S]*?-->/g, ' ');
    
    // 移除HTML标签，但保留内容
    text = text.replace(/<[^>]+>/g, ' ');
    
    // 解码HTML实体
    text = this.decodeHTMLEntities(text);
    
    return this.processExtractedText(text, maxLength, options);
  }
  
  /**
   * 从Markdown内容提取摘要
   */
  static extractFromMarkdown(htmlContent, maxLength, options) {
    let text = htmlContent;
    
    // 移除HTML标签（Markdown中可能包含HTML）
    text = text.replace(/<[^>]+>/g, ' ');
    
    // 移除Markdown语法
    text = this.removeMarkdownSyntax(text, options);
    
    // 解码HTML实体
    text = this.decodeHTMLEntities(text);
    
    return this.processExtractedText(text, maxLength, options);
  }
  
  /**
   * 移除不需要的DOM元素
   */
  static removeUnwantedElements(doc, options) {
    const unwantedSelectors = [
      'script', 'style', 'noscript',      // 脚本和样式
      '.hidden', '[style*="display:none"]', '[style*="display: none"]', // 隐藏元素
    ];
    
    if (options.removeCodeBlocks) {
      unwantedSelectors.push('pre', 'code');
    }
    
    unwantedSelectors.forEach(selector => {
      try {
        const elements = doc.querySelectorAll(selector);
        elements.forEach(el => el.remove());
      } catch (error) {
        // 忽略选择器错误
      }
    });
  }
  
  /**
   * 移除Markdown语法标记
   */
  static removeMarkdownSyntax(text, options) {
    // 移除代码块
    if (options.removeCodeBlocks) {
      text = text.replace(/```[\s\S]*?```/g, ' '); // 围栏代码块
      text = text.replace(/`[^`\n]+`/g, ' ');      // 内联代码
    }
    
    // 移除图片语法 ![alt](src)
    text = text.replace(/!\[([^\]]*)\]\([^)]*\)/g, '$1');
    
    // 处理链接语法 [text](url)
    if (options.removeLinkTexts) {
      text = text.replace(/\[([^\]]*)\]\([^)]*\)/g, '');
    } else {
      text = text.replace(/\[([^\]]*)\]\([^)]*\)/g, '$1');
    }
    
    // 移除标题标记
    text = text.replace(/^#{1,6}\s*/gm, '');
    
    // 移除强调标记
    text = text.replace(/[*_]{1,2}([^*_\n]+)[*_]{1,2}/g, '$1');
    
    // 移除删除线
    text = text.replace(/~~([^~\n]+)~~/g, '$1');
    
    // 移除列表标记
    text = text.replace(/^\s*[-*+]\s+/gm, '');      // 无序列表
    text = text.replace(/^\s*\d+\.\s+/gm, '');      // 有序列表
    
    // 移除引用标记
    text = text.replace(/^\s*>\s*/gm, '');
    
    // 移除水平分割线
    text = text.replace(/^[-*_]{3,}\s*$/gm, ' ');
    
    return text;
  }
  
  /**
   * 处理提取的文本内容
   */
  static processExtractedText(text, maxLength, options) {
    if (!text) return '';
    
    // 标准化空白字符
    text = text.replace(/\s+/g, ' ');
    
    // 处理换行
    if (!options.preserveLineBreaks) {
      text = text.replace(/\n+/g, ' ');
    }
    
    // 移除开头和结尾的空白
    text = text.trim();
    
    // 智能截断
    if (text.length > maxLength) {
      if (options.smartTruncation) {
        text = this.smartTruncate(text, maxLength);
      } else {
        text = text.substring(0, maxLength) + '...';
      }
    }
    
    return text;
  }
  
  /**
   * 智能截断文本，避免截断单词
   */
  static smartTruncate(text, maxLength) {
    if (text.length <= maxLength) {
      return text;
    }
    
    // 留出省略号的空间
    const truncateLength = maxLength - 3;
    const truncated = text.substring(0, truncateLength);
    
    // 查找最后一个空格或标点符号
    const breakPoints = [' ', '。', '，', '！', '？', '.', ',', '!', '?', ';', ':'];
    let bestBreakPoint = -1;
    
    for (let i = truncated.length - 1; i >= truncateLength * 0.8; i--) {
      if (breakPoints.includes(truncated[i])) {
        bestBreakPoint = i;
        break;
      }
    }
    
    if (bestBreakPoint > 0) {
      return truncated.substring(0, bestBreakPoint).trim() + '...';
    }
    
    // 如果找不到合适的断点，直接截断
    return truncated + '...';
  }
  
  /**
   * 解码HTML实体
   */
  static decodeHTMLEntities(text) {
    const entityMap = {
      '&lt;': '<',
      '&gt;': '>',
      '&amp;': '&',
      '&quot;': '"',
      '&#39;': "'",
      '&nbsp;': ' ',
      '&copy;': '©',
      '&reg;': '®',
      '&trade;': '™',
      '&hellip;': '…',
      '&mdash;': '—',
      '&ndash;': '–',
      '&ldquo;': '“',
      '&rdquo;': '”',
      '&lsquo;': '‘',
      '&rsquo;': '’'
    };
    
    let decoded = text;
    
    // 替换命名实体
    Object.keys(entityMap).forEach(entity => {
      const regex = new RegExp(entity, 'g');
      decoded = decoded.replace(regex, entityMap[entity]);
    });
    
    // 替换数字实体
    decoded = decoded.replace(/&#(\d+);/g, (match, num) => {
      return String.fromCharCode(parseInt(num, 10));
    });
    
    // 替换十六进制实体
    decoded = decoded.replace(/&#x([0-9a-fA-F]+);/g, (match, hex) => {
      return String.fromCharCode(parseInt(hex, 16));
    });
    
    return decoded;
  }
  
  /**
   * 最终清理和验证
   */
  static finalCleanup(text, maxLength) {
    if (!text) return '';
    
    // 移除多余的空白字符
    text = text.replace(/\s+/g, ' ').trim();
    
    // 确保不超过最大长度
    if (text.length > maxLength) {
      text = text.substring(0, maxLength - 3) + '...';
    }
    
    // 移除开头的标点符号
    text = text.replace(/^[^\w\u4e00-\u9fff]+/, '');
    
    return text;
  }
  
  /**
   * 降级提取方法（当主要方法失败时使用）
   */
  static fallbackExtraction(htmlContent, maxLength) {
    // 最简单的文本提取
    const text = htmlContent
      .replace(/<[^>]+>/g, ' ')        // 移除所有HTML标签
      .replace(/\s+/g, ' ')            // 标准化空白
      .trim();
    
    if (text.length > maxLength) {
      return text.substring(0, maxLength - 3) + '...';
    }
    
    return text;
  }
  
  /**
   * 批量提取摘要
   */
  static batchExtract(contentList, options = {}) {
    if (!Array.isArray(contentList)) {
      throw new Error('contentList must be an array');
    }
    
    return contentList.map((content, index) => {
      try {
        return {
          index,
          summary: this.extractSummary(content, options.contentType, options.maxLength, options),
          success: true
        };
      } catch (error) {
        return {
          index,
          summary: '',
          success: false,
          error: error.message
        };
      }
    });
  }
  
  /**
   * 获取摘要统计信息
   */
  static getSummaryStats(summary) {
    if (!summary) {
      return { length: 0, wordCount: 0, hasEllipsis: false };
    }
    
    const wordCount = summary.split(/\s+/).filter(word => word.length > 0).length;
    const hasEllipsis = summary.endsWith('...');
    
    return {
      length: summary.length,
      wordCount,
      hasEllipsis,
      estimatedReadingTime: Math.ceil(wordCount / 200) // 假设每分钟200词
    };
  }
}

// 导出便捷方法
export const extractSummary = (content, maxLength = 150) => 
  SummaryExtractor.extractSummary(content, 'auto', maxLength);

export const extractSummaryWithType = (content, type, maxLength = 150) =>
  SummaryExtractor.extractSummary(content, type, maxLength);