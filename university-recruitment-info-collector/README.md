# 高校招聘信息采集项目

用于搜集、整理和分析高校招聘信息。项目会接入多个信息源，不同来源可能使用不同采集方式，统一清洗后沉淀为结构化招聘数据，并为用户提供岗位匹配入口。

## 目标

- 分阶段接入高校人才网、招聘公众号文章等信息源
- 为不同信息源保留独立采集器和解析逻辑
- 提取学校、岗位、学院/部门、学科方向、报名截止时间、原文链接等信息
- 保存原始页面和结构化数据，方便后续筛选、统计和提醒
- 支持用户输入个人背景、研究方向、求职偏好后，自动推荐匹配岗位
- 可接入 LLM 对岗位要求和用户条件进行语义分析，输出匹配理由和风险提示

## 产品流程

```text
多来源招聘信息采集
        ↓
招聘信息清洗、去重、结构化
        ↓
用户输入个人信息和求职偏好
        ↓
规则匹配 + LLM 语义分析
        ↓
输出匹配岗位、匹配理由、待补充材料和风险提示
```

## 信息源规划

### 第一阶段：高校人才网

面向高校人才网、学校人才招聘网、人事处招聘栏目等公开网页。

主要采集方式：

- 站点列表页抓取
- 公告详情页解析
- 增量采集和去重
- 页面 HTML 原文归档

### 后续阶段：招聘信息公众号文章

面向微信公众号或其他内容平台中的招聘汇总文章。

可能采集方式：

- 文章链接或转存内容解析
- 正文中的学校、岗位、截止时间抽取
- 图片或富文本内容的结构化处理
- 与网页来源招聘信息去重合并

## 建议字段

### 招聘信息字段

- `school`: 学校名称
- `department`: 学院或用人部门
- `position`: 岗位名称
- `discipline`: 学科方向
- `location`: 工作地点
- `deadline`: 报名截止时间
- `source_type`: 信息源类型，例如 `university_talent_site`、`wechat_article`
- `source_name`: 信息源名称，例如站点名、公众号名
- `source_url`: 原文链接
- `published_at`: 发布时间
- `collected_at`: 采集时间

### 用户信息字段

- `education`: 最高学历
- `major`: 专业
- `research_direction`: 研究方向
- `keywords`: 个人关键词，例如技术方向、论文方向、项目经验
- `target_locations`: 期望地区
- `target_school_types`: 期望学校类型
- `job_preferences`: 岗位偏好
- `constraints`: 限制条件，例如必须解决编制、配偶工作、年龄要求等

### 匹配结果字段

- `job_id`: 岗位 ID
- `match_score`: 匹配分数
- `match_reasons`: 匹配理由
- `potential_risks`: 潜在风险或不满足项
- `suggested_actions`: 建议补充材料或下一步动作
- `llm_summary`: LLM 分析摘要

## 目录结构

```text
university-recruitment-info-collector/
├── data/
│   ├── raw/        # 原始页面、文章正文、下载文件等
│   ├── processed/  # 清洗后的结构化中间数据
│   └── exports/    # CSV/Excel/JSON 等导出结果
├── docs/
│   ├── product/    # 产品需求、用户流程、匹配逻辑说明
│   └── sources/    # 目标站点、公众号、字段规范和采集说明
├── src/
│   └── university_recruitment/
│       ├── llm/         # LLM 接入、提示词、结构化分析
│       ├── matching/    # 岗位匹配、打分、排序逻辑
│       ├── sources/
│       │   ├── university_talent_sites/  # 高校人才网采集器
│       │   └── wechat_articles/          # 公众号文章采集器
│       └── user_portal/ # 用户信息录入和结果展示入口
└── README.md
```

## 本地运行

创建环境并安装依赖：

```bash
python -m venv .venv
source .venv/bin/activate
pip install .
playwright install chromium
```

写入示例招聘数据：

```bash
university-recruitment-seed
```

从已配置的信息源采集真实招聘列表：

```bash
university-recruitment-collect
```

当前默认只启用已接入的广州高校信息源。也可以显式指定广州过滤：

```bash
university-recruitment-collect --source 广州
```

先预览采集结果但不写入数据库：

```bash
university-recruitment-collect --dry-run
```

启动 API：

```bash
university-recruitment-api
```

查看采集数据质量报告：

```bash
university-recruitment-report
```

查看信息源健康报告，定位采集为空、禁用源分类和下一步适配动作：

```bash
university-recruitment-report --source-health
```

主要接口：

- `GET /health`: 健康检查
- `GET /jobs`: 查看当前岗位数据
- `POST /match`: 提交用户画像并返回匹配岗位

信息源配置位于 `config/sources.toml`，第一批信息源说明位于 `docs/sources/university_talent_sites.md`。

广州高校候选池位于 `docs/sources/guangzhou_universities.md`。当前候选池约 84 所高校，均已纳入配置或明确标记；不可静态采集、动态系统、合并管理和过宽聚合源会以禁用源形式保留。

聚合招聘信息源位于 `docs/sources/aggregators.md`。高校人才网/高才网已纳入聚合源配置，普通 HTTP 采集会被 403 拒绝，因此当前使用 Playwright 浏览器采集。

`POST /match` 请求示例：

```json
{
  "user": {
    "education": "博士",
    "major": "计算机科学与技术",
    "research_direction": "人工智能",
    "keywords": ["机器学习", "数据挖掘"],
    "target_locations": ["广州"],
    "target_school_types": ["双一流"],
    "job_preferences": ["教学科研岗"],
    "constraints": ["编制"]
  },
  "limit": 5,
  "use_llm": false
}
```

## 后续计划

1. 整理第一阶段高校人才网目标列表
2. 定义统一招聘信息数据结构
3. 编写高校人才网页面采集和详情解析脚本
4. 增加去重、字段清洗和增量采集逻辑
5. 定义用户画像字段和岗位匹配结果结构
6. 实现基础规则匹配和排序
7. 接入 LLM 分析岗位要求与用户背景的匹配度
8. 预留公众号文章采集入口
9. 提供用户录入入口和匹配结果展示
