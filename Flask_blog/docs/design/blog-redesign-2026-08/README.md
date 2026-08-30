# 小重山 2026 设计文档

当前设计已经形成两套稳定基线：

```text
公开站
→ Content / Reading System

管理后台
→ Productivity Admin System
```

## 公开站

1. `01_公开站设计规范.md`
2. `02_页面与组件设计说明.md`
3. `03_文章内容系统与Block规范.md`

## 管理后台

4. `04_管理后台设计规范.md`
5. `05_管理后台Pattern与页面规范.md`

---

## 设计资产关系

```text
HTML Prototype
= 视觉参考

Design Spec
= 设计原则与不可违反的约束

Pattern Spec
= 重复业务问题的标准解决方案

Production Vue
= 最终实现
```

---

## 开发建议阅读顺序

### 重构公开站

```text
01
↓
02
↓
03
↓
相关 HTML Prototype
```

### 重构后台

```text
04
↓
05
↓
2026 Admin Prototype
```

---

## 当前阶段

设计探索阶段已经结束。

后续原则：

> 不再自由探索新的公开站或后台视觉方向。

下一阶段应进入：

```text
现有代码审计
↓
组件映射
↓
阶段拆分
↓
Vue 实现
↓
原型对照验收
```
