# 回答级盲测集阅读版

程序唯一数据源为 `data/evaluation/answer_holdout.jsonl`。本文档用于阅读和评审，不参与自动判定。

## 分布

| 类型 | 数量 | 目标 |
| --- | ---: | --- |
| 精确取值 | 8 | 数值、单位、表号与截图 |
| 公式 | 2 | LaTeX、变量、单位与条文 |
| 条件边界 | 8 | 相邻类别、跨度、使用条件 |
| 错误前提 | 4 | 主动纠正用户给出的错误值 |
| 无依据 | 2 | 明确拒答且不编造 |
| 合计 | 24 | 独立于检索调优集 |

## 用例

| ID | 类型 | 问题 | 核心期望 |
| --- | --- | --- | --- |
| answer-office-live-load | 精确取值 | 普通办公楼办公室楼面活荷载 | 2.0 kN/m²，表5.1.1 |
| answer-classroom-live-load | 精确取值 | 一般教室楼面活荷载 | 2.5 kN/m²，表5.1.1 |
| answer-accessible-roof-load | 精确取值 | 上人屋面活荷载 | 2.0 kN/m²，表5.3.1 |
| answer-non-accessible-roof-load | 精确取值 | 不上人屋面活荷载 | 0.5 kN/m²，表5.3.1 |
| answer-roof-garden-load | 精确取值 | 屋顶花园活荷载 | 3.0 kN/m²，表5.3.1 |
| answer-reduction-9-20 | 精确取值 | 9至20层折减系数 | 0.60，表5.1.2 |
| answer-reduction-over-20 | 精确取值 | 超过20层折减系数 | 0.55，表5.1.2 |
| answer-wind-factor-b-100 | 精确取值 | B类100m风压高度变化系数 | 2.00，表8.2.1 |
| answer-snow-formula | 公式 | 雪荷载标准值公式 | $s_k=\mu_r s_0$，第7.1.1条 |
| answer-wind-formula | 公式 | 主要受力结构风荷载公式 | $w_k=\beta_z\mu_s\mu_z w_0$，第8.1.1条 |
| answer-firetruck-6m | 条件边界 | 6m×6m消防车荷载 | 20.0 kN/m² |
| answer-firetruck-3m | 条件边界 | 3m×3m消防车荷载 | 35.0 kN/m² |
| answer-other-kitchen | 条件边界 | 其他厨房活荷载 | 2.0 kN/m² |
| answer-restaurant-kitchen | 条件边界 | 餐厅厨房活荷载 | 4.0 kN/m² |
| answer-office-corridor | 条件边界 | 办公楼走廊门厅 | 2.5 kN/m² |
| answer-residential-corridor | 条件边界 | 住宅走廊门厅 | 2.0 kN/m² |
| answer-crowded-balcony | 条件边界 | 人员密集阳台 | 3.5 kN/m² |
| answer-other-balcony | 条件边界 | 其他阳台 | 2.5 kN/m² |
| answer-correct-office-false-value | 错误前提 | 办公楼是否必须取3.5 | 否，通常为2.0 kN/m² |
| answer-correct-roof-false-value | 错误前提 | 不上人屋面是否取2.0 | 否，应为0.5 kN/m² |
| answer-correct-wind-factor | 错误前提 | B类100m是否为1.50 | 否，应为2.00 |
| answer-correct-reduction-boundary | 错误前提 | 超过20层是否为0.60 | 否，应为0.55 |
| answer-refuse-nonexistent-clause | 无依据 | 查询第99.9.9条 | 明确说明不存在或无依据 |
| answer-refuse-moon-base | 无依据 | 月球基地气闸舱精确荷载 | 明确拒答，不按常识补值 |

## 自动检查

- 固定回答章节；
- 必含事实、任选事实和禁用事实；
- 单位的普通文本及 LaTeX 等价形式；
- 规范编号、条文号和表号；
- 引用是否属于本次 `rag_trace`；
- Markdown 图片是否来自本次候选；
- 图片路由、本地文件、PDF 页码和 HTTP 响应；
- 无依据问题是否明确拒答。
