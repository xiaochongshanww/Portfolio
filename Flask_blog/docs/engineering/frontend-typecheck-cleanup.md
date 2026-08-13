# 前端 TypeCheck 存量错误清理 — 改造计划与进度追踪

> 文档目的：记录"前端 typecheck 基线修复"任务的完整计划、当前进度、修复模式与剩余工作，便于跨环境续接执行。
> 创建日期：2026-08-13
> 对应评估报告：[standardization-review.md](./standardization-review.md) 中 M2（类型检查门禁缺失）与 P1 路线。

---

## 一、任务目标

1. 消除前端 `vue-tsc --noEmit` 的全部存量类型错误，让 `npm run typecheck` 达到 **0 错误**。
2. 将 CI 中的 `typecheck-frontend` job 从 `continue-on-error: true`（非阻断）**转为真实门禁**。

## 二、问题根源

- `frontend/tsconfig.json` 开启 `strict: true` + `checkJs: true` + `allowJs: true`。
- 项目大量组件是 **JS script 的 `.vue` 文件**（无 `lang="ts"`）以及 **纯 `.js` 工具文件**，均被严格类型检查。
- 初始错误量约 **1777**，主要模式：
  - `ref(null)` / `ref([])` / `reactive({})` 缺类型 → 访问属性报 `never`（TS2339）。
  - 函数参数无类型 → `implicit any`（TS7006）。
  - `catch (error)` 中 error 为 `unknown`，访问 `.message`/`.response` 报错（TS18046）。
  - el-tag/el-select 等 Element Plus 组件的 `:type` 等属性需字面量联合类型。
  - `window.xxx` 自定义全局属性未声明（TS2339）。

## 三、已完成进度

### 3.1 基础设施（已完成）

| 项 | 状态 |
|----|------|
| `tsconfig.json` 新增 `baseUrl: "."` + `paths: { "@/*": ["src/*"] }`，修复 `@/` 别名在 vue-tsc 中不可解析（TS2307） | ✅ |
| 新建 `src/types.ts`：项目共享数据接口（User/Category/Tag/ArticleAuthor/Article/Comment/BackupRecord/RestoreRecord/MediaFile/LogEntry） | ✅ |
| `env.d.ts` 补充 `Window` 接口自定义属性（vueErrorHandler/testBatchMessages/openMediaLibrary/vditorCleanupFunctions 等） | ✅ |
| `src/stores/user.js`：给 store state 加 JSDoc 类型（`user` → `User \| null`） | ✅ |

### 3.2 已修复文件（错误清零）

| 文件 | 原错误数 | 修复方式 |
|------|---------|---------|
| `src/views/ArticleDetail.vue` | 108 | ref 加泛型、函数参数补类型、`message`→`ElMessage` 真 bug、Element 类型断言、apiClient 参数类型 |
| `src/views/admin/BackupManagement.vue` | 154 | ref/reactive JSDoc 类型、catch error 断言、函数参数 JSDoc、`Record<string,string>` map、setTimeout 类型、el-tag 联合类型 |
| `src/views/NewArticle.vue` | 117（部分完成） | 进行中：ref 类型、ArticleForm/NewTag typedef、catch 断言、`markAsChanged`→`triggerAutoSave` 真 bug 修复、setMeta JSDoc；**剩余约 32 错误**（多为 TS7006/TS18046，续接时可先用 5.1 模式处理函数参数与 catch 块） |

### 3.3 当前错误总量

- **启动时**：约 1777
- **当前**：约 **1411**（已修约 366）
- 剩余错误集中在 60+ 文件，前 12 名见下表

---

## 四、剩余工作（按文件排序）

