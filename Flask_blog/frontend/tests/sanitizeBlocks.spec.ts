import { describe, it, expect } from 'vitest'
import { sanitizeBlockHtml, isEmbedAllowed, isAttachmentUrlSafe } from '../src/utils/sanitizeBlocks'
import { blocksFromMarkdown } from '../src/utils/blocksFromMarkdown'

describe('sanitizeBlockHtml', () => {
  it('strips script tags', () => {
    const out = sanitizeBlockHtml('<p>ok</p><script>alert(1)<\/script>')
    expect(out).not.toContain('<script')
    expect(out).toContain('ok')
  })

  it('strips inline event handlers', () => {
    const out = sanitizeBlockHtml('<img src="x.png" onerror="alert(1)">')
    expect(out).not.toContain('onerror')
    expect(out).toContain('src="x.png"')
  })

  it('strips javascript: hrefs', () => {
    const out = sanitizeBlockHtml('<a href="javascript:alert(1)">点我</a>')
    expect(out.toLowerCase()).not.toContain('javascript:')
    expect(out).toContain('点我')
  })

  it('keeps benign markdown output intact', () => {
    const html = '<strong>重点</strong> 和 <a href="/article/x" rel="noopener">链接</a>'
    const out = sanitizeBlockHtml(html)
    expect(out).toContain('<strong>重点</strong>')
    expect(out).toContain('href="/article/x"')
  })
})

describe('blocksFromMarkdown XSS hardening (D3 红线)', () => {
  it('markdown containing raw <script> renders without script in any block html', () => {
    const md = '正常段落\n\n<script>alert(1)<\/script>\n\n![x](/a.png "onerror=alert(1)")'
    const blocks = blocksFromMarkdown(md)
    for (const b of blocks) {
      const json = JSON.stringify(b)
      expect(json).not.toContain('<script')
      expect(json).not.toContain('onerror=')
    }
  })

  it('html_block with event handlers gets sanitized', () => {
    const md = '<div onclick="steal()">点击</div>'
    const blocks = blocksFromMarkdown(md)
    const joined = blocks.map((b) => (b as any).html || '').join('')
    expect(joined).not.toContain('onclick')
    expect(joined).toContain('点击')
  })
})

describe('embed / attachment URL policy', () => {
  it('blocks external embeds when whitelist is empty (P0)', () => {
    expect(isEmbedAllowed('https://evil.example.com/frame')).toBe(false)
  })

  it('allows same-origin embeds only', () => {
    expect(isEmbedAllowed('/local/demo')).toBe(true)
    expect(isEmbedAllowed(window.location.origin + '/local/demo')).toBe(true)
  })

  it('attachment allows relative paths only', () => {
    expect(isAttachmentUrlSafe('/files/report.pdf')).toBe(true)
    expect(isAttachmentUrlSafe('https://cdn.example.com/a.pdf')).toBe(false)
    expect(isAttachmentUrlSafe('//protocol-relative/x')).toBe(false)
  })
})
