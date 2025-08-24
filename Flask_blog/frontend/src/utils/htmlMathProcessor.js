/**
 * HTML数学公式处理器
 * 专门处理已经是HTML格式但包含未渲染数学公式的内容
 */

import katex from 'katex'

/**
 * HTML中的数学公式处理器
 * 在HTML内容中查找数学公式标记并渲染为KaTeX
 */
export class HTMLMathProcessor {
  
  /**
   * 处理HTML内容中的数学公式
   * @param {string} htmlContent - HTML内容
   * @param {Object} options - 配置选项
   * @returns {string} 处理后的HTML内容
   */
  static processHTMLMath(htmlContent, options = {}) {
    if (!htmlContent || typeof htmlContent !== 'string') {
      return htmlContent
    }

    const {
      throwOnError = false,
      errorColor = '#cc0000',
      displayMode = 'auto', // 'auto', 'inline', 'display'
      strict = 'warn'
    } = options

    let processedContent = htmlContent

    try {
      // 1. 处理行内数学公式 $...$
      processedContent = this.processInlineMath(processedContent, {
        throwOnError,
        errorColor,
        strict
      })

      // 2. 处理块级数学公式 $$...$$
      processedContent = this.processDisplayMath(processedContent, {
        throwOnError,
        errorColor,
        strict
      })

      // 3. 处理LaTeX风格的数学公式 \(...\) 和 \[...\]
      processedContent = this.processLatexMath(processedContent, {
        throwOnError,
        errorColor,
        strict
      })

      console.log('✅ HTML数学公式处理完成', {
        originalLength: htmlContent.length,
        processedLength: processedContent.length,
        mathFormulasFound: this.countMathFormulas(htmlContent),
        katexElementsGenerated: this.countKatexElements(processedContent)
      })

    } catch (error) {
      console.error('❌ HTML数学公式处理失败:', error)
      return htmlContent // 返回原始内容
    }

    return processedContent
  }

  /**
   * 处理行内数学公式 $...$
   */
  static processInlineMath(html, options) {
    // 匹配单个$包围的公式，但避免匹配$$
    const inlineMathRegex = /(?<!\$)\$(?!\$)([^$\n]+?)\$(?!\$)/g
    
    return html.replace(inlineMathRegex, (match, mathContent) => {
      try {
        const rendered = katex.renderToString(mathContent.trim(), {
          displayMode: false,
          throwOnError: options.throwOnError,
          errorColor: options.errorColor,
          strict: options.strict
        })
        
        console.log('✅ 行内公式渲染成功:', mathContent.trim())
        return rendered
        
      } catch (error) {
        console.warn('⚠️ 行内公式渲染失败:', mathContent.trim(), error.message)
        return `<span class="math-error" title="${error.message}">$${mathContent}$</span>`
      }
    })
  }

  /**
   * 处理块级数学公式 $$...$$
   */
  static processDisplayMath(html, options) {
    // 匹配$$包围的公式
    const displayMathRegex = /\$\$([^$]+?)\$\$/g
    
    return html.replace(displayMathRegex, (match, mathContent) => {
      try {
        const rendered = katex.renderToString(mathContent.trim(), {
          displayMode: true,
          throwOnError: options.throwOnError,
          errorColor: options.errorColor,
          strict: options.strict
        })
        
        console.log('✅ 块级公式渲染成功:', mathContent.trim())
        return `<div class="katex-display">${rendered}</div>`
        
      } catch (error) {
        console.warn('⚠️ 块级公式渲染失败:', mathContent.trim(), error.message)
        return `<div class="math-error" title="${error.message}">$$${mathContent}$$</div>`
      }
    })
  }

  /**
   * 处理LaTeX风格的数学公式 \(...\) 和 \[...\]
   */
  static processLatexMath(html, options) {
    // 处理行内LaTeX公式 \(...\)
    const latexInlineRegex = /\\\\?\(([^)]+?)\\\\?\)/g
    html = html.replace(latexInlineRegex, (match, mathContent) => {
      try {
        const rendered = katex.renderToString(mathContent.trim(), {
          displayMode: false,
          throwOnError: options.throwOnError,
          errorColor: options.errorColor,
          strict: options.strict
        })
        
        console.log('✅ LaTeX行内公式渲染成功:', mathContent.trim())
        return rendered
        
      } catch (error) {
        console.warn('⚠️ LaTeX行内公式渲染失败:', mathContent.trim(), error.message)
        return `<span class="math-error" title="${error.message}">\\(${mathContent}\\)</span>`
      }
    })

