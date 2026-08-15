import { describe, it, expect } from 'vitest';
import { SummaryExtractor } from '../src/utils/summaryExtractor';

describe('SummaryExtractor.extractSummary', () => {
  it('returns empty for invalid input', () => {
    expect(SummaryExtractor.extractSummary('')).toBe('');
    expect(SummaryExtractor.extractSummary(undefined as any)).toBe('');
    expect(SummaryExtractor.extractSummary(null as any)).toBe('');
  });

  it('extracts from markdown', () => {
    const summary = SummaryExtractor.extractSummary(
      '# Hello\n\nThis is a **test** paragraph with enough text to summarize.',
      'auto',
      100
    );
    expect(summary.length).toBeGreaterThan(0);
    expect(summary.length).toBeLessThanOrEqual(100);
    expect(summary).not.toContain('#');
  });

  it('extracts from HTML source', () => {
    const summary = SummaryExtractor.extractSummary(
      '<p>First paragraph with meaningful content.</p><p>Second one here.</p>',
      'html_source',
      200
    );
    expect(summary).toContain('First');
  });

  it('truncates to maxLength', () => {
    const long = 'word '.repeat(200);
    const summary = SummaryExtractor.extractSummary(long, 'markdown', 50);
    expect(summary.length).toBeLessThanOrEqual(60); // 允许省略号
  });

  it('explicit content type avoids auto-detect', () => {
    const summary = SummaryExtractor.extractSummary(
      '# heading\nbody text',
      'markdown',
      100
    );
    expect(summary).not.toBe('');
  });
});
