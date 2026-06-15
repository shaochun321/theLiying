# Phase 1: 介质物理系统实施

- `[x]` **Step 1**: 创建 `medium_system.py` — MediumParticle + MediumLattice3D
- `[x]` **Step 2**: 实现波动传播 (acoustic) + 扩散传播 (thermal)
- `[x]` **Step 3**: 实现源注入 + 场读取 + 阻抗匹配界面
- `[x]` **Step 4**: 集成到 PracticeEngine
- `[x]` **Step 5**: 单元测试 — 波速/穿透深度/透射系数/能量稳定性
- `[x]` **Step 6**: 系统测试 — DERC + 偏好排序验证
  - `[x]` 基本偏好排序 (N=10): aco > the > lum ✅
  - `[x]` DERC 扫描 (N=20): 阶梯效应 — n≤1 平坦, n>1 急降
  - `[x]` 拉丁方 (N=20): 4/6 条件 n=1 rank #1
  - `[x]` n 信息修复: injection_scale = 1/spacing^(n-1)
