# G0R1_OCC_NEGATIVE_RESULTS — 负结果与方法勘误登记

日期：2026-09-19　轮次：G0-R1/OCC

## N-1（结构性，最重要）：S0+B1 桥配对无效

live 调度 S0（零阶保持）与 B1（逐子步差分）配对是**结构性错误**：ZOH 使
区间内 ΔY=0、全部外部变化集中在样本边界的单个子步 ⇒ 速率被放大
N_sub=1000×（实测 max|Ẏ|=995.0 T/s 脉冲伪影 vs B0 的 0.995 T/s），G0
链路被孤立单子步脉冲饿死（g_v1 探针 collector 峰=0.0）。与 G0-R0 结构
预期一致（"S1 下 B1 区间内=B0，仅样本边界不同"——B1 只有在 S1/S2 平滑
重建下有意义）。**裁定：live 因果桥 = S0+B0；B1 保留给 reference/replay
（S1/S2）语境。** 出处：r1_calibration.py 首轮运行（修正前）。

## N-2（方法）：5×5 阈值网格不鉴别

首轮 theta×rearm 25 组合全 LEGAL——网格未覆盖失败沿即宣称合法域=TSS-2b
"CG-0 资格不鉴别"教训重演。修正：扩至 theta_up∈{0.5,0.9,1.1}（Zener
顶棚方向）与 rearm∈{10000,25000,40000}（K8 脉冲间隔方向）后失败边界
双侧定位（theta∈(0.9,1.1)、rearm∈(10000,25000)）。

## N-3（方法）：合同 exit 检查初版过严

初版把 §7 的 exit 编码为"t_down ≥ 支撑衰减"，漏掉合同原文的第二合法
模式"**内部动力学退出**"（实测 cal_K1a：collector 对 onset 瞬态响应后
t_down=1.697s 时输入支撑仍在场）。修正=对齐合同原文，exit_mode 分类
登记（input_end / internal_dynamics）；原始测量数据未改动。

## N-4（否定发现，有信息量）：pre_trace 低维表示不承载相位

Hidden dynamics 干预 Z_low 臂（仅移植 hc+ensemble+collector 的
pre_trace×10）**不能**等化未来（latency 35 vs 92）——自持振荡的相位
载体在完整神经元状态（膜电容电荷等），不在 trace 层。未来若需要更低维
phase 表示，候选方向是膜电荷向量而非 trace 向量（登记，不在本轮深挖，
§14 停止规则生效）。

## N-5（登记事实）：dose 幅值维被 collector Zener 顶棚吸收

power 0.5/1.0/2.0 三档下 col_peak 均≈1.001、duration 均=139 步——幅值
差异被顶棚抹平，剂量信息保留在时序维（latency 748/558/443）与输入积分
维（Σ|u|）。与 W0-E/T0"顶棚塌缩"家族同源；occurrence 层的剂量表达=
时序编码，属登记事实（§10 不要求幅值维保真）。
