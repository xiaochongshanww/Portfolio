/**
 * 内容类型检测工具
 * 智能识别HTML源码内容和Markdown内容，为不同类型采用不同的渲染策略
 */

export class ContentTypeDetector {
  
  /**
   * 分析内容并返回类型检测结果
   * @param {string} htmlContent - 要分析的HTML内容
   * @returns {Object} 检测结果，包含类型、置信度和特征信息
   */
  static analyzeContent(htmlContent) {
    // 输入验证
    if (!htmlContent || typeof htmlContent !== 'string') {
      return { 
        type: 'markdown', 
        confidence: 1.0,
        features: { reason: 'empty_or_invalid_input' }
      };
    }

    try {
      const analysis = {
        htmlTagCount: this.countHTMLTags(htmlContent),
        inlineStyleCount: this.countInlineStyles(htmlContent),
        complexStructureCount: this.countComplexStructures(htmlContent),
        markdownPatterns: this.countMarkdownPatterns(htmlContent),
        totalLength: htmlContent.length,
        hasSpecialHTMLFeatures: this.detectSpecialHTMLFeatures(htmlContent)
      };
      
      return this.classifyContent(analysis, htmlContent);
    } catch (error) {
      console.warn('ContentTypeDetector: 分析过程中出现错误', error);
      return { 
        type: 'markdown', 
        confidence: 0.5,
        features: { reason: 'analysis_error', error: error.message }
      };
    }
  }
  
  /**
   * 统计HTML标签数量（更精确的实现）
   */
  static countHTMLTags(content) {
    // 匹配所有HTML标签，包括自闭合标签
    const tagPattern = /<\/?[a-zA-Z][^>]*\/?>/g;
    const matches = content.match(tagPattern);
    return matches ? matches.length : 0;
  }
  
