/**
 * KaTeX调试和测试工具
 * 用于直接验证KaTeX功能和输出
 */

import { renderMarkdown, checkShikiStatus } from './markdownProcessor.simple.js'

// 测试内容集合
const testCases = [
  {
    name: '行内公式测试',
    content: '这是一个行内公式：$E = mc^2$，很简单对吧？'
  },
  {
    name: '块级公式测试',
    content: '这是块级公式：\n\n$$\\sum_{i=1}^{n} x_i = \\frac{1}{n}\\sum_{i=1}^{n} x_i$$\n\n很漂亮！'
  },
  {
    name: '复杂公式测试',
    content: '复杂的数学公式：$$\\int_0^\\infty e^{-x^2} dx = \\frac{\\sqrt{\\pi}}{2}$$'
  },
  {
    name: '混合内容测试',
    content: `# 数学文章

这是一篇包含数学公式的文章。

## 基础公式

行内公式：质能方程 $E = mc^2$ 是物理学的基础。

## 积分公式

下面是一个重要的积分：

$$\\int_0^\\infty e^{-x^2} dx = \\frac{\\sqrt{\\pi}}{2}$$

## 代码示例

\`\`\`python
import numpy as np
def gaussian(x):
    return np.exp(-x**2)
\`\`\`

这就是混合内容测试。`
  }
]

/**
 * 测试单个用例
 */
export const testSingleCase = async (testCase) => {
  console.group(`🧪 测试: ${testCase.name}`)
  
  console.log('输入内容:', testCase.content)
  console.log('内容长度:', testCase.content.length)
  console.log('包含$符号:', testCase.content.includes('$'))
  console.log('包含\\(符号:', testCase.content.includes('\\('))
  console.log('包含\\[符号:', testCase.content.includes('\\['))
  
  try {
    const start = performance.now()
    const result = await renderMarkdown(testCase.content)
    const end = performance.now()
    
    console.log('✅ 渲染成功')
    console.log('输出长度:', result.length)
    console.log('渲染时间:', `${(end - start).toFixed(2)}ms`)
    
    // 检查输出特征
    const features = {
      containsKaTeX: result.includes('katex'),
      containsSpanKatex: result.includes('<span class="katex">'),
      containsMath: result.includes('<math'),
      containsMathClass: result.includes('math-'),
      containsShiki: result.includes('shiki'),
      containsCode: result.includes('<code'),
      containsPre: result.includes('<pre')
    }
    
    console.log('输出特征:', features)
    
    // 输出HTML片段用于检查
    if (result.length > 0) {
      console.log('HTML片段(前500字符):', result.substring(0, 500))
      
      if (features.containsKaTeX) {
        console.log('🎉 发现KaTeX输出!')
        // 提取KaTeX相关的HTML
        const katexRegex = /<span class="katex">.*?<\/span>/g
        const katexMatches = result.match(katexRegex)
        if (katexMatches) {
          console.log('KaTeX片段:', katexMatches[0])
        }
      } else if (testCase.content.includes('$')) {
        console.warn('⚠️ 输入包含数学公式但输出中未发现KaTeX!')
      }
    }
    
    console.groupEnd()
    return {
      success: true,
      result,
      features,
      renderTime: end - start
    }
    
  } catch (error) {
    console.error('❌ 渲染失败:', error)
    console.groupEnd()
    return {
      success: false,
      error: error.message,
      renderTime: 0
    }
  }
}

/**
 * 运行所有测试用例
 */
export const runAllTests = async () => {
  console.log('🚀 开始KaTeX调试测试...')
  console.log('测试用例数量:', testCases.length)
  
  const results = []
  
  for (const testCase of testCases) {
    const result = await testSingleCase(testCase)
    results.push({
      name: testCase.name,
      ...result
    })
    
    // 添加延迟，避免过快的连续测试
    await new Promise(resolve => setTimeout(resolve, 100))
  }
  
  // 汇总结果
  console.log('\n📊 测试结果汇总:')
  const successCount = results.filter(r => r.success).length
  const failureCount = results.filter(r => !r.success).length
  
  console.log(`成功: ${successCount}/${results.length}`)
  console.log(`失败: ${failureCount}/${results.length}`)
  
  if (failureCount > 0) {
    console.log('\n❌ 失败的测试:')
    results.filter(r => !r.success).forEach(r => {
      console.log(`- ${r.name}: ${r.error}`)
    })
  }
  
  const katexWorkingCount = results.filter(r => r.success && r.features?.containsKaTeX).length
  console.log(`\n🧮 KaTeX工作正常的测试: ${katexWorkingCount}/${results.length}`)
  
  return results
}

