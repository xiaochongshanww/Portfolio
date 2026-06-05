# 大规模重构方案

> 基于前端审查发现的 H1/H3/M2 问题，制定可落地的分步重构计划。

---

## 一、API 调用统一（原 H3）

### 现状

```
三种调用方式共存:
  方式1: apiClient.get('/users/me')         → 15+ 处直接调用
  方式2: UsersService.getApiV1UsersMe()     → 3 处 generated 调用
  方式3: fetch('/api/v1/auth/change_password') → 1 处 raw fetch
  + 独立 api 文件: src/api/media.js, src/api/backup.js
```

### 目标

统一为唯一入口：`import { API } from '@/api'`，所有请求经过同一拦截器链（token 注入 + 自动刷新 + ETag 缓存）。

### 执行步骤

#### Step 1：补全 `src/api/index.js` 的导出

当前 `index.js` 只导出 `API = createServices(Services)`，但 `Services` 来自 `src/generated/`，而 `src/generated/` 中的 service 方法与后端路由未必一一对应。

补全方式：在 `index.js` 中添加缺失的手写 API 方法，以兼容方式导出。

```javascript
// src/api/index.js — 改造后
import { OpenAPI } from '../generated'
import * as Services from '../generated'
import { bindGeneratedClient, createServices } from './generatedClientAdapter'
import apiClient from '../apiClient'

bindGeneratedClient(OpenAPI)
const GeneratedAPI = createServices(Services)

// 手写补全：generated 未覆盖的接口
const HandwrittenAPI = {
  // 分类/标签
  getCategories: (params) => apiClient.get('/taxonomy/categories/', { params }),
  createCategory: (data) => apiClient.post('/taxonomy/categories/', data),
  updateCategory: (id, data) => apiClient.patch(`/taxonomy/categories/${id}`, data),
  deleteCategory: (id) => apiClient.delete(`/taxonomy/categories/${id}`),

  getTags: (params) => apiClient.get('/taxonomy/tags/', { params }),
  createTag: (data) => apiClient.post('/taxonomy/tags/', data),
  updateTag: (id, data) => apiClient.patch(`/taxonomy/tags/${id}`, data),
  deleteTag: (id) => apiClient.delete(`/taxonomy/tags/${id}`),

  // 备份
  getBackupRecords: (params) => apiClient.get('/backup/records', { params }),
  createBackup: () => apiClient.post('/backup/create'),
  getBackupConfig: () => apiClient.get('/backup/config'),
  updateBackupConfig: (data) => apiClient.put('/backup/config', data),

  // 安全
  getSecurityStats: () => apiClient.get('/security/stats'),
  getSystemHealth: () => apiClient.get('/security/system-health'),

  // 设置
  getSettings: (section) => apiClient.get(`/settings/${section}`),
  updateSettings: (section, data) => apiClient.put(`/settings/${section}`, data),

  // 媒体（补充 generated 未覆盖的）
  uploadMedia: (formData) => apiClient.post('/media/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  }),
}

export const API = { ...GeneratedAPI, ...HandwrittenAPI }
```

#### Step 2：替换各处直接 `apiClient.get('/users/me')` 调用

| 文件 | 当前写法 | 改为 |
|------|----------|------|
| `src/stores/user.js:47` | `apiClient.get('/users/me')` | `API.UsersService.getApiV1UsersMe()` |
| `src/stores/user.js:78` | `apiClient.post('/auth/logout')` | `API.AuthService.postApiV1AuthLogout()` |
| `src/views/ArchivePage.vue:285` | `apiClient.get('/articles/public?...')` | `API.ArticlesService.getApiV1ArticlesPublic()` |
| `src/views/UserAdmin.vue:69` | `apiClient.get('/users/?page=...')` | `API.UsersService.getApiV1Users()` |

**预计改动：15 处，涉及 10 个文件。**

#### Step 3：替换直接 fetch 调用

`src/views/Profile.vue:803`：
```javascript
// 当前
const response = await fetch('/api/v1/auth/change_password', { ... })
// 改为
const response = await API.AuthService.postApiV1AuthChangePassword({
  requestBody: { email, old_password: oldPwd, new_password: newPwd }
})
```

#### Step 4：删除冗余的独立 api 文件

`src/api/media.js` 和 `src/api/backup.js` 中的方法全部合并到 `src/api/index.js` 后，删除这两个文件。

#### 风险

- 生成的 Service 方法签名与后端 OpenAPI 定义绑定。如果后端 OpenAPI 更新但前端未重新生成 `src/generated/`，类型会不匹配
- **工作量**：2 天（15 处替换 + 验证）

