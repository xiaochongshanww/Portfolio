import { describe, it, expect } from 'vitest';
import {
  HTMLMathProcessor,
  processHTMLMath,
  containsMathFormulas,
} from '../src/utils/htmlMathProcessor';

describe('HTMLMathProcessor', () => {
  it('returns input unchanged for empty/non-string', () => {
    expect(HTMLMathProcessor.processHTMLMath('')).toBe('');
    expect(HTMLMathProcessor.processHTMLMath(undefined as any)).toBeUndefined();
  });

  it('renders inline math $...$', () => {
    const out = HTMLMathProcessor.processHTMLMath('E = $mc^2$');
    expect(out).toContain('katex');
    expect(out).not.toContain('$mc^2$');
  });

  it('renders display math $$...$$', () => {
    const out = HTMLMathProcessor.processHTMLMath('$$x^2 + y^2 = z^2$$');
    expect(out).toContain('katex');
  });

  it('renders latex inline \\(...\\)', () => {
    const out = HTMLMathProcessor.processHTMLMath('\\(a+b\\)');
    expect(out).toContain('katex');
  });

  it('counts math formulas', () => {
    expect(HTMLMathProcessor.countMathFormulas('$a$ and $$b$$')).toBe(2);
    expect(HTMLMathProcessor.countMathFormulas('no math')).toBe(0);
  });

  it('counts katex elements', () => {
    const out = HTMLMathProcessor.processHTMLMath('$a$');
    expect(HTMLMathProcessor.countKatexElements(out)).toBeGreaterThan(0);
  });

  it('containsMathFormulas detects markers', () => {
    expect(containsMathFormulas('$e=mc^2$')).toBe(true);
    expect(containsMathFormulas('plain text')).toBe(false);
    expect(containsMathFormulas('')).toBe(false);
  });

  it('preprocessHTML protects code/pre ranges', () => {
    const { protectedRanges } = HTMLMathProcessor.preprocessHTML(
      '<code>$not-math$</code> and <pre>$$block$$</pre>'
    );
    expect(protectedRanges.length).toBe(2);
  });

  it('isProtectedPosition', () => {
    const ranges = [{ start: 0, end: 5 }];
    expect(HTMLMathProcessor.isProtectedPosition(3, ranges)).toBe(true);
    expect(HTMLMathProcessor.isProtectedPosition(10, ranges)).toBe(false);
  });

  it('processHTMLMath export works', () => {
    expect(processHTMLMath('$x$')).toContain('katex');
  });
});
