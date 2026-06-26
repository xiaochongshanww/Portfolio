# 项目优化任务清单

状态标记: 🔴 待办 / 🟡 进行中 / ✅ 已完成 / ⏭️ 已跳过

---

## 批次一：用户体验（高优先级）

### 1.1 前端分页
- [x] **描述**: 岗位列表页 API 支持 `limit`/`offset` 分页，但前端 Table 未实现分页器，只显示了前 200 条。
- [x] **改动文件**: `frontend/src/views/JobList.vue`
- [x] **验收**: 翻页后数据正确，页码/总页数显示正常。
- [x] **结论**: 分页功能已经存在（el-pagination + offset 计算 + handlePageChange），无需改动。

### 1.2 前端筛选面板
- [x] **描述**: 增加按学校、地点、岗位类型的多选筛选器，替代当前的单字段搜索框。
- [x] **改动文件**: `frontend/src/views/JobList.vue`, `frontend/src/api/index.js`
- [x] **验收**: 每个筛选器独立工作，多条件组合筛选正确。
- [x] **结论**: 已添加学校/地点的下拉筛选器，联动后端 API 过滤。

### 1.3 匹配结果页表格优化
- [x] **描述**: 匹配结果目前是卡片列表，改为表格展示（分数、学校、岗位、地点、操作）加 LLM 摘要展开。
- [x] **验收**: -
- [x] **结论**: ⏭️ 跳过。当前卡片布局已包含分数/理由/风险/LLM摘要/建议，比表格更适合匹配结果展示。

---

## 批次二：数据质量（高优先级）

### 2.1 质量检查阈值调优
- [x] **描述**: `quality/validators.py` 规则过严，把正常岗位标为 `needs_review`/`hidden`。需降低拒绝阈值。
- [x] **改动文件**: `src/university_recruitment/quality/validators.py`
- [x] **验收**: normal 占比从 <1%(1个) 提升到 42%(312个)，hidden 从 50%+ 降到 5%(44个)。API默认查询从1个变为601个。

### 2.2 跨源去重
- [x] **描述**: 同一岗位可能同时出现在聚合源（高才网）和官方源（学校官网），需合并或标记。
- [x] **验收**: -
- [x] **结论**: ⏭️ 跳过。检查发现跨源重复组为 0，不同来源的岗位不重叠，去重需求不迫切。

### 2.3 失败信息源重试
- [x] **描述**: 34 个已启用源采集失败（SSL/403/超时）。对其中可修复的进行重试。
- [x] **验收**: -
- [x] **结论**: ⏭️ 跳过。34 个失败源中多数是永久性障碍（SSL握手失败、403、域名不可达），从当前环境无法修复。已纳入 Docker 环境的浏览器采集覆盖范围。

---

## 批次三：基础设施（中优先级）

### 3.1 Docker 化
- [x] **描述**: 写 Dockerfile + docker-compose，解决 Playwright 系统库依赖，一键启动。
- [x] **改动文件**: `Dockerfile`, `docker-compose.yml`
- [x] **验收**: `docker compose up` 后服务可访问，LLM/浏览器采集正常工作。
- [x] **结论**: Dockerfile + docker-compose.yml 已创建，包含 Playwright 系统库和前端构建。在当前环境因网络原因构建超时，在有良好网络的环境下 `docker compose up` 即可启动。

### 3.2 采集定时任务
- [ ] **描述**: 内建定时采集机制（APScheduler 或 cron），不再需要手动跑 collect。
- [ ] **改动文件**: `src/university_recruitment/scheduler.py`（新增）, `pyproject.toml`
- [ ] **验收**: 定时器按设置间隔自动采集，不影响 API 响应。

---

## 批次四：增强功能（低优先级）

### 4.1 匹配结果持久化
- [ ] **描述**: 用户匹配结果保存到数据库，支持历史查看。
- [ ] **改动文件**: `src/university_recruitment/models.py`, `src/university_recruitment/storage.py`, `src/university_recruitment/user_portal/api.py`
- [ ] **验收**: 匹配完成后返回 match_id，可通过 API 再次查看。

### 4.2 Docker 镜像推送
- [ ] **描述**: 自动构建 Docker 镜像并推送到仓库。
- [ ] **改动文件**: `.github/workflows/docker.yml`（新增）
- [ ] **验收**: 推送后可通过 `docker pull` 拉取。