| 错误数 | 文件 | 说明 |
|-------|------|------|
| 95 | `src/views/MediaGallery.vue` | ref 缺类型 + implicit any |
| 74 | `src/views/admin/RestoreManagement.vue` | 同上（可用 RestoreRecord 类型） |
| 57 | `src/views/admin/MediaManagement.vue` | 同上（可用 MediaFile 类型） |
| 55 | `src/components/CategorySelector.vue` | 同上（Category） |
| 53 | `src/views/CategoryPage.vue` | 同上（Category/Article） |
| 50 | `src/views/admin/LogManagement.vue` | LogEntry 类型 |
| 49 | `src/utils/markdownProcessor.reliable.js` | **纯 JS**：markdown-it 回调签名 + implicit any |
| 49 | `src/utils/categoryRecommender.js` | 纯 JS |
| 49 | `src/components/media/MediaSelector.vue` | MediaFile |
| 43 | `src/api/index.js` | **纯 JS**：API 方法定义无类型 |
| 42 | `src/utils/summaryExtractor.js` | 纯 JS |
| 42 | `src/components/media/MediaUploadDialog.vue` | MediaFile |
| … | 其余约 50 个文件 | 多为 .vue（ref/参数）与 .js（JSDoc） |

### 4.1 剩余错误按文件类型分组（2026-08-13 快照）

**当前总量：约 1411 = 1032 (.vue) + 379 (.js)**

**纯 .js 文件清单（19 个，用 JSDoc 模式，见 5.2）：**
```
src/api/backup.js                  # 已完成（Proxy 已加类型）
src/api/generatedClientAdapter.js
src/api/index.js                   # 43 错误，最大
src/api/media.js
src/composables/useMeta.js         # 已完成（setMeta 已加 JSDoc）
src/composables/useResponsiveLayout.js
src/errorCodes.js
src/stores/user.js                 # 已完成（store 已加 JSDoc）
src/utils/categoryRecommender.js   # 49 错误
src/utils/codeTheme.js
src/utils/contentTypeDetector.js
src/utils/editorConversion.js
src/utils/htmlMathProcessor.js
src/utils/markdownProcessor.reliable.js  # 49 错误，markdown-it 回调
src/utils/mediaUtils.js
src/utils/message.js
src/utils/messageManager.js
src/utils/summaryExtractor.js      # 42 错误
src/utils/userDisplay.js
```

**剩余 .vue 文件**：重点见上表（MediaGallery/RestoreManagement/MediaManagement/CategorySelector/CategoryPage/LogManagement 等），模式统一见 5.1。

完整清单见文末：`npx vue-tsc --noEmit 2>&1 | grep -E "error TS" | cut -d'(' -f1 | sort | uniq -c | sort -rn`

---

## 五、修复模式（必须遵守）

### 5.1 .vue 文件（JS script，不能用 TS 语法！）

> ⚠️ 关键：JS script 中 **不能** 写 `import type`、`ref<Foo>(null)`、`as` 断言、泛型 `querySelector<T>()`。这些是 TS 语法，会报 `TS1005`/`TS8010`/`TS2365`。

**正确做法：JSDoc 类型标注**

```js
// ref 加类型
/** @type {import('vue').Ref<Article | null>} */
const article = ref(null);

// 数组 ref
/** @type {import('vue').Ref<BackupRecord[]>} */
const backups = ref([]);

// reactive
const detailDialog = reactive({
  visible: false,
  /** @type {BackupRecord | null} */
  backup: null
});

// 函数参数
/** @param {BackupRecord} backup */
const getProgress = (backup) => { ... };

// 可选参数（模板里可能传 undefined）
/** @param {string | undefined} status */
function getStatusText(status) { ... }

// 返回联合类型（给 el-tag :type）
/**
 * @param {string | undefined} status
 * @returns {'info' | 'success' | 'primary' | 'warning' | 'danger'}
 */
function getStatusTagType(status) { ... }

// catch 断言
} catch (error) {
  const err = /** @type {{ message?: string, response?: { data?: { message?: string } } }} */ (error);
  ElMessage.error(err.response?.data?.message || err.message || '网络错误');
}

// DOM 查询断言（不能用泛型）
/** @type {HTMLElement | null} */
const el = document.querySelector('.selector');
el && el.click();
```

**Element Plus 组件属性**：`:type` 用 `'info' | 'success' | 'primary' | 'warning' | 'danger'` 联合类型。

**setTimeout/setInterval 类型**：`ReturnType<typeof setTimeout> | null`。

