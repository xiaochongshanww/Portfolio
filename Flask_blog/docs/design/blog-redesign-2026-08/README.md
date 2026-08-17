# Flask Blog Redesign — 2026-08

本目录归档 2026 年 8 月个人博客重新设计阶段的视觉探索原型。

## 背景

现有 `Flask_blog` 功能与工程能力继续保留，本阶段先探索前台视觉语言与首页信息架构，不直接修改生产 Vue 页面。

设计目标从传统“博客首页”转向更明确的个人开发者数字空间，同时避免继续沿用旧版的蓝紫渐变、玻璃拟态、重卡片化、侧边栏内容社区式布局。

## 第一轮：完整首页方向

- `01-editorial-minimal.html` — Editorial Minimalism + Developer Portfolio。强调排版、留白、项目和 Writing。
- `02-indie-hacker.html` — Indie Hacker / Personal Playground。强调个人开发者、side project、正在构建。
- `03-digital-garden.html` — Digital Garden。强调长期知识沉淀、主题网络与内容成熟度。

这三版后来发现都不同程度带有 Editorial / 数字杂志式骨架，因此继续扩展非 Editorial 候选。

## 第二轮：非 Editorial 首屏探索

- `04-bento-developer.html` — Bento Developer。模块化、现代、产品化。
- `05-developer-workspace.html` — Developer Workspace。像进入开发者自己的数字工作空间。
- `06-playful-developer.html` — Playful Developer。更有趣、更个人化，降低严肃的 Portfolio 感。
- `07-calm-personal-web.html` — Calm Personal Web。安静、自然，弱化开发者模板感。
- `08-directions-comparison.html` — 第二轮四方向的快速比较入口。

## 当前状态

这些文件都是设计探索，不代表最终 UI 决策，也不应直接视为生产实现。后续应先筛选 1–2 个方向，再形成完整高保真首页，并最终映射回现有 Vue 3 + Tailwind + Element Plus 前端体系。

## 当前讨论中的候选重点

1. Bento Developer
2. Developer Workspace
3. Playful Developer
4. Calm Personal Web

归档目的主要是保留设计决策过程，避免后续迭代丢失已经探索过的方向。