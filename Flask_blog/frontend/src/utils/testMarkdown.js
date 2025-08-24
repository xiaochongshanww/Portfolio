/**
 * 测试markdown-it-katex是否正常工作
 */

import MarkdownIt from 'markdown-it'
import markdownItKatex from 'markdown-it-katex'

// 创建最简单的配置
const katexPlugin = markdownItKatex.default || markdownItKatex;
const md = MarkdownIt().use(katexPlugin)

// 测试内容
const testContent = `
# 数学公式测试

这是行内公式：$E = mc^2$

这是块级公式：
$$\\sum_{i=1}^{n} x_i = \\frac{1}{n}\\sum_{i=1}^{n} x_i$$

这是另一个行内公式：$f(x) = x^2$
`

// 测试函数
export const testKaTeX = () => {
  console.log('=== KaTeX测试开始 ===')
  console.log('markdownItKatex:', markdownItKatex)
  console.log('katexPlugin:', katexPlugin)
  console.log('输入:', testContent)
  
  try {
    const result = md.render(testContent)
    console.log('输出:', result)
    
    // 检查是否包含KaTeX生成的HTML
    if (result.includes('katex') || result.includes('math')) {
      console.log('✅ KaTeX插件工作正常')
      return true
    } else {
      console.log('❌ KaTeX插件未工作，输出中没有找到数学公式标记')
      console.log('原始输出长度:', result.length)
      return false
    }
  } catch (error) {
    console.error('❌ KaTeX测试失败:', error)
    console.error('错误堆栈:', error.stack)
    return false
  }
}

export default testKaTeX