    // 处理块级LaTeX公式 \[...\]
    const latexDisplayRegex = /\\\\?\[([^\]]+?)\\\\?\]/g
    html = html.replace(latexDisplayRegex, (match, mathContent) => {
      try {
        const rendered = katex.renderToString(mathContent.trim(), {
          displayMode: true,
          throwOnError: options.throwOnError,
          errorColor: options.errorColor,
          strict: options.strict
        })
        
        console.log('✅ LaTeX块级公式渲染成功:', mathContent.trim())
        return `<div class="katex-display">${rendered}</div>`
        
      } catch (error) {
        console.warn('⚠️ LaTeX块级公式渲染失败:', mathContent.trim(), error.message)
        return `<div class="math-error" title="${error.message}">\\[${mathContent}\\]</div>`
      }
    })

    return html
  }

  /**
   * 计算原始内容中的数学公式数量
   */
  static countMathFormulas(content) {
    const patterns = [
      /(?<!\$)\$(?!\$)([^$\n]+?)\$(?!\$)/g, // 行内 $...$
      /\$\$([^$]+?)\$\$/g,                    // 块级 $$...$$
      /\\\\?\(([^)]+?)\\\\?\)/g,              // LaTeX行内 \(...\)
      /\\\\?\[([^\]]+?)\\\\?\]/g              // LaTeX块级 \[...\]
    ]
    
    let total = 0
    patterns.forEach(pattern => {
      const matches = content.match(pattern)
      if (matches) total += matches.length
    })
    
    return total
  }

  /**
   * 计算处理后内容中的KaTeX元素数量
   */
  static countKatexElements(content) {
    const katexPattern = /<span class="katex"/g
    const matches = content.match(katexPattern)
    return matches ? matches.length : 0
  }

  /**
   * 检查内容是否包含数学公式标记
   */
  static containsMathFormulas(content) {
    if (!content || typeof content !== 'string') return false
    
    const mathPatterns = [
      /\$[^$\n]+?\$/,          // 行内公式
      /\$\$[^$]+?\$\$/,        // 块级公式
      /\\\\?\([^)]+?\\\\\?\)/, // LaTeX行内
      /\\\\?\[[^\]]+?\\\\\?\]/ // LaTeX块级
    ]
    
    return mathPatterns.some(pattern => pattern.test(content))
  }

  /**
   * 预处理HTML内容 - 保护数学公式不被HTML解析干扰
   */
  static preprocessHTML(html) {
    // 保护HTML标签内的数学公式不被处理
    // 例如：<code>$E=mc^2$</code> 中的公式不应该被渲染
    
    const protectedRanges = []
    
    // 保护<code>标签内的内容
    const codePattern = /<code[^>]*>.*?<\/code>/gi
    let match
    while ((match = codePattern.exec(html)) !== null) {
      protectedRanges.push({
        start: match.index,
        end: match.index + match[0].length
      })
    }
    
    // 保护<pre>标签内的内容
    const prePattern = /<pre[^>]*>.*?<\/pre>/gi
    while ((match = prePattern.exec(html)) !== null) {
      protectedRanges.push({
        start: match.index,
        end: match.index + match[0].length
      })
    }

    return { html, protectedRanges }
  }

  /**
   * 检查位置是否在受保护区域内
   */
  static isProtectedPosition(position, protectedRanges) {
    return protectedRanges.some(range => 
      position >= range.start && position <= range.end
    )
  }
}

/**
 * 便捷的导出函数
 */
export const processHTMLMath = (htmlContent, options = {}) => {
  return HTMLMathProcessor.processHTMLMath(htmlContent, options)
}

export const containsMathFormulas = (content) => {
  return HTMLMathProcessor.containsMathFormulas(content)
}

export default HTMLMathProcessor