  /**
   * 统计内联样式数量
   */
  static countInlineStyles(content) {
    // 匹配style属性，支持单引号、双引号和无引号
    const stylePattern = /style\s*=\s*(['"])[^'"]*\1|style\s*=\s*[^'"\s>][^\s>]*/gi;
    const matches = content.match(stylePattern);
    return matches ? matches.length : 0;
  }
  
  /**
   * 统计复杂HTML结构元素
   */
  static countComplexStructures(content) {
    // 检测典型的HTML布局和结构元素
    const complexElements = [
      'div', 'span', 'section', 'article', 'header', 'footer', 'aside', 'nav',
      'main', 'figure', 'figcaption', 'details', 'summary'
    ];
    
    let count = 0;
    complexElements.forEach(tag => {
      const pattern = new RegExp(`<${tag}[^>]*>`, 'gi');
      const matches = content.match(pattern);
      if (matches) count += matches.length;
    });
    
    return count;
  }
  
  /**
   * 统计Markdown模式的特征
   */
  static countMarkdownPatterns(content) {
    const patterns = {
      // Markdown标题 (# ## ###)
      headers: (content.match(/^#{1,6}\s+[^\n]+$/gm) || []).length,
      
      // 代码块 (```)
      codeBlocks: (content.match(/```[\s\S]*?```/g) || []).length,
      
      // Markdown链接格式 [text](url)
      links: (content.match(/\[([^\]]+)\]\(([^)]+)\)/g) || []).length,
      
      // 强调语法 **bold** __bold__ *italic* _italic_
      emphasis: (content.match(/(\*\*|__)[^*_\n]+(\*\*|__)|(\*|_)[^*_\n]+(\*|_)/g) || []).length,
      
      // 列表项 (- * +)
      unorderedLists: (content.match(/^[\s]*[-*+]\s+/gm) || []).length,
      
      // 有序列表 (1. 2.)
      orderedLists: (content.match(/^[\s]*\d+\.\s+/gm) || []).length,
      
      // 引用块 (>)
      blockquotes: (content.match(/^[\s]*>\s+/gm) || []).length,
      
      // 内联代码 (`code`)
      inlineCode: (content.match(/`[^`\n]+`/g) || []).length,
      
      // 数学公式 ($...$ 和 $$...$$)
      mathFormulas: ((content.match(/\$[^$\n]+?\$/g) || []).length + (content.match(/\$\$[^$]+?\$\$/g) || []).length)
    };
    
    return Object.values(patterns).reduce((sum, count) => sum + count, 0);
  }
  
  /**
   * 检测特殊的HTML特征
   */
  static detectSpecialHTMLFeatures(content) {
    const features = {
      // 检测CSS类使用
      hasCSSClasses: /class\s*=\s*['"][^'"]*['"]/.test(content),
      
      // 检测ID属性
      hasIDs: /id\s*=\s*['"][^'"]*['"]/.test(content),
      
      // 检测数据属性
      hasDataAttributes: /data-[a-zA-Z0-9-]+\s*=/.test(content),
      
      // 检测表格结构
      hasTableStructure: /<table[^>]*>[\s\S]*<\/table>/i.test(content),
      
      // 检测表单元素
      hasFormElements: /<(form|input|select|textarea|button)[^>]*>/i.test(content),
      
      // 检测多媒体元素
      hasMediaElements: /<(img|video|audio|canvas|svg)[^>]*>/i.test(content),
      
      // 检测HTML5语义元素
      hasSemanticElements: /<(article|section|nav|header|footer|aside|main)[^>]*>/i.test(content)
    };
    
    return features;
  }
  
  /**
   * 基于分析结果对内容进行分类
   */
  static classifyContent(analysis, originalContent) {
    const {
      htmlTagCount,
      inlineStyleCount,
      complexStructureCount,
      markdownPatterns,
      totalLength,
      hasSpecialHTMLFeatures
    } = analysis;
    
    // 计算HTML密度 (每100字符中的HTML标签数)
    const htmlDensity = htmlTagCount / Math.max(totalLength / 100, 1);
    
    // 计算特征权重
    const htmlFeatureScore = this.calculateHTMLFeatureScore({
      inlineStyleCount,
      complexStructureCount,
      hasSpecialHTMLFeatures,
      htmlDensity
    });
    
    const markdownFeatureScore = this.calculateMarkdownFeatureScore(markdownPatterns);
    
    // 决策逻辑：优先考虑强HTML特征
    if (this.hasStrongHTMLIndicators(analysis)) {
      return {
        type: 'html_source',
        confidence: Math.min(0.95, 0.7 + (htmlFeatureScore * 0.25)),
        features: {
          htmlTagCount,
          inlineStyleCount,
          complexStructureCount,
          htmlDensity: parseFloat(htmlDensity.toFixed(2)),
          estimatedPreservationNeeded: inlineStyleCount > 0 || hasSpecialHTMLFeatures.hasCSSClasses,
          specialFeatures: hasSpecialHTMLFeatures,
          classificationReason: 'strong_html_features'
        }
      };
    }
    
    // 弱HTML特征，但Markdown特征也不强
    if (htmlFeatureScore > markdownFeatureScore && htmlTagCount > 3) {
      return {
        type: 'html_source',
        confidence: Math.min(0.8, 0.6 + (htmlFeatureScore * 0.2)),
        features: {
          htmlTagCount,
          inlineStyleCount,
          htmlDensity: parseFloat(htmlDensity.toFixed(2)),
          estimatedPreservationNeeded: inlineStyleCount > 0,
          classificationReason: 'moderate_html_features'
        }
      };
    }
    
    // 默认归类为Markdown
    return {
      type: 'markdown',
      confidence: Math.min(0.95, 0.75 + (markdownFeatureScore * 0.05)),
      features: { 
        markdownPatterns,
        htmlTagCount,
        classificationReason: 'markdown_or_mixed_content'
      }
    };
  }
  
  /**
   * 检测强HTML指示器
   */
  static hasStrongHTMLIndicators(analysis) {
    const { 
      inlineStyleCount, 
      complexStructureCount, 
      hasSpecialHTMLFeatures,
      markdownPatterns,
      htmlTagCount,
      totalLength
    } = analysis;
    
    // 条件1：有内联样式且HTML结构复杂
    if (inlineStyleCount > 0 && complexStructureCount > 2) return true;
    
    // 条件2：有CSS类或ID，且HTML标签密度高
    if ((hasSpecialHTMLFeatures.hasCSSClasses || hasSpecialHTMLFeatures.hasIDs) && 
        htmlTagCount > totalLength / 50) return true;
    
    // 条件3：包含表格、表单或多媒体元素
    if (hasSpecialHTMLFeatures.hasTableStructure || 
        hasSpecialHTMLFeatures.hasFormElements || 
        hasSpecialHTMLFeatures.hasMediaElements) return true;
    
    // 条件4：HTML5语义元素较多且Markdown特征少
    if (hasSpecialHTMLFeatures.hasSemanticElements && markdownPatterns < 3) return true;
    
    return false;
  }
  
  /**
   * 计算HTML特征分数
   */
  static calculateHTMLFeatureScore({ inlineStyleCount, complexStructureCount, hasSpecialHTMLFeatures, htmlDensity }) {
    let score = 0;
    
    // 内联样式权重最高
    score += Math.min(inlineStyleCount * 0.3, 2.0);
    
    // 复杂结构权重
    score += Math.min(complexStructureCount * 0.2, 1.5);
    
    // HTML密度权重
    score += Math.min(htmlDensity * 0.1, 1.0);
    
    // 特殊特征权重
    Object.values(hasSpecialHTMLFeatures).forEach(hasFeature => {
      if (hasFeature) score += 0.3;
    });
    
    return Math.min(score, 5.0);
  }
  
  /**
   * 计算Markdown特征分数
   */
  static calculateMarkdownFeatureScore(markdownPatterns) {
    return Math.min(markdownPatterns * 0.2, 3.0);
  }
  
  /**
   * 获取内容类型的中文描述
   */
  static getTypeDescription(analysisResult) {
    const { type, confidence, features } = analysisResult;
    
    const descriptions = {
      'html_source': `HTML源码内容 (${Math.round(confidence * 100)}% 置信度)`,
      'markdown': `Markdown内容 (${Math.round(confidence * 100)}% 置信度)`
    };
    
    return descriptions[type] || '未知内容类型';
  }
  
  /**
   * 批量分析多个内容
   */
  static batchAnalyze(contentList) {
    if (!Array.isArray(contentList)) {
      throw new Error('contentList must be an array');
    }
    
    return contentList.map((content, index) => ({
      index,
      content: content.substring(0, 100) + '...', // 截取前100字符用于调试
      analysis: this.analyzeContent(content)
    }));
  }
}

// 导出默认实例方法，方便直接使用
export const detectContentType = (content) => ContentTypeDetector.analyzeContent(content);
export const getTypeDescription = (analysisResult) => ContentTypeDetector.getTypeDescription(analysisResult);