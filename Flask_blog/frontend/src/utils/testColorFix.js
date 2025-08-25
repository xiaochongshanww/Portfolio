/**
 * 快速测试颜色修复
 */

import { renderMarkdown } from './markdownProcessor.reliable.js'

const testCode = `# 测试代码高亮颜色修复

测试Python代码：
\`\`\`python
import numpy as np
import matplotlib.pyplot as plt

def hello_world():
    print("Hello, World!")
    return "success"

# 创建一些数据
x = np.linspace(0, 10, 100)
y = np.sin(x)

plt.plot(x, y)
plt.show()
\`\`\`

测试JavaScript代码：
\`\`\`javascript
const greeting = "Hello, World!";
console.log(greeting);

function calculate(a, b) {
    return a + b;
}

const result = calculate(5, 3);
console.log("Result:", result);
\`\`\`

测试HTML代码：
\`\`\`html
<!DOCTYPE html>
<html>
<head>
    <title>Test Page</title>
</head>
<body>
    <h1>Hello World</h1>
    <p>This is a test.</p>
</body>
</html>
\`\`\`
`;

export const testColorFix = async () => {
    console.log('🧪 测试颜色修复...')
    
    try {
        const result = await renderMarkdown(testCode);
        
        const analysis = {
            success: !!result,
            outputLength: result.length,
            hasShikiClass: result.includes('class="shiki"'),
            hasDataTheme: result.includes('data-theme="github-light"'),
            hasColorSpans: result.includes('<span style="color:'),
            hasPre: result.includes('<pre'),
            codeBlockCount: (result.match(/<pre/g) || []).length
        };
        
        console.log('✅ 颜色修复测试结果:', analysis);
        
        // 输出前500字符用于检查
        console.log('📄 输出示例:', result.substring(0, 500));
        
        // 检查是否还有黑色背景
        const hasBlackBackground = result.includes('background-color:#1f2937') || 
                                 result.includes('background-color: #1f2937');
        
        if (hasBlackBackground) {
            console.warn('⚠️ 仍然检测到黑色背景!');
        } else {
            console.log('✅ 没有检测到黑色背景');
        }
        
        return {
            ...analysis,
            hasBlackBackground,
            result
        };
        
    } catch (error) {
        console.error('❌ 颜色修复测试失败:', error);
        return { success: false, error: error.message };
    }
};

// 如果在浏览器中，暴露测试函数
if (typeof window !== 'undefined') {
    window.testColorFix = testColorFix;
    console.log('🔧 颜色修复测试函数已暴露到 window.testColorFix');
}