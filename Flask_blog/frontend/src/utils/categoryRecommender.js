/**
 * 智能分类推荐工具
 * 基于文章标题、内容和标签智能推荐相关分类
 */

/**
 * 分类关键词映射表
 * 根据内容特征推荐对应分类
 */
const CATEGORY_KEYWORDS = {
  // 具体技术分类
  'Vue.js': [
    'vue', 'vuejs', 'vue.js', 'composition api', 'vue3', 'vue 3', 'vite', 'nuxt',
    'vue router', 'vuex', 'pinia', '组合式', '选项式', 'reactive', 'ref', 'computed'
  ],
  'React': [
    'react', 'reactjs', 'jsx', 'hooks', 'usestate', 'useeffect', 'nextjs', 'redux',
    'react router', 'react native', 'component', 'props', 'state'
  ],
  'JavaScript': [
    'javascript', 'js', 'es6', 'es2015', 'typescript', 'nodejs', 'node.js',
    'async', 'await', 'promise', 'callback', 'closure', 'prototype', 'dom'
  ],
  'Python': [
    'python', 'py', 'python3', 'pip', 'virtualenv', 'conda', 'jupyter', 'pandas',
    'numpy', 'matplotlib', 'requests', 'beautifulsoup', 'scrapy'
  ],
  'Flask': [
    'flask', 'python web', 'jinja2', 'werkzeug', 'sqlalchemy', 'blueprint',
    'api', 'rest', 'restful', 'web framework', 'micro framework'
  ],
  'Django': [
    'django', 'python web', 'orm', 'model', 'view', 'template', 'admin',
    'migration', 'middleware', 'web framework'
  ],
  '机器学习': [
    'machine learning', 'ml', 'scikit-learn', 'sklearn', 'supervised', 'unsupervised',
    'regression', 'classification', 'clustering', '算法', '模型', '训练'
  ],
  '深度学习': [
    'deep learning', 'dl', 'neural network', 'tensorflow', 'pytorch', 'keras',
    'cnn', 'rnn', 'lstm', 'transformer', 'bert', 'gpt', '神经网络'
  ],
  // 技术分类
  '前端开发': [
    'vue', 'react', 'angular', 'javascript', 'typescript', 'html', 'css', 'sass', 'scss',
    'webpack', 'vite', 'npm', 'yarn', 'babel', 'eslint', 'prettier', '前端', '组件',
    'dom', 'ajax', 'fetch', 'axios', '响应式', '移动端', 'pwa', 'spa'
  ],
  '后端开发': [
    'python', 'java', 'nodejs', 'golang', 'rust', 'php', 'ruby', 'spring', 'django',
    'flask', 'express', 'koa', 'fastapi', 'laravel', 'rails', '后端', 'api',
    'restful', 'graphql', 'microservice', '微服务', '服务器', 'server'
  ],
  '数据库': [
    'mysql', 'postgresql', 'mongodb', 'redis', 'elasticsearch', 'sqlite', 'oracle',
    'mariadb', 'cassandra', 'dynamodb', '数据库', 'sql', 'nosql', '索引', '查询',
    '事务', 'acid', '备份', '迁移', 'orm', 'sequelize', 'mongoose'
  ],
  '移动开发': [
    'android', 'ios', 'kotlin', 'swift', 'flutter', 'react native', 'ionic',
    '移动应用', 'app', '安卓', '苹果', 'xcode', 'android studio', '移动端'
  ],
  '人工智能': [
    'machine learning', 'deep learning', 'neural network', 'ai', 'ml', 'dl',
    'tensorflow', 'pytorch', 'scikit-learn', 'pandas', 'numpy', 'jupyter',
    '机器学习', '深度学习', '神经网络', '人工智能', 'nlp', 'cv', '计算机视觉'
  ],
  '云计算': [
    'aws', 'azure', 'gcp', 'docker', 'kubernetes', 'terraform', 'jenkins',
    'devops', 'ci/cd', '容器', '微服务', '云原生', '自动化部署', '监控'
  ],
  '设计': [
    'ui', 'ux', 'design', 'figma', 'sketch', 'photoshop', 'illustrator',
    '用户体验', '用户界面', '交互设计', '视觉设计', '原型', '设计模式',
    '色彩', '字体', '布局', '图标', '品牌', 'logo'
  ],
  '产品管理': [
    'product', 'pm', '产品经理', '需求', '原型', '竞品分析', '用户研究',
    'prd', 'mvp', '敏捷', 'scrum', '项目管理', '产品设计', '产品规划'
  ],
  '创业': [
    'startup', '创业', '商业模式', '融资', '投资', '商业计划', 'vc', 'angel',
    '创新', '企业家', '市场', '营销', '品牌', '战略', '管理', '团队'
  ],
  '生活方式': [
    '生活', '健康', '旅行', '美食', '摄影', '读书', '音乐', '电影',
    '运动', '健身', '瑜伽', '冥想', '心理健康', '个人成长', '时间管理'
  ]
};

