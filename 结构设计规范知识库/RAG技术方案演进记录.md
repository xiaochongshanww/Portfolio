# 结构设计规范知识库 — RAG 技术方案演进记录

> 本文档记录项目从传统 RAG 到多模态 RAG 的技术演进过程、遇到的问题、尝试过的方案及最终决策。

---

## 一、架构演进

### Phase 1 — 初始架构（纯文本 RAG）

```
用户 → ZhipuAI Embedding → ChromaDB 检索 → Ollama LLM → 回答
```

- 使用 `unstructured` 库 + `hi_res` 策略处理 PDF
- ZhipuAI embedding-2 做向量化
- ChromaDB 做向量存储
- Ollama 本地模型做 LLM 推理
- 兼容 OpenAI API 格式，对接 Chatbox 等客户端

### Phase 2 — 切换为云端 LLM + 多模态

```
用户 → ZhipuAI Embedding → ChromaDB 检索 → MiMo 多模态 API → 带图回答
                        ↓
                  页面截图(3x PNG)
                        ↓
                  MiMo 看图理解
```

- 放弃 Ollama（本地算力不足）
- 替换 DeepSeek 为 MiMo 多模态模型（支持图片理解）
- PDF 每页渲染为 3x 分辨率 PNG 截图
- 检索时同时发送文本上下文 + 页面截图给 MiMo

### Phase 3 — 混合检索 + 优化

```
用户 → ZhipuAI Embedding + BM25 trigram → RRF 融合 → 图片加载 → MiMo 回答
                           ↑
                   条文号直接查找
```

- 向量检索 + BM25 关键词检索（trigram 中文分词）
- 语句中检测到条文号时强制命中对应条目
- 多轮对话：历史问题 + 当前问题联合检索
- 相关性阈值过滤低质量结果

### 最终部署架构

```
浏览器 → Open WebUI(:8080) → 跳板机 Nginx → RAG API(:8000) → MiMo API
                                                ↑
                                      ChromaDB + BM25
                                                ↑
                                      data/images/ (1038页截图)
```

---

## 二、PDF 解析方案对比

| 方案 | 速度 | 表格 | 公式 | 图文 | 安装复杂度 |
|------|------|------|------|------|-----------|
| unstructured `hi_res` | 极慢（每本>2h） | HTML | ❌ | ❌ | 低 |
| unstructured `fast` | 快（~9min/5本） | 文本碎片 | ❌ | ❌ | 低 |
| **PyMuPDF（当前）** | 快（~20min含渲染） | 文本碎片 | ❌ | ✅ 渲染为PNG | 低 |
| MinerU | 中 | ✅ Markdown | ✅ LaTeX | ❌ | **极高**（不可行） |

### MinerU 尝试记录

尝试安装 MinerU 作为替代方案，但最终放弃：

1. **pip 安装** — 依赖链极长：
   - PyTorch(2GB) → transformers(1GB) → detectron2(需源码编译) → ultralytics → doclayout_yolo → paddleocr → ...
2. **模型下载** — 需从 HuggingFace 下载 7+ 个模型：LayoutLMv3(1.3G)、DocLayout YOLO(40MB)、MFD(40MB)、UniMERNet Small(775MB)、StructEqTable、TableMaster、RapidTable
3. **配置缺失** — `layoutlmv3_base_inference.yaml` 等核心配置文件不存在于公开仓库
4. **Docker 镜像** — `alexsuntop/mineru:3.1.0` 存在但大小 **18.3GB**，通过代理拉取被 Docker Hub 403 拒绝（出口 IP 146.190.115.113 被限）
5. **结论**：投入产出比太低，放弃

---

## 三、搜索方案演进

### 3.1 纯向量检索（已弃用）

```python
chroma_collection.query(query_embeddings=[emb], n_results=5)
```

**问题**：语义相似但上下文不相关的内容被召回。
- 如"荷载分类和荷载代表值"匹配了"重力荷载代表值"但不包含实际定义
- 条文号（如"5.1.3"）无法通过语义检索准确命中

### 3.2 混合检索（当前）

```python
def hybrid_search(query, top_k):
    # 1. 向量检索（语义匹配）
    dense_results = chroma_collection.query(...)
    # 2. BM25 trigram（关键词匹配）
    bm25_scores = bm25_index.get_scores(tokenize_chinese(query))
    # 3. 条文号直接查找
    clause_nums = re.findall(r'\d+\.\d+\.?\d*', query)
    # 4. RRF 融合 + 距离排序
```

### 3.3 Chinese Tokenization 实验

