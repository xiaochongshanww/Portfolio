/**
 * 用户显示名称工具函数
 * 统一处理用户在界面上的显示名称，提供智能回退和长度控制
 */

/**
 * 获取用户显示名称
 * @param {Object} user - 用户对象
 * @param {string} user.nickname - 用户昵称
 * @param {string} user.email - 用户邮箱
 * @param {number} user.id - 用户ID
 * @param {Object} options - 配置选项
 * @param {number} options.maxLength - 最大显示长度，默认12
 * @param {boolean} options.showEmail - 无昵称时是否显示邮箱前缀，默认true
 * @param {string} options.fallback - 最终回退文本，默认"用户"
 * @returns {string} 处理后的显示名称
 */
export function getUserDisplayName(user, options = {}) {
  const {
    maxLength = 12,
    showEmail = true,
    fallback = '用户'
  } = options

  if (!user) {
    return fallback
  }

  // 优先使用昵称
  if (user.nickname && user.nickname.trim()) {
    const nickname = user.nickname.trim()
    return truncateText(nickname, maxLength)
  }

  // 其次使用邮箱前缀（如果允许）
  if (showEmail && user.email) {
    const emailPrefix = getEmailPrefix(user.email)
    if (emailPrefix && emailPrefix !== user.email) {
      return truncateText(emailPrefix, maxLength)
    }
  }

  // 最后使用ID回退（避免显示"用户"）
  if (user.id) {
    return `${fallback}${user.id}`
  }

  return fallback
}

/**
 * 获取用户简短显示名称（用于小空间）
 * @param {Object} user - 用户对象
 * @param {number} maxLength - 最大长度，默认8
 * @returns {string} 简短显示名称
 */
export function getUserShortName(user, maxLength = 8) {
  return getUserDisplayName(user, { 
    maxLength, 
    showEmail: true, 
    fallback: 'U' 
  })
}

/**
 * 获取用户完整显示名称（用于详情页）
 * @param {Object} user - 用户对象
 * @returns {string} 完整显示名称
 */
export function getUserFullName(user) {
  return getUserDisplayName(user, { 
    maxLength: 50, 
    showEmail: true, 
    fallback: '匿名用户' 
  })
}

/**
 * 检查用户是否需要完善昵称
 * @param {Object} user - 用户对象
 * @returns {boolean} 是否需要完善昵称
 */
export function shouldPromptNickname(user) {
  return user && (!user.nickname || !user.nickname.trim())
}

/**
 * 从邮箱提取用户名前缀
 * @param {string} email - 邮箱地址
 * @returns {string} 邮箱前缀
 */
function getEmailPrefix(email) {
  if (!email || typeof email !== 'string') {
    return ''
  }

  const prefix = email.split('@')[0]
  
  // 过滤掉纯数字或过短的前缀
  if (prefix.length < 2 || /^\d+$/.test(prefix)) {
    return ''
  }

  // 过滤掉常见的临时邮箱模式
  const tempEmailPatterns = [
    /^temp/i,
    /^test/i,
    /^\d+[a-z]+\d+$/,
    /^[a-z]+\d+$/
  ]

  if (tempEmailPatterns.some(pattern => pattern.test(prefix))) {
    return ''
  }

  return prefix
}

/**
 * 截断文本并添加省略号
 * @param {string} text - 原始文本
 * @param {number} maxLength - 最大长度
 * @returns {string} 截断后的文本
 */
function truncateText(text, maxLength) {
  if (!text || typeof text !== 'string') {
    return ''
  }

  if (text.length <= maxLength) {
    return text
  }

  return text.slice(0, maxLength - 1) + '…'
}

/**
 * 获取用户显示名称的提示信息
 * @param {Object} user - 用户对象
 * @returns {string} 提示信息
 */
export function getUserDisplayHint(user) {
  if (!user) {
    return ''
  }

  if (user.nickname && user.nickname.trim()) {
    return `昵称: ${user.nickname}`
  }

  if (user.email) {
    return `邮箱: ${user.email}`
  }

  return `用户ID: ${user.id}`
}

/**
 * 生成用户设置昵称的建议
 * @param {Object} user - 用户对象
 * @returns {Object} 建议信息
 */
export function getNicknameSuggestion(user) {
  if (!user || !shouldPromptNickname(user)) {
    return null
  }

  const emailPrefix = user.email ? getEmailPrefix(user.email) : ''
  
  return {
    shouldPrompt: true,
    message: '设置个人昵称，让其他用户更容易记住您',
    suggestion: emailPrefix || `用户${user.id}`,
    action: '去设置'
  }
}