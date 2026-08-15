import { describe, it, expect } from 'vitest';
import {
  ContentTypeDetector,
  detectContentType,
  getTypeDescription,
} from '../src/utils/contentTypeDetector';

describe('ContentTypeDetector.analyzeContent', () => {
  it('returns markdown for empty/invalid input', () => {
    expect(ContentTypeDetector.analyzeContent('').type).toBe('markdown');
    expect(ContentTypeDetector.analyzeContent(undefined as any).type).toBe('markdown');
    expect(ContentTypeDetector.analyzeContent(null as any).type).toBe('markdown');
  });

  it('detects plain markdown', () => {
    const result = ContentTypeDetector.analyzeContent('# Title\n\nSome **bold** text');
    expect(result.type).toBe('markdown');
    expect(result.confidence).toBeGreaterThan(0);
  });

  it('detects strong HTML (table)', () => {
    const result = ContentTypeDetector.analyzeContent(
      '<table><tr><td>a</td></tr></table>'
    );
    expect(result.type).toBe('html_source');
  });

  it('detects HTML with inline styles and complex structure', () => {
    const result = ContentTypeDetector.analyzeContent(
      '<div style="color:red"><section><article>x</article></section></div>'
    );
    expect(result.type).toBe('html_source');
  });
});

describe('ContentTypeDetector counters', () => {
  it('countHTMLTags', () => {
    expect(ContentTypeDetector.countHTMLTags('<p>a</p><br/>')).toBe(3);
    expect(ContentTypeDetector.countHTMLTags('no html')).toBe(0);
  });

  it('countInlineStyles', () => {
    expect(ContentTypeDetector.countInlineStyles('<div style="color:red">x</div>')).toBe(1);
    expect(ContentTypeDetector.countInlineStyles('none')).toBe(0);
  });

  it('countComplexStructures', () => {
    expect(ContentTypeDetector.countComplexStructures('<div><span>a</span></div>')).toBe(2);
  });

  it('countMarkdownPatterns', () => {
    const md = '# h\n\n- item\n- item2\n\n`code`\n\n**bold**\n\n[link](url)\n\n> quote';
    expect(ContentTypeDetector.countMarkdownPatterns(md)).toBeGreaterThan(0);
  });

  it('detectSpecialHTMLFeatures', () => {
    const f = ContentTypeDetector.detectSpecialHTMLFeatures(
      '<div class="x" id="y" data-a="1"><table></table><img src="z"/></div>'
    );
    expect(f.hasCSSClasses).toBe(true);
    expect(f.hasIDs).toBe(true);
    expect(f.hasDataAttributes).toBe(true);
    expect(f.hasTableStructure).toBe(true);
    expect(f.hasMediaElements).toBe(true);
  });
});

describe('ContentTypeDetector helpers', () => {
  it('hasStrongHTMLIndicators for table', () => {
    const analysis = {
      htmlTagCount: 5,
      inlineStyleCount: 0,
      complexStructureCount: 0,
      markdownPatterns: 0,
      totalLength: 50,
      hasSpecialHTMLFeatures: { hasTableStructure: true },
    } as any;
    expect(ContentTypeDetector.hasStrongHTMLIndicators(analysis)).toBe(true);
  });

  it('calculateHTMLFeatureScore caps at 5', () => {
    const score = ContentTypeDetector.calculateHTMLFeatureScore({
      inlineStyleCount: 10,
      complexStructureCount: 10,
      htmlDensity: 10,
      hasSpecialHTMLFeatures: { a: true, b: true, c: true, d: true, e: true, f: true, g: true },
    } as any);
    expect(score).toBeLessThanOrEqual(5);
  });

  it('calculateMarkdownFeatureScore caps at 3', () => {
    expect(ContentTypeDetector.calculateMarkdownFeatureScore(100)).toBe(3);
  });

  it('getTypeDescription', () => {
    expect(ContentTypeDetector.getTypeDescription({ type: 'html_source', confidence: 0.9 } as any)).toContain('HTML');
    expect(ContentTypeDetector.getTypeDescription({ type: 'markdown', confidence: 0.9 } as any)).toContain('Markdown');
  });

  it('batchAnalyze', () => {
    const results = ContentTypeDetector.batchAnalyze(['# md', '<table></table>']);
    expect(results).toHaveLength(2);
    expect(results[0].index).toBe(0);
    expect(() => ContentTypeDetector.batchAnalyze('not-array' as any)).toThrow();
  });
});

describe('exported helpers', () => {
  it('detectContentType and getTypeDescription', () => {
    const result = detectContentType('# title');
    expect(result.type).toBe('markdown');
    expect(getTypeDescription(result)).toContain('Markdown');
  });
});