/**
 * 热门分类权重配置
 */
const POPULAR_CATEGORIES_BOOST = {
  '前端开发': 1.3,
  '后端开发': 1.2,
  '人工智能': 1.5,
  '云计算': 1.1,
  '移动开发': 1.1
};

/**
 * 文本预处理
 * @param {string} text - 原始文本
 * @returns {string} 预处理后的文本
 */
function preprocessText(text) {
  if (!text) return '';
  
  return text
    .toLowerCase()
    .replace(/[^\w\s\u4e00-\u9fa5]/g, ' ') // 保留中英文字符和数字
    .replace(/\s+/g, ' ')
    .trim();
}

/**
 * 计算文本相似度得分
 * @param {string} text - 待分析文本
 * @param {string[]} keywords - 关键词列表
 * @returns {number} 相似度得分
 */
function calculateSimilarityScore(text, keywords) {
  const processedText = preprocessText(text);
  let score = 0;
  let matchedKeywords = new Set();
  
  keywords.forEach(keyword => {
    const processedKeyword = preprocessText(keyword);
    
    // 完全匹配
    if (processedText.includes(processedKeyword)) {
      score += keyword.length > 3 ? 2 : 1; // 长关键词权重更高
      matchedKeywords.add(keyword);
    }
    
    // 部分匹配（适用于复合词）
    const words = processedText.split(' ');
    words.forEach(word => {
      if (word.length > 2 && processedKeyword.includes(word)) {
        score += 0.5;
      }
    });
  });
  
  // 根据匹配关键词数量给予额外加分
  const matchRatio = matchedKeywords.size / keywords.length;
  score += matchRatio * 5;
  
  return score;
}

/**
 * 基于标签推荐分类
 * @param {string[]} tags - 文章标签
 * @param {Object[]} categories - 可用分类列表
 * @returns {Object[]} 推荐分类及得分
 */
function recommendByTags(tags, categories) {
  if (!tags || !Array.isArray(tags) || tags.length === 0) return [];
  
  const recommendations = [];
  const tagText = tags.join(' ');
  
  Object.entries(CATEGORY_KEYWORDS).forEach(([categoryName, keywords]) => {
    const score = calculateSimilarityScore(tagText, keywords);
    if (score > 0) {
      const category = categories.find(cat => 
        cat.name === categoryName || 
        cat.name.toLowerCase().includes(categoryName.toLowerCase())
      );
      if (category) {
        recommendations.push({
          category,
          score: score * 1.5, // 标签匹配权重较高
          reason: '基于标签匹配'
        });
      }
    }
  });
  
  return recommendations;
}

/**
 * 基于内容推荐分类
 * @param {string} title - 文章标题
 * @param {string} content - 文章内容
 * @param {string} summary - 文章摘要
 * @param {Object[]} categories - 可用分类列表
 * @returns {Object[]} 推荐分类及得分
 */
