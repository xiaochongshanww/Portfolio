import { describe, it, expect } from 'vitest';
import { roundTrip } from '../src/utils/editorConversion';

describe('editor conversion round-trip', () => {
  it('preserves basic markdown', () => {
    const md = '# 标题\n\n段落 **bold** _italic_';
    const rt = roundTrip(md);
    expect(rt).toContain('标题');
    expect(rt).toMatch(/bold/);
  });
  it('preserves video shortcode', () => {
    const md = ':::video https://youtu.be/abc123:::';
    const rt = roundTrip(md);
    expect(rt).toMatch(/video-embed|youtu/);
  });
  it('preserves gist shortcode', () => {
    const md = ':::gist https://gist.github.com/user/hash:::';
    const rt = roundTrip(md);
    expect(rt).toMatch(/embed-gist/);
  });
});
