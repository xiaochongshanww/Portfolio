/**
 * Vditor 图片上传工具函数。
 * 处理 CDN 上传、媒体库上传、粘贴上传、Markdown 图片处理。
 */

import apiClient from '@/apiClient'


function getBestVariant(variants: any[], label: string): string | null {
  if (!variants || !variants.length) return null
  const v = variants.find((x: any) => x.label === label)
  return v?.url || null
}


function parseUploadResponse(msg: string) {
  try {
    const response = JSON.parse(msg)
    const data = response.data || response
    if (!data) return null

    // 尝试多尺寸变体
    const rawVariants = data.variants || (data.data?.variants)
    const variants = Array.isArray(rawVariants) ? rawVariants
      : rawVariants?.variants || []

    const mdUrl = getBestVariant(variants, 'md')
    const smUrl = getBestVariant(variants, 'sm')
    const fallbackUrl = data.url || data.url_sm || data.url_md

    return {
      url: mdUrl || smUrl || fallbackUrl || data.url,
      width: data.width,
      height: data.height,
    }
  } catch {
    return null
  }
}


export function getUploadConfig(token: string) {
  return {
    url: '/api/v1/media/upload',
    headers: { 'Authorization': `Bearer ${token}` },
    accept: 'image/jpeg,image/png,image/webp,image/gif',
    filename() { return 'file' },
    success(editor: any, msg: string) {
      const info = parseUploadResponse(msg)
      if (info?.url) {
        editor.insertValue(`![image](${info.url})`)
      }
    },
    error(msg: string) {
      console.error('Upload failed:', msg)
    },
  }
}


export async function uploadImageFile(file: File): Promise<string | null> {
  try {
    const formData = new FormData()
    formData.append('file', file)
    const response = await apiClient.post('/media/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    const data = response.data?.data || response.data
    if (!data) return null

    const variants = Array.isArray(data.variants)
      ? data.variants : data.variants?.variants || []

    const mdUrl = getBestVariant(variants, 'md')
    const smUrl = getBestVariant(variants, 'sm')
    return mdUrl || smUrl || data.url || null
  } catch (e) {
    console.error('Upload failed:', e)
    return null
  }
}


export async function processMarkdownImages(content: string): Promise<string> {
  const imageRegex = /!\[([^\]]*)\]\(([^)]+)\)/g
  const matches = Array.from(content.matchAll(imageRegex))
  if (!matches.length) return content

  let result = content
  for (const [, altText, imagePath] of matches) {
    const isLocalPath =
      imagePath.startsWith('file://') ||
      imagePath.startsWith('/Users/') ||
      imagePath.startsWith('/home/') ||
      imagePath.startsWith('C:') ||
      imagePath.startsWith('D:')

    if (isLocalPath) {
      const placeholder = `![${altText || '图片'}](本地图片-请拖拽或粘贴图片文件)`
      result = result.replace(imagePath, placeholder)
    }
  }
  return result
}
