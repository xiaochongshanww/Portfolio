# 评估集阅读版

本文档是 `data/evaluation/queries.jsonl` 的人工阅读版，用于评审检索评估覆盖面、问题类型和期望命中条件。原始 JSONL 仍是程序评估的唯一数据源，本文档不参与自动化测试。

## 总览

- 用例总数：100
- 数据文件：`data/evaluation/queries.jsonl`
- 用途：验证结构规范知识库的检索质量，重点覆盖条文、表格取值、定义、分类、规范简称、规范编号、多规范对比和公式类问题。

## 类型分布

| 类型 | 数量 | 说明 |
| --- | ---: | --- |
| table | 29 | 表格、标准值、系数、限值、取值类问题 |
| clause | 17 | 明确条文号检索问题 |
| general | 15 | 规范性要求、注意事项、适用范围等一般问题 |
| definition | 11 | 概念定义类问题 |
| classification | 9 | 分类、等级、设防类别类问题 |
| alias | 7 | 规范简称、口语化表达类问题 |
| code | 6 | 规范编号类问题 |
| formula | 3 | 公式、表达式类问题 |
| multi_spec | 3 | 跨规范关系类问题 |

## 字段说明

| 字段 | 含义 |
| --- | --- |
| ID | 用例唯一标识，对应 JSONL 中的 `id` |
| 类型 | 用例类型，对应 JSONL 中的 `type` |
| 问题 | 用户查询文本，对应 JSONL 中的 `query` |
| 期望来源 | 期望召回结果应命中的规范名称或规范编号 |
| 条文号 | 条文类问题期望命中的条文号；非条文类为 `-` |
| 关键词 | 期望召回文本中应覆盖的关键概念或取值 |

## 完整清单