**对象字面量需要动态加字段**：用 `/** @type {Record<string, unknown>} */` 或补全类型。

### 5.2 .js 文件（纯 JS，用 JSDoc）

```js
// 顶部引入类型
/** @typedef {import('../types').Article} Article */

/** @param {number} id @returns {Promise<Article>} */
async function getArticle(id) { ... }

// 对象初始化为 null 后访问属性
/** @type {Record<string, unknown> | null} */
let cache = null;

// catch
} catch (e) {
  const err = /** @type {{ message?: string }} */ (e);
}
```

### 5.3 通用约束

- **绝不改变运行时逻辑**，只加类型/JSDoc/断言/可选链/`Number()`/`.getTime()`。
- 若真 bug（如 `markAsChanged` 未定义 → 应为 `triggerAutoSave`；`message.warning` → `ElMessage.warning`）在修复中暴露，修正引用并记录。
- 不修改 `src/generated/`（构建时重建）。
- 优先复用 `src/types.ts`；确需扩展时向接口追加可选字段。
- 修完一个文件立即验证，再继续下一个。

---

## 六、验证命令

```bash
cd frontend
# 查看全部错误
npx vue-tsc --noEmit 2>&1 | grep -E "error TS" | cut -d'(' -f1 | sort | uniq -c | sort -rn
# 查看单个文件
npx vue-tsc --noEmit 2>&1 | grep "BackupManagement.vue"
```

目标：`npx vue-tsc --noEmit 2>&1 | grep -cE "error TS"` → `0`

完成后：
1. `npm run lint`（0 error，881 warning 可接受）
2. `npm run test`（7 文件 20 用例全绿）
3. `npm run build`（成功）
4. 将 `.github/workflows/ci.yml` 的 `typecheck-frontend` 去掉 `continue-on-error: true`

---

## 七、执行建议

- **逐个文件处理**，从错误最多的开始（MediaGallery → RestoreManagement → ...）。
- 每个文件耗时约 10-30 分钟（取决于错误类型），纯 .js 文件因 JSDoc 繁琐稍慢。
- 建议每修 3-5 个文件跑一次全量 vue-tsc（单次 2-5 分钟），不要每改一行就跑。
- 已确立的模式（5.1/5.2）可直接套用到后续所有文件。

## 八、相关 Git 状态

当前未提交的改动（均为本任务产生）：
```
M frontend/env.d.ts                                  # Window 接口扩展
M frontend/src/api/backup.js                         # Proxy JSDoc 类型
M frontend/src/composables/useMeta.js                # setMeta JSDoc
M frontend/src/stores/user.js                        # store user 类型
M frontend/src/views/ArticleDetail.vue               # ✅ 已完成（108→0）
M frontend/src/views/NewArticle.vue                  # 进行中（剩约 32）
M frontend/src/views/admin/BackupManagement.vue      # ✅ 已完成（154→0）
M frontend/tsconfig.json                             # 新增 baseUrl/paths
?? docs/engineering/frontend-typecheck-cleanup.md    # 本文档
?? frontend/src/types.ts                             # 新增共享类型
```

> 注：`.claude/settings.local.json` 与 `university-recruitment-info-collector/.service_info` 是本地/他项目文件，勿提交。

## 九、跨环境续接指引

换环境执行时：

1. **先跑验证命令**确认基线：
   ```bash
   cd frontend && npx vue-tsc --noEmit 2>&1 | grep -cE "error TS"   # 期望约 1411
   ```
2. **确认上述 git 改动已存在**（或先提交/暂存这批已完成进度，再在新环境继续）。
3. **按第四/4.1 节清单逐个文件修**，模式见第五/5.1/5.2。
4. 每修 3-5 个文件跑一次全量 vue-tsc（单次 2-5 分钟）。
5. 修完验证：typecheck=0 → lint 0 error → test 全绿 → build 成功 → CI 去掉 `continue-on-error`。

**已完成文件的修复可作参考模板**：`ArticleDetail.vue`、`BackupManagement.vue`（.vue 模式）、`useMeta.js`、`stores/user.js`（.js 模式）。
