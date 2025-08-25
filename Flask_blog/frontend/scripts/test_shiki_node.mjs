import MarkdownIt from 'markdown-it';
import { fromHighlighter } from '@shikijs/markdown-it';
import { createHighlighter } from 'shiki';

const sample = "```js\nfunction add(a, b) {\n  return a + b;\n}\n```\n";

(async () => {
  try {
    console.log('Creating shiki highlighter...');
    const highlighter = await createHighlighter({ themes: ['github-light'], langs: ['javascript'] });
    console.log('Highlighter created:', !!highlighter);

    const md = MarkdownIt({ html: true }).use(fromHighlighter(highlighter, { theme: 'github-light' }));
    const out = md.render(sample);
    console.log('Rendered HTML length:', out.length);
    console.log('Output sample:', out.substring(0, 800));
  } catch (e) {
    console.error('Test failed:', e);
  }
})();