function recommendByContent(title, content, summary, categories) {
  const recommendations = [];
  
  console.log('📊 内容推荐分析 - 输入数据:', { 
    title, 
    content: content?.substring(0, 100) + '...', 
    summary,
    contentLength: content?.length || 0
  });
  console.log('📊 可用分类数量:', categories?.length || 0);
  console.log('📊 分类数据类型:', typeof categories, Array.isArray(categories));
  
  if (!categories || !Array.isArray(categories)) {
    console.error('❌ 分类数据无效:', categories);
    return [];
  }
  
  console.log('📊 可用分类:', categories.map(cat => `${cat.name}(ID:${cat.id})`));
  
  // 组合所有文本内容，标题权重最高
  const combinedText = [
    title ? title.repeat(3) : '', // 标题重复3次增加权重
    summary ? summary.repeat(2) : '', // 摘要重复2次
    content || ''
  ].join(' ');
  
  console.log('📝 组合文本内容:', combinedText.substring(0, 200) + '...');
  
  Object.entries(CATEGORY_KEYWORDS).forEach(([categoryName, keywords]) => {
    let score = calculateSimilarityScore(combinedText, keywords);
    
    console.log(`🔍 分析分类 "${categoryName}": 得分=${score}`);
    
    // 应用热门分类权重加成
    if (POPULAR_CATEGORIES_BOOST[categoryName]) {
      score *= POPULAR_CATEGORIES_BOOST[categoryName];
      console.log(`⭐ 应用权重加成 ${POPULAR_CATEGORIES_BOOST[categoryName]}: 新得分=${score}`);
    }
    
    if (score > 0) {
      // 更灵活的分类匹配策略
      const category = categories.find(cat => {
        const exact = cat.name === categoryName;
        const contains = cat.name.toLowerCase().includes(categoryName.toLowerCase());
        const reverseContains = categoryName.toLowerCase().includes(cat.name.toLowerCase());
        
        // 特殊匹配规则 - 技术到分类的映射
        const specialMatches = {
          '前端开发': ['Vue.js', 'React', 'JavaScript', 'vue', 'react', 'javascript'].some(tech => 
            cat.name.toLowerCase().includes(tech.toLowerCase()) || tech.toLowerCase().includes(cat.name.toLowerCase())
          ),
          '后端开发': ['Python', 'Flask', 'Django', 'python', 'flask', 'django'].some(tech => 
            cat.name.toLowerCase().includes(tech.toLowerCase()) || tech.toLowerCase().includes(cat.name.toLowerCase())
          ),
          '人工智能': ['机器学习', '深度学习', 'machine learning', 'deep learning'].some(tech => 
            cat.name.toLowerCase().includes(tech.toLowerCase()) || tech.toLowerCase().includes(cat.name.toLowerCase())
          )
        };
        
        const match = exact || contains || reverseContains || specialMatches[categoryName];
        
        if (match) {
          console.log(`✅ 找到匹配分类: "${cat.name}" 匹配 "${categoryName}"`);
        }
        
        return match;
      });
      
      if (category) {
        recommendations.push({
          category,
          score,
          reason: '基于内容分析'
        });
        console.log(`➕ 添加推荐: ${category.name} (得分: ${score})`);
      } else {
        console.log(`❌ 未找到对应分类: "${categoryName}"`);
      }
    }
  });
  
  console.log(`📊 内容推荐结果: ${recommendations.length} 个推荐`);
  return recommendations;
}

/**
 * 智能推荐分类
 * @param {Object} articleData - 文章数据
 * @param {string} articleData.title - 文章标题
 * @param {string} articleData.content - 文章内容
 * @param {string} articleData.summary - 文章摘要
 * @param {string[]} articleData.tags - 文章标签
 * @param {Object[]} categories - 可用分类列表
 * @param {Object} options - 推荐选项
 * @returns {Object[]} 推荐结果
 */
