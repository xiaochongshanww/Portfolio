# 数学公式渲染测试

## 行内公式测试
这是一个行内公式：$E = mc^2$，爱因斯坦的质能方程。

另一个行内公式：$\int_{-\infty}^{\infty} e^{-x^2} dx = \sqrt{\pi}$

## 块级公式测试
这是一个块级公式：

$$\frac{d}{dx}\left[ \int_{a}^{x} f(t) dt\right] = f(x)$$

更复杂的公式：

$$\sum_{n=1}^{\infty} \frac{1}{n^2} = \frac{\pi^2}{6}$$

## LaTeX风格公式测试
行内LaTeX风格：\(x = \frac{-b \pm \sqrt{b^2 - 4ac}}{2a}\)

块级LaTeX风格：
\[
\begin{pmatrix}
a & b \\
c & d
\end{pmatrix}
\begin{pmatrix}
x \\
y
\end{pmatrix}
=
\begin{pmatrix}
ax + by \\
cx + dy
\end{pmatrix}
\]

## 组合测试
在一段文字中包含多个公式：质量能量关系$E=mc^2$，薛定谔方程$i\hbar\frac{\partial}{\partial t}\Psi = \hat{H}\Psi$，以及欧拉公式$e^{i\pi} + 1 = 0$。

## Markdown冲突测试
这里测试Markdown和KaTeX的冲突处理：

行内公式中的乘法符号：$f(x) = a * x^2 + b * x + c$

块级公式中的强调符号：
$$E = m * c^2$$

更复杂的例子：$\sum_{i=1}^{n} x_i * y_i$

## 长公式测试（多行）
Ridge回归损失函数：
$\text{Cost}*{\text{Ridge}} = \text{MSE} + \lambda \sum*{j=1}^{p} \beta_j^2 = \frac{1}{n}\sum_{i=1}^{n}(y_i - \hat{y_i})^2 + \lambda \sum_{j=1}^{p} \beta_j^2$

另一个长公式：
$f(x) = \sum_{i=0}^{n} a_i \cdot x^i + \prod_{j=1}^{m} b_j \cdot \sin(c_j \cdot x) + \int_{0}^{\infty} e^{-t} \cdot dt$

## 代码高亮测试

### JavaScript代码
```javascript
// 计算斐波那契数列
function fibonacci(n) {
  if (n <= 1) return n;
  return fibonacci(n - 1) + fibonacci(n - 2);
}

console.log(fibonacci(10)); // 55
```

### Python代码
```python
import numpy as np
import matplotlib.pyplot as plt

# 生成数据
x = np.linspace(0, 2*np.pi, 100)
y = np.sin(x)

# 绘制图形
plt.figure(figsize=(10, 6))
plt.plot(x, y, 'b-', linewidth=2, label='sin(x)')
plt.xlabel('x')
plt.ylabel('y')
plt.title('Sine Function')
plt.grid(True)
plt.legend()
plt.show()
```

### Vue组件
```vue
<template>
  <div class="math-renderer">
    <h2>{{ title }}</h2>
    <div v-html="renderedContent"></div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { processMarkdown } from '@/utils/markdownProcessor.js'

const props = defineProps({
  content: String,
  title: String
})

const renderedContent = computed(async () => {
  return await processMarkdown(props.content)
})
</script>
```

### SQL查询
```sql
SELECT 
    u.username,
    COUNT(a.id) as article_count,
    AVG(a.views) as avg_views
FROM users u
LEFT JOIN articles a ON u.id = a.author_id
WHERE u.created_at >= '2024-01-01'
GROUP BY u.id, u.username
HAVING article_count > 5
ORDER BY avg_views DESC
LIMIT 10;
```

## 代码与数学公式混合测试

在机器学习中，我们经常需要实现损失函数：

```python
import torch
import torch.nn as nn

def ridge_loss(y_pred, y_true, lambda_reg=0.01):
    """
    Ridge回归损失函数
    """
    mse_loss = nn.MSELoss()(y_pred, y_true)
    l2_penalty = lambda_reg * torch.sum(torch.pow(y_pred, 2))
    return mse_loss + l2_penalty
```

对应的数学公式是：

$$\text{Loss} = \frac{1}{n}\sum_{i=1}^{n}(y_i - \hat{y_i})^2 + \lambda \sum_{j=1}^{p} \beta_j^2$$

其中：
- $n$ 是样本数量
- $y_i$ 是真实值，$\hat{y_i}$ 是预测值
- $\lambda$ 是正则化参数
- $\beta_j$ 是模型参数

## 错误处理测试
这是一个错误的公式：$\invalid{syntax}$，应该显示错误提示。