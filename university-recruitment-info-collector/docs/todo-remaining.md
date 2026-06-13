# 未完成清单

基线提交: `9674198eb2d646e53656af82dddfb7ade59ffce1`
最后更新: 2026-06-13

## 当前数据质量基线 (510条)

```
position               100.0% ✅
normalized_position     0.0%  🔴 (全新字段)
department              89.2% ✅
discipline              11.6% 🔴
education_requirement   57.3% 🔴
job_type                23.5% 🔴
location                99.0% ✅
deadline                20.4% 🔴
published_at            62.2% ⚠️
quality_score/normal    0.0%  🔴 (全新字段)

Notice-like titles: 381/510 (74.7%) 🔴🔴🔴
Suspect departments: 70/510 (13.7%) ⚠️
```

---

## 🔴 P0 未完成

| # | 模块 | 需求 | 状态 | 工作量 |
|---|---|---|---|---|
| 1 | attachment_parser.py | **附件内容解析** - Excel/CSV/DOCX/PDF 本地解析，依赖 openpyxl/python-docx | ❌ | M |
| 2 | browser_site.py, hkust_gz.py, gaoxiaojob.py | **所有适配器改用 analyze_document** - 目前仅 static_site 完成 | ❌ | M |
| 3 | extractor.py | **Stage C 修正应用** - apply_review_corrections/removed/additional 函数 | ❌ | S |
| 4 | static_site.py, reprocess.py | **Evidence 保存** - extraction_confidence 字段未填，evidence_json 未序列化 | ❌ | S |
| 5 | validators.py, static_site.py | **FieldCandidate 替代规则直接兜底** - 正则结果应经 choose_best_candidate | ❌ | M |
| 6 | reprocess | **全量重处理执行** - 命令已创建未运行、未出新 CSV | ❌ | S |

## 🟡 P1 未完成

| # | 模块 | 需求 | 状态 |
|---|---|---|---|
| 7 | enrich.py | **改用 analyze_document** | ❌ |
| 8 | frontend | **质量展示** - quality_score/quality_status + 低质量开关 | ❌ |
| 9 | exports | **CSV 导出增强** - 新字段列表 | ❌ |
| 10 | tests | **新增测试** - validators/sections/tables/multi-position | ❌ |
| 11 | validators | **Location 拆分为 city/district/address** - normalize_location 已实现未接入 | ❌ |
| 12 | models | **discipline 多专业 list[str]** - 截断入库问题 | ❌ |

## 🟢 已完成的 P0 基础

- models.py: QualityStatus/DocumentType/质量字段/RecruitmentJob 扩展 ✅
- config.py: LLM_MAX_DOCUMENT_CHARS 配置系列 ✅
- url_utils.py: build_position_job_id 多岗位 ID ✅
- detail_parser.py: ParsedSection/Table/Attachment + colspan/rowspan ✅
- quality/validators.py: position/department/discipline/education/location 验证 + quality_score ✅
- static_site.py: analyze_document 多岗位拆分 + quality_score + SKIP_TYPES ✅
- storage.py: V2 迁移 9 质量列 ✅
- reprocess.py: 命令创建 ✅
- scripts/analyze_export_quality.py: 质量分析脚本 ✅

## 📋 执行计划（按依赖顺序）

### Phase 1 — 快速补齐 P0 (优先级最高)
1. Stage C 修正应用函数（extractor.py）
2. Evidence 保存到入库链路（static_site.py）
3. 全量重处理运行 + 新 CSV

### Phase 2 — 适配器统一 (P0)
4. gaoxiaojob.py 改用 analyze_document
5. enrich.py 改用 analyze_document

### Phase 3 — 字段质量 (P0)
6. FieldCandidate 机制替代直接兜底
7. Location 拆分为 city/district/address 入库

### Phase 4 — 测试与验证 (P1)
8. 新增 validators/sections/tables/multi-position 测试
9. 运行 `university-recruitment-reprocess --all`
10. `scripts/analyze_export_quality.py` 检查改善效果
