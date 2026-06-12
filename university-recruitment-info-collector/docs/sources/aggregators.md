# 聚合招聘信息源

聚合源用于快速发现广州高校招聘信息，和高校官方入口互补。

## 高校人才网/高才网

已记录入口：

| 信息源 | URL | 状态 | 说明 |
| --- | --- | --- | --- |
| 高校人才网-广州站 | https://www.gaoxiaojob.com/column/46.html | 已配置，默认禁用 | 范围较宽，容易混入泛招聘信息 |
| 高校人才网-广州高校栏目 | https://www.gaoxiaojob.com/column/494.html | 默认启用 | 使用 `gaoxiaojob_browser` |
| 高校人才网-广州高校招聘汇总 | https://www.gaoxiaojob.com/hotword/utsl891453 | 默认启用 | 使用 `gaoxiaojob_browser` |

## 使用策略

- 聚合源作为发现源，用于补全学校和岗位覆盖。
- 官方高校入口作为权威源，用于确认公告正文、附件、报名方式、截止时间。
- 聚合源采集到的岗位需要保留 `source_type = aggregator`，方便后续和官方源去重、比对。

## 当前限制

高校人才网页面对普通 `httpx` 请求返回 403，因此不能使用纯静态 HTTP 采集。当前已预留浏览器采集器：

```bash
pip install .
playwright install chromium
university-recruitment-collect --source 高校人才网 --dry-run
```

为避免浏览器逐条打开详情页导致采集过慢，当前高才网聚合源默认只解析每个入口前 5 条详情，其余岗位先保留标题和链接。

后续可选方案：

1. 接入浏览器采集器，使用 Playwright 渲染页面后解析。
2. 分析站点前端接口，若存在公开 JSON API，则直接采集 API。
3. 使用搜索引擎发现高校人才网页面，再回到官方源做核验。
