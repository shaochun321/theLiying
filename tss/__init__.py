"""tss — TSS/基础生成元理论轨顶层包（时间/空间/尺度生成算子研究线）。

TYPE:INFRA（包组织层，无物理载体主张）

2026-09-06 自 nexus_v1/ 迁出（纯搬迁：零改名、零重构、零逻辑改动，
仅目录与 import 路径变化）。迁移记录与新旧路径映射见本目录 README.md。

依赖方向纪律（与迁移前一致）：
    tss/* → nexus_v1/*   允许（单向读取活体电路对象）
    nexus_v1/* → tss/*   禁止（organism 对本轨零感知）

子包：
    tss.generators — 基础生成元 𝒢/χ 闭合/自然化/转导映射
    tss.relations  — 发生边界/首次进入门/时间关系 R_prec/R1/R2
    tss.events     — 关系实例谱系绑定（D3 候选，未取得事件核资格）
"""
