/**
 * 文章内容系统 Block 类型定义
 * 来源: docs/design/blog-redesign-2026-08/03_文章内容系统与Block规范.md 第 3/24 节
 */

export type BlockWidth = 'text' | 'code' | 'wide' | 'xwide'

export interface BaseBlock {
  id: string
  type: string
  width?: BlockWidth
}

export interface ParagraphBlock extends BaseBlock {
  type: 'paragraph'
  html: string
}

export interface HeadingBlock extends BaseBlock {
  type: 'heading'
  level: number
  text: string
  /** 稳定 slug id,供 TOC 与锚点使用 */
  anchor: string
}

export interface ListItem {
  html: string
}

export interface ListBlock extends BaseBlock {
  type: 'list'
  ordered: boolean
  items: ListItem[]
}

export interface QuoteBlock extends BaseBlock {
  type: 'quote'
  html: string
  cite?: string
}

export type CalloutTone = 'info' | 'warning' | 'success' | 'note'

export interface CalloutBlock extends BaseBlock {
  type: 'callout'
  tone: CalloutTone
  title?: string
  html: string
}

export interface CodeBlock extends BaseBlock {
  type: 'code'
  language: string
  filename?: string
  code: string
  highlightLines?: number[]
  showLineNumbers?: boolean
}

export interface ImageBlock extends BaseBlock {
  type: 'image'
  src: string
  alt: string
  caption?: string
  zoomable?: boolean
}

export interface GalleryItem {
  src: string
  alt: string
  caption?: string
}

export interface GalleryBlock extends BaseBlock {
  type: 'gallery'
  items: GalleryItem[]
  layout?: 'grid' | 'compare' | 'carousel'
}

export interface TableBlock extends BaseBlock {
  type: 'table'
  /** 表头单元格 html */
  head: string[]
  /** 每行为一组单元格 html */
  rows: string[][]
  caption?: string
  align?: Array<'left' | 'center' | 'right'>
}

export interface DiagramBlock extends BaseBlock {
  type: 'diagram'
  format: 'mermaid' | 'svg' | 'custom'
  source: string
  caption?: string
}

export interface EmbedBlock extends BaseBlock {
  type: 'embed'
  title: string
  component?: string
  src?: string
  openInNewWindow?: boolean
}

export interface MediaBlock extends BaseBlock {
  type: 'media'
  mediaType: 'video' | 'audio' | 'external'
  title: string
  src: string
  poster?: string
  duration?: number
  caption?: string
}

export interface AttachmentBlock extends BaseBlock {
  type: 'attachment'
  name: string
  fileType: string
  size?: number
  url: string
  updatedAt?: string
}

export interface TabItem {
  label: string
  content: ArticleBlock[]
}

export interface TabsBlock extends BaseBlock {
  type: 'tabs'
  tabs: TabItem[]
}

/** 预留:自定义组件 Block */
export interface CustomBlock extends BaseBlock {
  type: 'custom'
  componentName: string
  props?: Record<string, unknown>
}

export type ArticleBlock =
  | ParagraphBlock
  | HeadingBlock
  | ListBlock
  | QuoteBlock
  | CalloutBlock
  | CodeBlock
  | ImageBlock
  | GalleryBlock
  | TableBlock
  | DiagramBlock
  | EmbedBlock
  | MediaBlock
  | AttachmentBlock
  | TabsBlock
  | CustomBlock

/** 03 号规范第 4 节宽度映射表:P0 渲染器按此默认值套 content-width-* 类 */
export const DEFAULT_BLOCK_WIDTH: Record<string, BlockWidth> = {
  paragraph: 'text',
  heading: 'text',
  list: 'text',
  quote: 'text',
  callout: 'text',
  code: 'code',
  attachment: 'text',
  media: 'text',
  table: 'wide',
  image: 'wide',
  diagram: 'wide',
  gallery: 'xwide',
  embed: 'xwide',
  tabs: 'text',
  custom: 'text',
}
