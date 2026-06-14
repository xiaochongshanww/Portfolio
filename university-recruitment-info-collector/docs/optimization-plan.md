# 数据质量优化计划

基线提交: `dbcdb19`
最后更新: 2026-06-14

## 执行记录

### 2026-06-14 已完成

| # | 任务 | 状态 |
|---|---|---|
| 1.4 | evidence_json 加入 update_enriched_fields 变化检测 | ✅ |
| 3.1 | quality_score 阈值调整: 75→60(normal), 45→30(needs_review) | ✅ |
| 3.2 | notice-like 扣分调整: -30→-15 | ✅ |
| 3.3 | quality 重新评分: 477/545 条已重算 | ✅ |
| 4.1 | 老数据重新评分完毕 | ✅ |

### 核心发现

重新评分后：
- **Score≥60 (normal)**: 15 条 — 数据本身质量不足，非评分规则问题
- **30≤Score<60**: 72 条
- **Score<30**: 458 条

根本原因不是评分规则太严，而是 **原始数据字段覆盖太低**：
- 71% 岗位是泛化公告标题（非具体岗位名）
- 大量岗位缺 discipline/job_type/education 等关键字段
- evidence_json 迟迟未写入数据库

**solution: 必须运行全量 LLM reprocess + 新的 collection 才能从根本上改善数据。**

```bash
# 分批处理 hidden 岗位
university-recruitment-reprocess --only-low-quality --batch-size 50
```

---

## 当前数据基线 (545条)

| 字段 | 覆盖率 | 目标 |
|---|---|---|
| normalized_position | 4/545 (0.7%) 🔴 | ≥80% |
| evidence_json | 0/545 (0%) 🔴 | ≥50% |
| job_type | 124/545 (23%) 🔴 | ≥60% |
| discipline | 63/545 (12%) 🔴 | ≥40% |
| department | 450/545 (83%) ✅ | ≥80% |
| education_requirement | 291/545 (53%) ⚠️ | ≥60% |
| quality_score | 339/545 (62%) ⚠️ | ≥90% |
| quality_status=hidden | 271/545 (50%) 🔴 | ≤20% |

---

## 一、P0 — evidence_json 持久化

证据已从 LLM 提取但从未写入数据库。

### 1.1 修复 static_site.py 多岗位路径

观察当前代码，确认 evidence 是否被正确收集。如果没有，补全 key。

### 1.2 修复 gaoxiaojob.py 多岗位路径

同 1.1。

### 1.3 修复 enrich.py 多岗位路径

enrich 已经提取 evidence_json，但需要确认 `update_enriched_fields` 是否覆盖该字段。

### 1.4 修复 storage.py `update_enriched_fields`

当前只更新 7 个字段，没有 evidence_json。添加该字段更新。

### 1.5 验证

全量 reprocess 后 evidence_json 覆盖率 > 0。

---

## 二、P0 — normalized_position 写入所有路径

### 2.1 检查 static_site.py

LLM 返回 `position_normalized`，确认写入 `normalized_position`。

### 2.2 检查 gaoxiaojob.py

### 2.3 检查 enrich.py

### 2.4 检查 reprocess.py

### 2.5 验证

---

## 三、P0 — quality_score 边界调整

当前 50% 岗位为 `hidden`，需要检查 scoring 规则。

### 3.1 检查 `calculate_job_quality()`

降低 hidden 门槛：`score >= 60 → normal`, `score >= 35 → needs_review`, `else → hidden`

### 3.2 调整 notice-like 扣分

当前 `-30` 过于激进。许多真正岗位也匹配 notice-like 模式。改为 `-15`。

### 3.3 验证

调整后 quality_status=hidden ≤ 20%。

---

## 四、P1 — 老数据重新评分

已有 quality_score 的 339 条需要重新评分（规则调整后）。原有正常和 needs_review 保持不变，但 hidden 重新计算。

### 4.1 新增 store 批量更新 quality_status 方法

### 4.2 执行

---

## 五、P1 — 全量重处理（降速降本）

将 reprocess 改为分批执行，减少一次性 LLM 开销。

### 5.1 按质量状态分批

先处理 `quality_status=hidden` + `evidence_json IS NULL` 的记录。

### 5.2 新增 `--batch-size` 参数

允许控制每批处理数量。

---

## 六、执行顺序

```
Phase 1: 1.1 → 1.2 → 1.3 → 1.4 → 1.5  (evidence 持久化)
Phase 2: 2.1 → 2.2 → 2.3 → 2.4 → 2.5  (normalized_position)
Phase 3: 3.1 → 3.2 → 3.3 → 4.1 → 4.2  (quality 调整 + 重新评分)
Phase 4: 5.1 → 5.2                       (重处理)
```