export function recommendCategories(articleData, categories, options = {}) {
  const {
    maxRecommendations = 5,
    minScore = 1,
    includeReason = true
  } = options;
  
  if (!categories || categories.length === 0) {
    return [];
  }
  
  const { title = '', content = '', summary = '', tags = [] } = articleData;
  
  // 如果所有输入都为空，返回热门分类
  if (!title && !content && !summary && tags.length === 0) {
    return categories
      .filter(cat => POPULAR_CATEGORIES_BOOST[cat.name])
      .slice(0, maxRecommendations)
      .map(category => ({
        category,
        score: POPULAR_CATEGORIES_BOOST[category.name] || 1,
        reason: '热门分类推荐'
      }));
  }
  
  // 基于标签推荐
  const tagRecommendations = recommendByTags(tags, categories);
  
  // 基于内容推荐
  const contentRecommendations = recommendByContent(title, content, summary, categories);
  
  // 合并推荐结果
  const allRecommendations = [...tagRecommendations, ...contentRecommendations];
  
  // 按分类ID分组，合并得分
  const mergedRecommendations = new Map();
  
  allRecommendations.forEach(rec => {
    const categoryId = rec.category.id;
    if (mergedRecommendations.has(categoryId)) {
      const existing = mergedRecommendations.get(categoryId);
      existing.score += rec.score;
      existing.reasons = [...new Set([...existing.reasons, rec.reason])];
    } else {
      mergedRecommendations.set(categoryId, {
        category: rec.category,
        score: rec.score,
        reasons: [rec.reason]
      });
    }
  });
  
  // 转换为数组并排序
  const result = Array.from(mergedRecommendations.values())
    .filter(rec => rec.score >= minScore)
    .sort((a, b) => b.score - a.score)
    .slice(0, maxRecommendations)
    .map(rec => ({
      category: rec.category,
      score: rec.score,
      confidence: Math.min(rec.score / 10, 1), // 置信度 0-1
      reason: includeReason ? rec.reasons.join('、') : undefined
    }));
  
  return result;
}

/**
 * 获取相关分类建议
 * @param {number} selectedCategoryId - 已选分类ID
 * @param {Object[]} categories - 所有分类
 * @returns {Object[]} 相关分类列表
 */
export function getRelatedCategories(selectedCategoryId, categories) {
  if (!selectedCategoryId || !categories) return [];
  
  const selectedCategory = categories.find(cat => cat.id === selectedCategoryId);
  if (!selectedCategory) return [];
  
  const related = [];
  
  // 同级分类（相同parent_id）
  const siblings = categories.filter(cat => 
    cat.id !== selectedCategoryId && 
    cat.parent_id === selectedCategory.parent_id
  );
  related.push(...siblings.map(cat => ({ ...cat, relation: '同级分类' })));
  
  // 子分类
  const children = categories.filter(cat => cat.parent_id === selectedCategoryId);
  related.push(...children.map(cat => ({ ...cat, relation: '子分类' })));
  
  // 父分类
  if (selectedCategory.parent_id) {
    const parent = categories.find(cat => cat.id === selectedCategory.parent_id);
    if (parent) {
      related.push({ ...parent, relation: '父分类' });
    }
  }
  
  return related.slice(0, 6); // 限制数量
}

/**
 * 验证分类选择的合理性
 * @param {number} categoryId - 分类ID
 * @param {Object} articleData - 文章数据
 * @param {Object[]} categories - 分类列表
 * @returns {Object} 验证结果
 */
export function validateCategorySelection(categoryId, articleData, categories) {
  if (!categoryId) {
    return { valid: true, warning: null };
  }
  
  const category = categories.find(cat => cat.id === categoryId);
  if (!category) {
    return { valid: false, error: '选择的分类不存在' };
  }
  
  // 获取推荐分类
  const recommendations = recommendCategories(articleData, categories, { maxRecommendations: 10 });
  const isRecommended = recommendations.some(rec => rec.category.id === categoryId);
  
  if (!isRecommended && (articleData.title || articleData.content)) {
    return { 
      valid: true, 
      warning: '所选分类与文章内容的匹配度较低，建议考虑其他分类' 
    };
  }
  
  return { valid: true, warning: null };
}

export default {
  recommendCategories,
  getRelatedCategories,
  validateCategorySelection
};