# 高校人才网信息源

当前项目仅关注广州高校招聘信息。非广州高校源保留在配置文件中作为历史参考，但默认禁用。

广州高校候选池见 `docs/sources/guangzhou_universities.md`。该候选池按公开高校名单整理，当前约 84 所，其中本科 40 所、专科 44 所。

聚合招聘信息源见 `docs/sources/aggregators.md`。聚合源用于发现岗位，官方源用于权威核验。

| 学校 | 信息源 | URL | 采集器 |
| --- | --- | --- | --- |
| 北京大学 | 北京大学人事部-教学科研 | https://hr.pku.edu.cn/rczp/jxky/index.htm | `static_list` |
| 复旦大学 | 复旦大学人事处-教学科研 | https://hr.fudan.edu.cn/15364/list.htm | `static_list` |
| 复旦大学 | 复旦大学人事处-专任岗位 | https://hr.fudan.edu.cn/zrgw/list.htm | `static_list` |
| 中国科学技术大学 | 中国科学技术大学人才招聘网-最新招聘公告 | https://employment.ustc.edu.cn/cn/indexnewslist.aspx?signtype=51 | `static_list` |
| 南京大学 | 南京大学人力资源处-教学科研人才招聘 | https://hr.nju.edu.cn/6308/list1.htm | 暂停启用，本机访问存在 TLS 握手失败 |
| 中山大学 | 中山大学人才招聘网 | https://rcb.sysu.edu.cn/ | `static_list` |
| 华南理工大学 | 华南理工大学人事处 | https://www2.scut.edu.cn/hr/_t287/main.htm | `static_list` |
| 暨南大学 | 暨南大学人力资源开发与管理处-教学科研人才招聘 | https://hrdam.jnu.edu.cn/298/list.htm | `static_list` |
| 广州大学 | 广州大学-高层次人才招聘公告 | https://www.gzhu.edu.cn/rczp1/gccrczpgg.htm | `static_list` |

## 当前启用范围

默认启用 4 所广州高校：

- 中山大学
- 华南理工大学
- 暨南大学
- 广州大学

后续应从候选池逐校补充招聘入口。公办、民办高校同等优先级，接入顺序主要看招聘入口是否公开可访问、页面是否可稳定采集、岗位内容是否与用户目标相关。

## 采集策略

- 第一版只采集列表页中的招聘链接和标题。
- 标题中包含招聘、人才、教师、博士后、岗位、引进等关键词时进入候选。
- 后续对每个站点补详情页解析，提取正文、发布时间、截止时间、岗位要求等字段。
- 南京大学人力资源处当前从本机访问会出现 TLS 握手失败，后续可尝试浏览器采集或独立 HTTP 客户端适配。

## 后续补充

- 上海交通大学人才招聘网入口需要单独确认 `join.sjtu.edu.cn` 的页面结构，再决定是否用静态页面采集或浏览器采集。
- 微信公众号文章采集后续单独维护为 `wechat_articles` 信息源。
