# AI 校对修正层实施方案

## 目标

MinerU 解析结果不直接作为不可质疑的真值。系统采用“规则审计 + AI 候选 + 人工批准 + 可追踪应用”的流程，让解析错误可发现、可修正、可审计、可回归。

## 标准流程

```text
MinerU content_list
 -> standard elements
 -> rules audit
 -> AI review candidates
 -> approved corrections
 -> chunks
 -> ChromaDB
 -> manifest
```

当前已实现规则审计、approved correction overlay、manifest 追踪和多模态 review 命令。`review` 在配置 `MIMO_API_KEY` 后会调用多模态模型生成 candidates；未配置时返回 `not_configured`，不影响构建。

## 数据约定

- `data/audit/reports/quality_report.json`：规则审计汇总。
- `data/audit/reports/*_ai_review.json`：AI 校对报告。
- `data/corrections/candidates/*.json`：AI 生成的待审修正候选，默认不参与构建。
- `data/corrections/approved/*.json`：人工批准后的修正，rebuild 默认应用。

approved 修正文件示例：

```json
{
  "corrections": [
    {
      "id": "fix-page-42-table",
      "action": "replace_text",
      "target": {"element_index": 15, "field": "text"},
      "value": "修正后的文本或表格 Markdown"
    }
  ]
}
```

支持动作：

- `replace_text`
- `set_field`
- `delete_element`
- `insert_after`
- `merge_next`

## CLI

```bash
python -m src.pipeline audit --processed-dir data/processed
python -m src.pipeline review --doc GB50009-2012 --pages 40-45 --source data/raw --processed-dir data/processed
python -m src.pipeline promote-corrections --doc GB50009-2012
python -m src.pipeline rebuild --source data/raw
python -m src.pipeline rebuild --source data/raw --no-corrections
```

多模态 review 使用现有 MiMo 配置：

```bash
export MIMO_API_KEY="..."
export MIMO_BASE_URL="https://api.xiaomimimo.com/v1"
export MIMO_MODEL="mimo-v2-omni"
```

可用 `AI_REVIEW_MODEL` 单独覆盖校对模型。

`promote-corrections` 默认只提升 `review_status=approved` 的候选到 `data/corrections/approved/`。如需临时提升 pending 候选，可显式使用 `--include-pending`；不建议用于表格数值、公式和强制性条文。

## 安全边界

- AI 只生成候选，不直接写入 approved。
- 表格数值、公式、强制性条文、结构安全参数必须人工确认。
- 构建 manifest 记录审计发现数、应用修正数、跳过修正数。
- `data_version_hash` 纳入修正结果，便于回归比较。
