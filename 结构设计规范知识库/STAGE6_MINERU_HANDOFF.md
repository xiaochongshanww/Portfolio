# 阶段六：MinerU 环境执行交接文档

## 背景

当前项目已经完成知识库产品化基础设施：

- 默认 PDF 解析后端为 MinerU，PyMuPDF 仅作为显式 fallback。
- `content_list` 是唯一主入库输入。
- MinerU 的 Markdown、middle/model JSON、图片等产物会被保留、索引和 hash。
- 构建会生成 `manifest.json`、`build_quality.json`、ChromaDB 向量库。
- 已加入 AI 校对修正层：`review -> candidates -> approved -> rebuild`。

本机当前没有完整 MinerU 执行环境。阶段六需要在另一台已经具备 MinerU CLI/模型的环境上执行真实构建，并把质量结果、修正建议和必要文档带回。

## 目标

在 MinerU 可用环境完成一次真实知识库构建，产出可审计的第一版知识库快照：

- `data/mineru/`：MinerU 全量解析产物。
- `data/processed/`：标准 elements、chunks、质量报告。
- `data/images/`：可访问的表格、公式、图片媒体文件。
- `db/`：ChromaDB 向量库。
- `data/manifest.json`：构建清单和 `data_version_hash`。
- `data/audit/reports/`：规则审计和 AI 校对报告。
- `data/corrections/approved/`：人工确认后的修正，可选择提交。

## 目标环境准备

在目标机器进入仓库：

```bash
git clone git@github.com:xiaochongshanww/Portfolio.git
cd Portfolio/结构设计规范知识库
git checkout main
git pull origin main
```

创建虚拟环境并安装依赖：

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

确认 MinerU 可用：

```bash
which mineru
mineru --version
```

配置环境变量：

```bash
export PDF_PARSER_BACKEND=mineru
export MINERU_BIN=mineru
export MINERU_ARGS=""
export ZHIPUAI_API_KEY="..."

# 需要 AI 校对时配置
export MIMO_API_KEY="..."
export MIMO_BASE_URL="https://api.xiaomimimo.com/v1"
export MIMO_MODEL="mimo-v2-omni"
export AI_REVIEW_MODEL="mimo-v2-omni"
```

## 执行步骤

先确认待处理 PDF：

```bash
python -m src.pipeline build --dry-run
```

建议先用小文档 smoke：

```bash
mkdir -p /tmp/spec-smoke
cp data/raw/test_image.pdf /tmp/spec-smoke/
python -m src.pipeline rebuild --source /tmp/spec-smoke
python -m src.pipeline status
```

再跑真实全量构建：

```bash
python -m src.pipeline rebuild --source data/raw
python -m src.pipeline status
```

运行审计：

```bash
python -m src.pipeline audit --processed-dir data/processed
```

运行检索评估：

```bash
python -m src.evaluation run --top-k 5
```

启动控制台：

```bash
uvicorn src.app.main:app --host 127.0.0.1 --port 8000
```

打开：

```text
http://127.0.0.1:8000/static/index.html
```

## AI 校对流程

针对高风险页生成候选：

```bash
python -m src.pipeline review --doc GB50009-2012 --pages 40-45 --source data/raw --processed-dir data/processed
```

在控制台“校对候选”中审核：

- `批准`：标记为 `approved`。
- `拒绝`：标记为 `rejected`。
- `待审`：恢复为 `pending`。

将 approved candidates 提升为构建修正：

```bash
python -m src.pipeline promote-corrections --doc GB50009-2012
```

应用修正并重建：

```bash
python -m src.pipeline rebuild --source data/raw
```

安全边界：

- 表格数值、公式、强制性条文、结构安全参数必须人工确认。
- 不要直接把 pending candidates 提升到 approved。
- `--include-pending` 只用于临时实验，不用于正式知识库快照。

## 验收标准

一次阶段六构建至少满足：

- `python -m src.pipeline status` 返回 `built: true`。
- `data/manifest.json` 存在并包含 `parser_backend=mineru`。
- `data/processed/build_quality.json` 存在。
- `data/mineru/<doc_id>/artifacts.json` 存在。
- `data_version_hash` 在同一输入和参数下稳定。
- `python -m src.evaluation run --top-k 5` 能完成并输出评估摘要。
- 对 `GB 50009` 表格页、`GB 50011` 条文/公式页至少各抽检 3 页。
- 发现的高风险解析错误要进入 candidates 或 approved corrections。

## 需要带回或提交的内容

默认不提交：

- `data/mineru/`
- `data/processed/`
- `data/images/`
- `data/audit/`
- `db/`
- `data/manifest.json`
- `data/corrections/candidates/`

建议带回作为本地快照或压缩包：

```bash
tar -czf stage6-build-snapshot.tgz data/mineru data/processed data/images data/audit data/manifest.json
```

建议提交：

- `data/corrections/approved/*.json`：如果这些修正已经人工确认，并希望纳入可复现构建。
- 必要的文档更新：构建结果摘要、已知问题、验收结论。

## 常见问题

`ZHIPUAI_API_KEY 未设置`

向量化入库需要智谱 embedding key。设置后重跑 rebuild。

`未找到 MinerU CLI`

确认 `which mineru`、`MINERU_BIN` 和虚拟环境 PATH。

`MinerU 未生成 content_list JSON`

该文档构建失败，不写成功 manifest。检查 `data/mineru/<doc_id>/raw/` 和 MinerU 日志。

`review 返回 dependency_missing`

AI 校对页图渲染依赖 PyMuPDF。确认 `pip install PyMuPDF` 后重试。

`review 返回 not_configured`

未配置 `MIMO_API_KEY`。这不影响 rebuild，只是不生成 AI candidates。

## 当前仓库状态

截至本交接文档创建时，阶段五和 AI 校对修正层已经推送到 `origin/main`。目标环境应从 `main` 最新代码开始执行。