| ID | 类型 | 问题 | 期望来源 | 条文号 | 关键词 |
| --- | --- | --- | --- | --- | --- |
| clause-seismic-8-2-1 | clause | 抗震规范第 8.2.1 条是什么？ | 建筑抗震设计规范<br>GB 50011-2010 | 8.2.1 | 抗震 |
| load-live-value | table | 建筑结构荷载规范里住宅楼面活荷载标准值是多少？ | 建筑结构荷载规范<br>GB 50009-2012 | - | 住宅、活荷载 |
| reliability-standard | definition | 建筑结构可靠性设计统一标准适用于什么？ | 建筑结构可靠性设计统一标准<br>GB 50068-2018 | - | 可靠性 |
| fortification-category | classification | 抗震设防分类标准如何划分建筑工程类别？ | 建筑工程抗震设防分类标准<br>GB 50223-2008 | - | 设防、分类 |
| construction-quality | general | 施工质量验收统一标准的验收要求有哪些？ | 建筑工程施工质量验收统一标准<br>GB 50300-2013 | - | 验收 |
| alias-seismic | alias | 抗规里多遇地震作用怎么考虑？ | 建筑抗震设计规范<br>GB 50011-2010 | - | 地震 |
| alias-load | alias | 荷规中风荷载相关规定在哪里？ | 建筑结构荷载规范<br>GB 50009-2012 | - | 风荷载 |
| code-query-load | code | GB50009 里的雪荷载怎么取值？ | 建筑结构荷载规范<br>GB 50009-2012 | - | 雪荷载 |
| code-query-seismic | code | GB 50011-2010 对场地类别有什么规定？ | 建筑抗震设计规范<br>GB 50011-2010 | - | 场地 |
| clause-general-3-1-1 | clause | 3.1.1 条的基本要求是什么？ | GB | 3.1.1 | - |
| reliability-limit-state | definition | 可靠性统一标准中极限状态如何分类？ | 建筑结构可靠性设计统一标准<br>GB 50068-2018 | - | 极限状态 |
| load-combination | general | 荷载组合应考虑哪些情况？ | 建筑结构荷载规范<br>GB 50009-2012 | - | 荷载组合 |
| seismic-fortification-intensity | general | 抗震设防烈度在哪里规定？ | 建筑抗震设计规范<br>GB 50011-2010 | - | 设防烈度 |
| category-key-building | classification | 重点设防类建筑如何判定？ | 建筑工程抗震设防分类标准<br>GB 50223-2008 | - | 重点设防 |
| quality-subdivision | general | 检验批和分项工程验收有什么要求？ | 建筑工程施工质量验收统一标准<br>GB 50300-2013 | - | 检验批、分项工程 |
| table-load-roof | table | 屋面活荷载标准值应查哪个表？ | 建筑结构荷载规范<br>GB 50009-2012 | - | 屋面、活荷载 |
| seismic-structure-system | general | 抗震结构体系有哪些基本要求？ | 建筑抗震设计规范<br>GB 50011-2010 | - | 结构体系 |
| reliability-design-life | definition | 设计使用年限在可靠性标准里怎么规定？ | 建筑结构可靠性设计统一标准<br>GB 50068-2018 | - | 设计使用年限 |
| category-school | classification | 学校建筑抗震设防类别如何确定？ | 建筑工程抗震设防分类标准<br>GB 50223-2008 | - | 学校、设防类别 |
| quality-acceptance-record | general | 验收记录应包含哪些内容？ | 建筑工程施工质量验收统一标准<br>GB 50300-2013 | - | 验收记录 |
| load-crane | general | 吊车荷载应如何考虑？ | 建筑结构荷载规范<br>GB 50009-2012 | - | 吊车荷载 |
| seismic-nonstructural | general | 非结构构件抗震设计有什么要求？ | 建筑抗震设计规范<br>GB 50011-2010 | - | 非结构构件 |
| reliability-material | definition | 材料强度标准值和设计值有什么关系？ | 建筑结构可靠性设计统一标准<br>GB 50068-2018 | - | 标准值、设计值 |
| multi-spec-fortification | multi_spec | 抗震设计和设防分类两个规范对设防目标有什么区别？ | 建筑抗震设计规范<br>建筑工程抗震设防分类标准 | - | 设防 |
| ambiguous-clause-5-1-1 | clause | 5.1.1 条说明了什么？ | GB | 5.1.1 | - |
| table-load-office-live | table | 办公楼的楼面活荷载标准值取多少？ | 建筑结构荷载规范<br>GB 50009-2012 | - | 办公楼、2.0 |
| table-load-hospital-ward | table | 医院病房楼面均布活荷载标准值是多少？ | 建筑结构荷载规范<br>GB 50009-2012 | - | 医院病房、2.0 |
| table-load-classroom | table | 教室楼面活荷载标准值是多少？ | 建筑结构荷载规范<br>GB 50009-2012 | - | 教室、2.5 |
| table-load-canteen | table | 食堂和餐厅的楼面活荷载标准值怎么取？ | 建筑结构荷载规范<br>GB 50009-2012 | - | 食堂、餐厅、2.5 |
| table-load-theater | table | 礼堂剧场影院有固定座位看台的楼面活荷载标准值是多少？ | 建筑结构荷载规范<br>GB 50009-2012 | - | 礼堂、剧场、3.0 |
| table-load-balcony-crowd | table | 可能出现人员密集情况的阳台活荷载标准值是多少？ | 建筑结构荷载规范<br>GB 50009-2012 | - | 阳台、人员密集、3.5 |
| table-load-balcony-other | table | 其他阳台的楼面活荷载标准值取多少？ | 建筑结构荷载规范<br>GB 50009-2012 | - | 阳台、其他、2.5 |
| table-load-roof-accessible | table | 上人屋面均布活荷载标准值是多少？ | 建筑结构荷载规范<br>GB 50009-2012 | - | 上人的屋面、2.0 |
| table-load-roof-non-accessible | table | 不上人屋面均布活荷载标准值是多少？ | 建筑结构荷载规范<br>GB 50009-2012 | - | 不上人的屋面、0.5 |
| table-load-helicopter-light | table | 轻型屋面直升机停机坪局部荷载标准值是多少？ | 建筑结构荷载规范<br>GB 50009-2012 | - | 轻型、20 |
| table-load-service-life-factor | table | 楼面和屋面活荷载考虑设计使用年限的调整系数在哪个表？ | 建筑结构荷载规范<br>GB 50009-2012 | - | 表3.2.5、设计使用年限 |
| table-load-floor-reduction | table | 活荷载按楼层的折减系数应查哪个表？ | 建筑结构荷载规范<br>GB 50009-2012 | - | 表5.1.2、折减系数 |
| table-load-ash-roof | table | 屋面积灰荷载标准值应查哪些表？ | 建筑结构荷载规范<br>GB 50009-2012 | - | 屋面积灰荷载、标准值 |
| table-seismic-intensity-acceleration | table | 抗震设防烈度和设计基本地震加速度值的对应关系在哪个表？ | 建筑抗震设计规范<br>GB 50011-2010 | - | 表3.2.2、设计基本地震加速度 |
| table-seismic-plan-irregular | table | 平面不规则的主要类型有哪些？ | 建筑抗震设计规范<br>GB 50011-2010 | - | 平面不规则、扭转不规则 |
| table-seismic-vertical-irregular | table | 竖向不规则的主要类型有哪些？ | 建筑抗震设计规范<br>GB 50011-2010 | - | 竖向不规则、侧向刚度不规则 |
| table-seismic-site-section | table | 有利一般不利和危险地段如何划分？ | 建筑抗震设计规范<br>GB 50011-2010 | - | 有利地段、危险地段 |
| table-seismic-soil-type | table | 土的类型划分和剪切波速范围在哪里规定？ | 建筑抗震设计规范<br>GB 50011-2010 | - | 土的类型、剪切波速 |
| table-seismic-site-cover | table | 各类建筑场地覆盖层厚度应查哪个表？ | 建筑抗震设计规范<br>GB 50011-2010 | - | 覆盖层厚度、建筑场地 |
| table-reliability-safety-level | table | 建筑结构安全等级如何划分？ | 建筑结构可靠性设计统一标准<br>GB 50068-2018 | - | 安全等级、破坏后果 |
| table-reliability-index | table | 结构构件可靠指标 beta 应查哪个表？ | 建筑结构可靠性设计统一标准<br>GB 50068-2018 | - | 可靠指标、安全等级 |
| table-reliability-design-life | table | 建筑结构设计使用年限有哪些类别？ | 建筑结构可靠性设计统一标准<br>GB 50068-2018 | - | 设计使用年限、临时性 |
| table-reliability-importance-factor | table | 结构重要性系数如何取值？ | 建筑结构可靠性设计统一标准<br>GB 50068-2018 | - | 结构重要性系数 |
| table-reliability-action-factor | table | 建筑结构作用分项系数怎么取？ | 建筑结构可靠性设计统一标准<br>GB 50068-2018 | - | 作用分项系数 |
| table-quality-sampling | table | 检验批最小抽样数量如何确定？ | 建筑工程施工质量验收统一标准<br>GB 50300-2013 | - | 检验批、最小抽样数量 |
| table-quality-division | table | 建筑工程分部工程和分项工程划分在哪个表？ | 建筑工程施工质量验收统一标准<br>GB 50300-2013 | - | 分部工程、分项工程 |
| table-quality-site-record | table | 施工现场质量管理检查记录采用哪个表？ | 建筑工程施工质量验收统一标准<br>GB 50300-2013 | - | 施工现场质量管理检查记录 |
| clause-load-5-1-1 | clause | 荷载规范第5.1.1条规定了什么？ | 建筑结构荷载规范<br>GB 50009-2012 | 5.1.1 | 表5.1.1 |
| clause-load-5-1-2 | clause | 荷载规范第5.1.2条关于活荷载折减系数有什么要求？ | 建筑结构荷载规范<br>GB 50009-2012 | 5.1.2 | 折减系数 |
| clause-load-5-1-3 | clause | 荷载规范第5.1.3条对消防车活荷载有什么规定？ | 建筑结构荷载规范<br>GB 50009-2012 | 5.1.3 | 消防车 |
| clause-load-3-1-4 | clause | 荷载规范第3.1.4条如何规定荷载标准值？ | 建筑结构荷载规范<br>GB 50009-2012 | 3.1.4 | 标准值 |
| clause-load-7-1-1 | clause | 荷载规范第7.1.1条关于雪荷载标准值怎么说？ | 建筑结构荷载规范<br>GB 50009-2012 | 7.1.1 | 雪荷载 |
| clause-load-8-1-1 | clause | 荷载规范第8.1.1条风荷载有什么基本规定？ | 建筑结构荷载规范<br>GB 50009-2012 | 8.1.1 | 风荷载 |
| clause-seismic-3-1-1 | clause | 抗震规范第3.1.1条的设防基本要求是什么？ | 建筑抗震设计规范<br>GB 50011-2010 | 3.1.1 | 抗震设防 |
| clause-seismic-3-4-3 | clause | 抗震规范第3.4.3条对不规则建筑有什么要求？ | 建筑抗震设计规范<br>GB 50011-2010 | 3.4.3 | 不规则 |
| clause-seismic-4-1-1 | clause | 抗震规范第4.1.1条如何划分有利不利地段？ | 建筑抗震设计规范<br>GB 50011-2010 | 4.1.1 | 有利、不利 |
| clause-seismic-4-1-3 | clause | 抗震规范第4.1.3条关于土的类型如何规定？ | 建筑抗震设计规范<br>GB 50011-2010 | 4.1.3 | 土的类型 |
| clause-seismic-4-3-2 | clause | 抗震规范第4.3.2条液化判别有什么要求？ | 建筑抗震设计规范<br>GB 50011-2010 | 4.3.2 | 液化 |
| clause-reliability-3-2-1 | clause | 可靠性统一标准第3.2.1条关于安全等级怎么规定？ | 建筑结构可靠性设计统一标准<br>GB 50068-2018 | 3.2.1 | 安全等级 |
| clause-reliability-3-3-3 | clause | 可靠性统一标准第3.3.3条关于设计使用年限怎么规定？ | 建筑结构可靠性设计统一标准<br>GB 50068-2018 | 3.3.3 | 设计使用年限 |
| clause-quality-3-0-9 | clause | 施工质量验收统一标准第3.0.9条关于抽样数量怎么规定？ | 建筑工程施工质量验收统一标准<br>GB 50300-2013 | 3.0.9 | 抽样数量 |
| definition-load-permanent | definition | 什么是永久荷载？ | 建筑结构荷载规范<br>GB 50009-2012 | - | 永久荷载 |
| definition-load-variable | definition | 什么是可变荷载？ | 建筑结构荷载规范<br>GB 50009-2012 | - | 可变荷载 |
| definition-load-accidental | definition | 什么是偶然荷载？ | 建筑结构荷载规范<br>GB 50009-2012 | - | 偶然荷载 |
| definition-seismic-action | definition | 什么是地震作用？ | 建筑抗震设计规范<br>GB 50011-2010 | - | 地震作用 |
| definition-seismic-site-category | definition | 建筑抗震设计规范中场地类别是什么意思？ | 建筑抗震设计规范<br>GB 50011-2010 | - | 场地类别 |
| definition-reliability-limit-state | definition | 什么是极限状态？ | 建筑结构可靠性设计统一标准<br>GB 50068-2018 | - | 极限状态 |
| definition-quality-inspection-lot | definition | 施工质量验收中检验批是什么意思？ | 建筑工程施工质量验收统一标准<br>GB 50300-2013 | - | 检验批 |
| classification-seismic-standard-category | classification | 建筑工程抗震设防类别分为哪几类？ | 建筑工程抗震设防分类标准<br>GB 50223-2008 | - | 特殊设防、重点设防 |
| classification-special-fortification | classification | 特殊设防类建筑如何理解？ | 建筑工程抗震设防分类标准<br>GB 50223-2008 | - | 特殊设防 |
| classification-standard-fortification | classification | 标准设防类建筑如何判定？ | 建筑工程抗震设防分类标准<br>GB 50223-2008 | - | 标准设防 |
| classification-moderate-fortification | classification | 适度设防类建筑有什么要求？ | 建筑工程抗震设防分类标准<br>GB 50223-2008 | - | 适度设防 |
| classification-hospital-fortification | classification | 医院建筑抗震设防类别如何确定？ | 建筑工程抗震设防分类标准<br>GB 50223-2008 | - | 医院 |
| classification-school-fortification-detail | classification | 中小学校舍抗震设防类别如何确定？ | 建筑工程抗震设防分类标准<br>GB 50223-2008 | - | 学校 |
| formula-load-snow | formula | 雪荷载标准值的计算公式是什么？ | 建筑结构荷载规范<br>GB 50009-2012 | - | 雪荷载标准值 |
| formula-load-wind | formula | 风荷载标准值如何计算？ | 建筑结构荷载规范<br>GB 50009-2012 | - | 风荷载标准值 |
| formula-reliability-action-combination | formula | 可靠性统一标准中承载能力极限状态作用组合表达式是什么？ | 建筑结构可靠性设计统一标准<br>GB 50068-2018 | - | 承载能力极限状态 |
| alias-load-snow | alias | 荷规里雪压和雪荷载怎么取？ | 建筑结构荷载规范<br>GB 50009-2012 | - | 雪荷载 |
| alias-load-wind | alias | 荷规风压高度变化系数在哪查？ | 建筑结构荷载规范<br>GB 50009-2012 | - | 风压高度变化系数 |
| alias-seismic-site | alias | 抗规场地类别和覆盖层厚度怎么确定？ | 建筑抗震设计规范<br>GB 50011-2010 | - | 场地、覆盖层 |
| alias-seismic-irregular | alias | 抗规里平面不规则和竖向不规则怎么判定？ | 建筑抗震设计规范<br>GB 50011-2010 | - | 不规则 |
| alias-reliability-safety | alias | 可靠性统一标准安全等级怎么划分？ | 建筑结构可靠性设计统一标准<br>GB 50068-2018 | - | 安全等级 |
| code-gb50068-design-life | code | GB50068 对设计使用年限有什么规定？ | 建筑结构可靠性设计统一标准<br>GB 50068-2018 | - | 设计使用年限 |
| code-gb50300-inspection-lot | code | GB50300 对检验批验收有什么要求？ | 建筑工程施工质量验收统一标准<br>GB 50300-2013 | - | 检验批 |
| code-gb50223-school | code | GB50223 对学校建筑设防类别怎么规定？ | 建筑工程抗震设防分类标准<br>GB 50223-2008 | - | 学校 |
| code-gb50011-liquefaction | code | GB50011 液化判别有哪些规定？ | 建筑抗震设计规范<br>GB 50011-2010 | - | 液化 |
| general-load-live-note | general | 民用建筑楼面活荷载表的注释有哪些需要注意？ | 建筑结构荷载规范<br>GB 50009-2012 | - | 本表、活荷载 |
| general-load-crane-dynamic | general | 吊车荷载动力系数如何考虑？ | 建筑结构荷载规范<br>GB 50009-2012 | - | 动力系数 |
| general-load-ash | general | 屋面积灰荷载适用于哪些情况？ | 建筑结构荷载规范<br>GB 50009-2012 | - | 积灰荷载 |
| general-seismic-performance | general | 建筑抗震性能化设计有哪些基本要求？ | 建筑抗震设计规范<br>GB 50011-2010 | - | 性能化设计 |
| general-seismic-nonstructural-detail | general | 非结构构件抗震措施应注意什么？ | 建筑抗震设计规范<br>GB 50011-2010 | - | 非结构构件 |
| general-quality-main-control | general | 主控项目和一般项目验收有什么区别？ | 建筑工程施工质量验收统一标准<br>GB 50300-2013 | - | 主控项目、一般项目 |
| general-quality-division | general | 分部工程验收应满足哪些条件？ | 建筑工程施工质量验收统一标准<br>GB 50300-2013 | - | 分部工程 |
| multi-spec-load-reliability-standard-value | multi_spec | 荷载规范和可靠性统一标准中标准值的含义有什么关系？ | 建筑结构荷载规范<br>建筑结构可靠性设计统一标准 | - | 标准值 |
| multi-spec-seismic-category-school | multi_spec | 抗震规范和设防分类标准对学校建筑设防要求有什么关系？ | 建筑抗震设计规范<br>建筑工程抗震设防分类标准 | - | 学校、设防 |
