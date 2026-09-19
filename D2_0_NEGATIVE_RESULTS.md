# D2_0_NEGATIVE_RESULTS — 负结果与方法登记

日期：2026-09-20　轮次：D2-0/P2-B

## N-1（结构预判证伪，有信息量）：镜像对称在 parent 层破缺

预注册预测"对称求和细胞下 C3_m 与 C4_m 逐位相同"被证伪
（RMSE=2.15e-2）。根因：site28 与 site31 的 G0 链换能潜伏期相差 8 子步
（521 vs 529，突触扰动个体差异），occurrence 窗非镜像。**教训：'同类型
生成元'不等于'全同生成元'——parent 个体性会进入关系动力学**；关系候选
的 C3/C4 差异必须归因 parent 个体性，不得包装成 order 检测。

## N-2（自然化候选否决）：N3 不通过 dt 稳健预注册判据

A_i=∫a dt 的 2× 抽稀重算相对差 4.06e-2 > 预注册 1% 阈——collector
尖峰级结构使积分对采样分辨率敏感。N3=INSUFFICIENT（Q6 区分度本身达标
spread=0.249——否决仅因 Q7）。未来若需活动剂量类自然化，候选方向是
对尖峰结构先物理平滑（如经 RC 读出层）再积分，非提高采样密度硬凑。

## N-3（登记事实）：亚阈值剂量/短脉冲的结构性无发生

u=0.02（cal_C2_sim2/hold_dose1）与 300 子步短脉冲（hold_dur1）不触发
parent occurrence ⇒ 对应 hold 项 STRUCTURALLY_NO_RELATION（反馈 §二十
明许，非失败）。dose 在 occurrence 层的第一表达是触发/不触发二分。

## N-4（预期兑现的阴性）：换能神经元态不承载关系记忆

hidden dynamics tier0（仅移植两个 RelationInputNeuron 状态）不消除未来
分叉——换能 trace τ≈0.1s 在 t0（窗后 ~0.8s）已衰竭。关系记忆的唯一
载体=RelationCell 膜态（tier1 精确等化）。与 G0-R1 N-4（相位载体在膜
电荷不在 trace）同族结论：**本项目的跨时距记忆一致地由膜电容承载，
trace 层是短程量**。

## N-5（对照预期兑现）：NC1 有信号无过程

瞬时积可在 C2/C5 上给出非零"关系值"，但无状态/无历史/无耗散——
RELATION_SIGNAL=YES 且 RELATION_PROCESS=NO 同时成立，实证"计算出关系值
本身不等于产生了关系过程"（方案 §15 预期）。