| 方法 | BM25 匹配效果 | 结论 |
|------|--------------|------|
| regex `[一-鿿\w]+` | 分数全为 0 | 不适用于中文 |
| jieba 分词 | 可用，长查询被切碎稀释 | 中等 |
| **trigram 字符 n-gram** | 能匹配"重力荷载"的变体 | **推荐** |

Trigram 示例：
```
"重力荷载代表值" → 单词:[重力荷载代表值] + trigram:[重力荷,力荷载,荷载代,载代表,代表值]
```

---

## 四、RAG 质量优化记录

### 问题 1：表格数据碎片化

**症状**：表 5.1.1 数据被切成 13 个小块，检索不到完整内容

**根因**：页码数字"14"、孤立系数值"0.5"、水印"www.weboos.com"被 `is_title_block` 判定为标题，导致换行切分

**修复**：增加过滤规则
```python
PAGE_NUM_RE = re.compile(r'^\d{1,3}$')      # 页码
DECIMAL_RE = re.compile(r'^[\d\.\s]{1,5}$')  # 孤立数值
URL_RE = re.compile(r'^[a-zA-Z0-9]+\.[a-z]') # 水印
SHORT_SYMBOL_RE = re.compile(r'^[\d\.\-—·]+$') # 短符号
```

**效果**：13 块 → 2 块，表格内容完整保留。回答从"未找到"变为正确输出 7 个类别标准值。

### 问题 2：MiMo 不解析检索到的文本

**症状**：12 段文本 + 10 页截图已送达 MiMo，但回答"未找到明确依据"

**尝试过的方案**：
- 增加 prompt 规则（"优先从检索文本中查找"）→ 无效
- 增加示例回答（"住宅...2.0 kN/m²"）→ 无效
- **硬编码表格格式化** → 有效但违反了"不要特化"原则，已移除
- 最终判断：属于 MiMo 模型本身的文本理解能力局限

### 问题 3：图片引用变量名错误

**根因**：f-string 模板中使用 Python list 而非字符串拼接
```python
img_list = []                    # Python list
user_text = f"...{img_list}..."  # 渲染为 "['item1', 'item2']"
```
修复为：
```python
img_list_str = "\n".join(img_list)
user_text = f"...{img_list_str}..."
```

### 问题 4：多轮对话指代

**方案**：历史问题 + 当前问题联合检索
```python
enhanced_query = f"{history[-1]} {current_query}"
# "它的系数是多少？" → "住宅楼面活荷载标准值是多少？ 它的系数是多少？"
```

### 问题 5：相关性阈值设计

- 初版使用 RRF 融合分数做阈值，但 RRF 分数范围在 0~0.05，与预期不符
- 改为直接用向量检索的距离做判断：`dist < 0.65`
- 测试后发现中文规范向量距离普遍在 0.55~0.95，阈值最终设为 0.65

### 问题 6：Docker 网络代理

- 本地无法直连 Docker Hub / GitHub / HuggingFace
- Xray(VMess)代理可达，但 Docker daemon 经过代理拉升镜像被 403
- 最终：API 直接宿主机运行，放弃 Docker 镜像拉取

---

## 五、当前系统参数

| 参数 | 值 | 说明 |
|------|----|------|
| RAG_TOP_K | 12 | 召回条数 |
| RAG_MIN_SCORE | 0.65 | 图片加载距离阈值 |
| IMG_BASE_URL | /images（可配） | 图片服务地址 |
| BM25 窗口 | top_k × 10 | BM25 候选池大小 |
| BM25 距离 | >5分:0.3 / 其它:0.45 | BM25 结果优先级 |
| 文本上下文上限 | 前 20 段 | 发送给 LLM 的检索文本 |
| 图片分辨率 | 3x (216dpi) | PDF 页面渲染倍数 |
| 图片总量 | 1038 页 / 417MB | 5 本规范 |

---

## 六、待解决问题

| 问题 | 影响 | 状态 |
|------|------|------|
| MiMo 不解析文本中的表格数据 | 某些表格回答正确，某些答"未找到" | 模型局限，暂无法解决 |
| 新增规范需走完整管道 | 渲染 1038 页图耗时 ~20min | 可接受 |
| MinerU 等替代方案因网络限制无法部署 | 表格/公式提取能力受限 | 搁置 |
| PaddleOCR 已安装但未集成 | 发送图片前可做 OCR 增强文本提取 | 待评估 |
| 初版使用 API 额度用完 | 向量化需 ZhipuAI API | 需 API Key |

---

## 七、提交历史

```
385d781 移除硬编码的特化代码
7d69a4f 增加表格数据格式化提示
b3cb754 修复图片引用变量名错误
c6a8233 修复表格数据碎片化问题
1922796 回答支持带图引用，增加图片服务端点
2afb6aa 重构为多模态RAG系统，支持PDF截图+MiMo视觉理解
```
