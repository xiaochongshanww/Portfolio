import { renderMarkdown } from '../src/utils/markdownProcessor.simple.js';

const sample = `**L2 惩罚项的数学表达式为：**

$$
\\text{L2 Penalty} = \\lambda \\sum_{j=1}^{p} \\beta_j^2
$$

**其中：**

* **βj 是模型第 j 个特征的系数。**
* **p 是特征的总数。**
`;

(async () => {
  try {
    console.log('Rendering sample...');
    const out = await renderMarkdown(sample);
    console.log('--- OUTPUT START ---');
    console.log(out.substring(0, 2000));
    console.log('--- OUTPUT END ---');
    console.log('.katex present?', out.includes('class="katex"') || out.includes('katex'));
  } catch (e) {
    console.error('Error during render:', e);
  }
})();