---

## 二、大文件拆分（原 H1）

### 2.1 NewArticle.vue（3038 行）

#### 现状分析

| 行号范围 | 内容 | 职责 |
|----------|------|------|
| 1-500 | template：文章表单（标题、slug、内容区、标签、分类、封面、SEO、定时发布、提交按钮） |
| 500-1930 | script setup：编辑器初始化、自动保存、标签管理、分类加载、图片上传、表单校验、工作流操作 |
| 1930-3038 | script 后半 + style：二次初始化逻辑、样式覆盖 |

#### 拆分方案

```
NewArticle.vue (骨架: 表单容器 + 编排逻辑, ~500 行)
├── ArticleForm.vue          (新)   表单字段 (标题/Slug/摘要/封面)  ~150 行
├── CategorySelector.vue     (已有) 分类选择器 + 快速创建          ~200 行
├── TagManager.vue           (新)   标签输入 + 管理                ~150 行
├── SEOFields.vue            (新)   SEO 标题/描述                  ~100 行
├── SchedulePicker.vue       (新)   定时发布选择器                 ~100 行
└── VditorEditor.vue         (已有) Markdown 编辑器               1515 行
```

**关键点**：
- 表单状态仍由 `NewArticle.vue` 统一管理，子组件通过 `v-model` / `props` 通信
- 编辑器 `VditorEditor.vue` 保持独立，通过 `v-model` 绑定 `content_md`
- `CategorySelector.vue` 已存在，保持不变

#### 执行顺序

```
1. 提取 TagManager.vue    — 最独立，无外部依赖
2. 提取 SEOFields.vue     — 纯展示，仅 v-model
3. 提取 SchedulePicker.vue — 纯展示
4. 提取 ArticleForm.vue   — 依赖前三个，组装表单字段
5. 改造 NewArticle.vue    — 用子组件替换内联代码
```

**工作量**：3 天（含测试验证）

---

### 2.2 ArticleDetail.vue（2203 行）

#### 现状分析

| 行号范围 | 内容 |
|----------|------|
| 1-300 | template：文章头部（标题、作者信息、元数据、封面图） |
| 300-600 | template：文章内容区 + 管理操作按钮（审核/发布/驳回/定时/归档） |
| 600-1000 | template：点赞、收藏、评论列表、评论表单 |
| 1000-1400 | template：侧边栏、相关文章 |
| 1400-1700 | script：数据加载、用户状态检查、操作逻辑 |
| 1700-2203 | script：评论互动逻辑 + style |

#### 拆分方案

```
ArticleDetail.vue (骨架: 页面编排, ~500 行)
├── ArticleHeader.vue        (新)   标题 + 作者信息 + 元数据      ~150 行
├── ArticleActions.vue       (新)   管理操作按钮面板              ~200 行
├── ArticleInteractions.vue  (新)   点赞 + 收藏                  ~100 行
├── CommentsSection.vue      (新)   评论列表 + 表单 (整合 CommentNode + CommentsThread)  ~300 行
├── ArticleSidebar.vue       (新)   侧边栏/相关文章               ~200 行
└── ArticleContentRenderer.vue (已有) 内容渲染                   1057 行
```

**关键点**：
- `CommentsSection.vue` = 现有 `CommentsThread.vue` + 评论表单，无需全量重写
- `ArticleActions.vue` 包含工作流按钮，需要 props 接收 `article.status` 和 `nextList`

**工作量**：2 天

---

### 2.3 VditorEditor.vue（1515 行）

#### 现状分析

| 行号范围 | 内容 |
|----------|------|
| 1-100 | template：编辑器容器 + 工具栏自定义 |
| 100-500 | script：图片上传处理（CDN上传 + 媒体库上传 + 粘贴上传）|
| 500-1000 | script：Vditor 初始化配置、toolbar、快捷键 |
| 1000-1300 | script：生命周期管理、内容同步、外部接口暴露 |
| 1300-1515 | style：编辑器样式覆盖 |

#### 拆分方案

```
VditorEditor.vue (编辑器核心: 初始化 + 生命周期, ~400 行)
├── VditorUploader.ts        (新)  图片上传逻辑 (CDN/媒体库/粘贴)  ~200 行
├── vditorToolbar.ts         (新)  toolbar 配置                   ~100 行
└── vditorStyles.css         (新)  样式覆盖                       ~200 行
```

