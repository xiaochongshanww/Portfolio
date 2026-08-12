# 📚 文档中心

本目录是 Flask Blog 平台的全部项目文档入口，按大型项目标准分级组织。

## 目录导航

| 目录 | 内容 | 入口 |
|------|------|------|
| `getting-started/` | 快速上手与开发环境 | [开发快速开始](getting-started/quickstart.md) · [本地开发](getting-started/development.md) |
| `architecture/` | 系统架构总览 | [架构概览](architecture/overview.md) |
| `backend/` | 后端模块说明 | [后端概览](backend/overview.md) |
| `design/` | 各模块设计文档 | [备份系统](design/backup-system.md) · [日志管理](design/log-management.md) · [安全监控](design/security-monitoring.md) · [首页设计](design/homepage.md) · [封面图优化](design/cover-image.md) |
| `product/` | 产品需求文档 | [PRD](product/prd.md) · [需求描述](product/requirements.md) |
| `operations/` | 部署与运维 | [生产部署](operations/deployment.md) · [性能基线](operations/performance.md) · [GHCR 配置](operations/ghcr-setup.md) |
| `engineering/` | 工程规范与质量 | [开发规范](engineering/standards.md) · [测试体系](engineering/testing.md) · [代码审查](engineering/code-review-report.md) · [重构计划](engineering/refactoring-plan.md) · [规范化评估](engineering/standardization-review.md) |
| `reference/` | 参考资料 | [Token 过期提醒](reference/token-expiry-reminder.md) |

## 文档索引

### getting-started — 快速上手
- [开发快速开始（Docker 开发环境）](getting-started/quickstart.md) — 一键启动、调试、故障排除
- [本地开发设置](getting-started/development.md) — 本地运行前后端

### architecture — 架构
- [系统架构概览](architecture/overview.md) — 整体架构 / 后端模块 / 前端结构 / 部署与安全架构

### backend — 后端
- [后端模块说明](backend/overview.md) — 本地设置、健康检查、Celery、限流、缓存、指标、API

### design — 模块设计
- [站点备份系统设计](design/backup-system.md) — 物理备份引擎、增量备份、恢复管理
- [日志管理系统设计](design/log-management.md) — 日志采集、存储、查询、配置
- [安全监控方案](design/security-monitoring.md) — 威胁检测、IP 封禁、监控面板
- [首页设计](design/homepage.md) — 首页信息架构与视觉方案
- [封面图 UX 优化](design/cover-image.md) — 封面图交互与性能优化

### product — 产品
- [产品需求文档（PRD）](product/prd.md) — 功能清单、用户故事、数据模型、流程与验收标准
- [原始需求描述](product/requirements.md) — 角色权限、内容创作、前端体验、非功能需求

### operations — 部署与运维
- [生产部署指南](operations/deployment.md) — Docker 一键部署、备份恢复、运维命令
- [性能基线](operations/performance.md) — 指标目标、Lighthouse/Prometheus 监控切入点
- [GHCR 镜像配置](operations/ghcr-setup.md) — GitHub Container Registry 推送与访问

### engineering — 工程规范与质量
- [项目开发规范](engineering/standards.md) — 代码结构、测试、依赖、版本控制、安全要求
- [测试体系评估](engineering/testing.md) — 测试层级、覆盖策略与工具链
- [代码审查计划](engineering/code-review-plan.md) — 审查范围与安排
- [代码审查报告](engineering/code-review-report.md) — 审查结果与整改
- [重构计划](engineering/refactoring-plan.md) — 阶段性重构方案
- [深度重构方案](engineering/refactoring-deep-plan.md) — 架构级重构详细方案
- [项目规范化评估报告](engineering/standardization-review.md) — 工程规范化的客观评估与改进路线

### reference — 参考资料
- [Token 过期提醒](reference/token-expiry-reminder.md) — GitHub Token 轮换备忘

## 文档规范

- **命名**：目录与文件统一英文小写（kebab-case）。
- **交叉引用**：使用相对路径链接，随文件移动同步更新。
- **根目录约定**：仅保留 `README.md`（项目入口）与 `CONTRIBUTING.md`（贡献指南，GitHub 特殊展示）。
- **新增文档**：按上表归类放入对应目录；无对应分类时新建 `reference/` 下或与维护者确认。
