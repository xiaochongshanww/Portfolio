/**
 * Vditor 工具栏配置。
 * 按功能分组，便于维护和定制。
 */

const MODE_SWITCH = {
  name: 'modeSwitch',
  tipPosition: 's' as const,
}

const HEADINGS = {
  name: 'headings',
  tipPosition: 's' as const,
}

const BOLD = {
  name: 'bold',
  tipPosition: 's' as const,
}

const ITALIC = {
  name: 'italic',
  tipPosition: 's' as const,
}

const STRIKE = {
  name: 'strike',
  tipPosition: 's' as const,
}

const LINE = {
  name: 'line',
  tipPosition: 's' as const,
}

const QUOTE = {
  name: 'quote',
  tipPosition: 's' as const,
}

const LIST = {
  name: 'list',
  tipPosition: 's' as const,
}

const ORDERED_LIST = {
  name: 'ordered-list',
  tipPosition: 's' as const,
}

const CHECK = {
  name: 'check',
  tipPosition: 's' as const,
}

const OUTLINE = {
  name: 'outline',
  tipPosition: 's' as const,
}

const CODE = {
  name: 'code',
  tipPosition: 's' as const,
}

const INLINE_CODE = {
  name: 'inline-code',
  tipPosition: 's' as const,
}

const PREVIEW = {
  name: 'preview',
  tipPosition: 's' as const,
}

const FULLSCREEN = {
  name: 'fullscreen',
  tipPosition: 's' as const,
}

const INFO = {
  name: 'info',
  tipPosition: 's' as const,
}

const HELP = {
  name: 'help',
  tipPosition: 's' as const,
}

const UNDO = {
  name: 'undo',
  tipPosition: 's' as const,
}

const REDO = {
  name: 'redo',
  tipPosition: 's' as const,
}

const TABLE = {
  name: 'table',
  tipPosition: 's' as const,
}

const EDIT = {
  name: 'edit',
  tipPosition: 's' as const,
}

const BOTH = {
  name: 'both',
  tipPosition: 's' as const,
}

const DEVTOOLS = {
  name: 'devtools',
  tipPosition: 's' as const,
}

const EMOJI = {
  name: 'emoji',
  tipPosition: 's' as const,
}

const SUBSCRIPT = {
  name: 'subscript',
  tipPosition: 's' as const,
}

const SUPERSCRIPT = {
  name: 'superscript',
  tipPosition: 's' as const,
}

const BACKLINK = {
  name: 'backlink',
  tipPosition: 's' as const,
}


/** 完整工具栏配置（适用于新建/编辑文章） */
export const FULL_TOOLBAR: any[] = [
  MODE_SWITCH,
  '|',
  HEADINGS,
  BOLD,
  ITALIC,
  STRIKE,
  '|',
  LINE,
  QUOTE,
  LIST,
  ORDERED_LIST,
  CHECK,
  '|',
  CODE,
  INLINE_CODE,
  TABLE,
  '|',
  UNDO,
  REDO,
  '|',
  OUTLINE,
  PREVIEW,
  FULLSCREEN,
  INFO,
  HELP,
  '|',
  EDIT,
  BOTH,
  DEVTOOLS,
  EMOJI,
  SUBSCRIPT,
  SUPERSCRIPT,
  BACKLINK,
]


/** 精简工具栏（适用于快速评论/短内容） */
export const MINIMAL_TOOLBAR: any[] = [
  BOLD,
  ITALIC,
  STRIKE,
  '|',
  QUOTE,
  LIST,
  ORDERED_LIST,
  '|',
  CODE,
  INLINE_CODE,
  '|',
  UNDO,
  REDO,
]