**关键点**：
- `VditorUploader.ts` 作为纯函数模块，不依赖 Vue 组件上下文
- `vditorToolbar.ts` 导出 toolbar 配置数组
- `VditorEditor.vue` 只保留组件初始化、`v-model` 绑定、生命周期

**工作量**：1 天

---

### 2.4 BackupManagement.vue（2110 行）

当前 2110 行由 5 个功能区域混合在一个文件：

```
1. 备份记录列表 (el-table)
2. 创建/删除备份操作
3. 备份配置表单
4. 恢复记录列表
5. 外部元数据管理
```

#### 拆分方案

```
BackupManagement.vue (容器: 标签页切换, ~300 行)
├── BackupRecordList.vue     (新)  备份记录表格 + 操作按钮       ~500 行
├── BackupConfigForm.vue     (新)  备份配置表单                   ~300 行
├── RestoreRecordList.vue    (新)  恢复记录表格                   ~400 行
├── PhysicalBackupPanel.vue  (新)  物理备份操作面板               ~300 行
└── ExternalMetadataPanel.vue (新) 外部元数据管理面板             ~300 行
```

**工作量**：2 天

---

## 三、页面组件零 props（原 M2）

### 现状

40+ views 文件全部从 `vue-router` 的路由参数（`$route.params` / `$route.query`）获取输入，没有 props。

### 改造方案

对三类关键页面添加 props：

#### 3.1 接受路由参数的页面

```javascript
// Login.vue — 当前
const route = useRoute()
const redirect = route.query.redirect

// Login.vue — 改造后
const props = defineProps({
  redirect: { type: String, default: '/' },
})

// 需要路由传参：<router-link :to="{ name: 'login', query: { redirect: '/admin' } }">
```

涉及 6 个页面：`Login`、`ArticleDetail`、`NewArticle`、`AuthorProfile`、`CategoryPage`、`TagPage`

#### 3.2 添加 Props 后的兼容

```javascript
// 兼容路由参数：如果 props 未传，从 $route 读取
const route = useRoute()
const resolvedId = computed(() => props.id || route.params.id)
```

这样既支持 `<ArticleDetail id="123" />` 方式直接渲染，也支持路由导航。

#### 3.3 在 router.js 中启用 props 传递

```javascript
{ path: '/article/:slug', component: ArticleDetail, props: true },
```

Vue Router 的 `props: true` 会自动将 `:slug` 作为 `props.slug` 传入组件。

#### 工作量

1 天（6 个页面 × 每个约 1 小时）

---

## 四、执行路线图

### 阶段 1：API 统一（2 天）

```
Day 1 AM: 补全 src/api/index.js 导出（handwritten 方法）
Day 1 PM: 替换 stores/user.js + 各 view 中的 apiClient 直接调用
Day 2 AM: 替换 Profile.vue 的 fetch 调用，删除 src/api/media.js + backup.js
Day 2 PM: 回归验证（逐个页面打开确认 API 调用正常）
```

### 阶段 2：VditorEditor + ArticleDetail 拆分（3 天）

```
Day 3: VditorEditor 拆分 → VditorUploader.ts + vditorToolbar.ts
Day 4: ArticleDetail 拆分 → ArticleHeader + ArticleActions + CommentsSection
Day 5: 回归验证 + 修复样式差异
```

### 阶段 3：NewArticle 拆分（3 天）

```
Day 6: TagManager.vue + SEOFields.vue
Day 7: SchedulePicker.vue + ArticleForm.vue
Day 8: NewArticle 骨架整合 + 回归验证
```

### 阶段 4：Props 兼容 + BackupManagement 拆分（3 天）

```
Day 9:  6 个关键页面添加 props 兼容
Day 10: BackupManagement → 4 个子组件提取
Day 11: 全量回归测试
```

### 总计

**11 个工作日**，切分为 4 个独立可交付阶段，每阶段结束后都保持 `main` 分支可部署。

---

## 五、风险与对策

| 风险 | 概率 | 影响 | 对策 |
|------|------|------|------|
| 拆分后样式不一致 | 中 | 中 | 拆分前记录页面截图，拆分后逐像素对比 |
| API 统一后某 view 不可用 | 中 | 高 | 每替换一个文件立即手动验证该页面 |
| 子组件拆分后 props 接口不稳定 | 低 | 中 | 先定义 TypeScript interface，再实现组件 |
| git merge 冲突 | 中 | 低 | 每阶段独立分支，完成后合入 main |
| 测试覆盖不足导致回归 | 高 | 中 | 关键拆分前先补 E2E 测试 |
