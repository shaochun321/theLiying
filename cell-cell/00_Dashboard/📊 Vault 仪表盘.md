---
tags: [MOC, 导航, Dataview, 查询]
type: index
date: 2026-06-14
aliases: [dashboard, 仪表盘, 总览]
---

# 📊 Vault 仪表盘

> 点击下方查询页进入对应视图。所有 Dataview 查询自动更新。

- [[📋 按概念查询]] — 输入词条(Xin/影子层/环流/B06…)，找到所有相关文档
- [[📅 按时间线查询]] — 按日期查看 Plan → Build → Reflect
- [[🔴 按优先级查询]] — P0/P1/P2 按紧急程度筛选
- [[🏷️ 按类型查询]] — 按文档类型筛选

---

## 🏠 固定导航

- [[核心词条索引]] · [[理念架构图]] · [[概念演化链]]
- [[矛盾·遗留·生长点]] · [[Plan-Walkthrough-Analysis三角映射]]
- [[当前方向与缺口追踪]] · [[AI编程自足文档]]

---

## 快速 Dataview

### 所有 MOC 导航页
```dataview
TABLE date, concepts
FROM #MOC
SORT date DESC
```

### 按概念覆盖统计
```dataview
TABLE length(rows) as "文档数"
FROM ""
FLATTEN concepts
GROUP BY concepts
SORT rows.length DESC
```