/**
 * 检查当前页面是否有KaTeX样式
 */
export const checkKatexStyles = () => {
  console.group('🎨 检查KaTeX样式')
  
  // 检查CSS文件是否加载
  const stylesheets = Array.from(document.styleSheets)
  const katexStylesheet = stylesheets.find(sheet => {
    try {
      return sheet.href && sheet.href.includes('katex')
    } catch (e) {
      return false
    }
  })
  
  console.log('KaTeX样式表已加载:', !!katexStylesheet)
  if (katexStylesheet) {
    console.log('KaTeX样式表URL:', katexStylesheet.href)
  }
  
  // 检查是否有.katex相关的CSS规则
  let katexRulesCount = 0
  try {
    stylesheets.forEach(sheet => {
      try {
        const rules = sheet.cssRules || sheet.rules
        if (rules) {
          Array.from(rules).forEach(rule => {
            if (rule.selectorText && rule.selectorText.includes('katex')) {
              katexRulesCount++
            }
          })
        }
      } catch (e) {
        // 跨域样式表访问限制，忽略
      }
    })
  } catch (e) {
    console.warn('无法检查CSS规则:', e.message)
  }
  
  console.log('找到的KaTeX CSS规则数:', katexRulesCount)
  
  // 检查页面上是否有.katex元素
  const katexElements = document.querySelectorAll('.katex')
  console.log('页面上的.katex元素数量:', katexElements.length)
  
  if (katexElements.length > 0) {
    const firstKatex = katexElements[0]
    const computedStyles = window.getComputedStyle(firstKatex)
    console.log('第一个.katex元素的计算样式示例:', {
      display: computedStyles.display,
      fontFamily: computedStyles.fontFamily,
      fontSize: computedStyles.fontSize,
      color: computedStyles.color
    })
  }
  
  console.groupEnd()
  
  return {
    stylesheetLoaded: !!katexStylesheet,
    rulesCount: katexRulesCount,
    elementsCount: katexElements.length
  }
}

// 导出测试用例供外部使用
export { testCases }

// 便捷的全局调试函数
export const debugKaTeX = {
  runTests: runAllTests,
  testCase: testSingleCase,
  checkStyles: checkKatexStyles,
  checkShiki: checkShikiStatus,
  testCases
}

/**
 * 专门调试代码高亮颜色问题
 */
export const debugCodeColors = async () => {
  console.log('🎨 调试代码高亮颜色...')
  
  const simpleTestCase = {
    name: '代码高亮颜色测试',
    content: `测试代码高亮：

\`\`\`python
def hello():
    print("Hello, World!")
    return "success"
\`\`\`

\`\`\`javascript
const greeting = "Hello";
console.log(greeting);
\`\`\`
`
  }
  
  try {
    const result = await renderMarkdown(simpleTestCase.content)
    
    console.log('📄 生成的完整HTML:', result)
    
    // 分析HTML结构
    const preMatches = result.match(/<pre[^>]*>.*?<\/pre>/gs)
    if (preMatches) {
      preMatches.forEach((match, i) => {
        console.log(`🔍 代码块 ${i + 1}:`, match)
        console.log(`   - 包含data-theme: ${match.includes('data-theme')}`)
        console.log(`   - 包含class="shiki": ${match.includes('class="shiki"')}`)
        console.log(`   - 包含背景色样式: ${match.includes('background-color')}`)
        console.log(`   - 包含颜色span: ${match.includes('<span style="color')}`)
      })
    }
    
    // 检查可能的CSS问题
    console.log('🔍 CSS样式检查:')
    const stylesheets = Array.from(document.styleSheets)
    stylesheets.forEach((sheet, i) => {
      try {
        const rules = sheet.cssRules || sheet.rules
        if (rules) {
          for (let rule of rules) {
            if (rule.selectorText && rule.selectorText.includes('pre')) {
              console.log(`   样式表 ${i}: ${rule.selectorText} -> ${rule.style.backgroundColor || 'no bg'}`)
            }
          }
        }
      } catch (e) {
        console.log(`   样式表 ${i}: 无法访问 (可能是跨域)`)
      }
    })
    
    return result
    
  } catch (error) {
    console.error('❌ 调试失败:', error)
    return null
  }
}

// 在浏览器控制台中暴露调试函数
if (typeof window !== 'undefined') {
  window.debugKaTeX = debugKaTeX
  window.debugCodeColors = debugCodeColors
}

export default debugKaTeX