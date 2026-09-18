# G0R0_NEGATIVE_RESULTS — 负结果登记（§40，同等保存）

日期：2026-09-19

1. **T1-B C2 断言勘误**："generator dt=内部积分粒度非物理秒"是未经代码
   审计的合同断言，被行为实验推翻（E1-E3 全 PHYSICAL）——"合同文字不能
   替代代码证据"（外部 §14/§44）成为本项目新增纪律先例。
2. **旧 1:1 耦合物理不一致定量化**：剂量=细参考的 0.00101（≈1/1000）
   ——生成元在全部历史 WORLD_COUPLED 实验中以 1/1000 物理速率运行。
   冻结结果为 step 语义内部自洽，不重审；其"物理秒"解释一律作废。
3. **全向量多率收敛 FAIL（FIRST_RESULT）**：D4 原判据比=1.037——根因
   为 ensemble/collector 自持极限环相位失相干
   （G0_OSCILLATOR_PHASE_SENSITIVITY，先证=exp_P2A1b_3），对任何边界
   采样策略不可收敛；接口层（L1/HC）一阶收敛（比=0.101）。该发现对
   Occurrence Revalidation 的含义：**逐状态比较不是 G0 的合法验收面，
   事件级/统计级量才是**。
4. **B_BRIDGE_L1_SATURATION**：物理秒制速率下 u_B 峰 0.274 ≫ L1 钳位
   起点 0.05（33.3% 子步饱和）；B1@S1 与 B1@S2ref 被钳成逐位相同
   （饱和假象曾令比较失效）。g canonical 量级源于 step 制速率，
   revalidation 必须在物理秒制下重标（本轮 §20/§32 禁调，未动）。
5. **DELAY_STEP_COUPLING 实证**（隐性）：delay_steps=5 在 dt_G 两档下
   物理延迟 5.0/2.5 ms 漂移；G0 核心链 delay=0 未行使，DA 路径
   （100-500 步）受影响——G0-R1 修复清单。
6. **L1 pre_trace=DISCRETE_COUNTER**（τ 漂移比精确 0.500）——链内惰性
   （propagate 消费 activation），但作为组件级卫生债登记。
7. **occurrence（本轮记录非判定）**：多率 B 桥五场景各 1 次（对比旧
   耦合 smoke=0）——按 §34/§40 该差异不是本轮 PASS/FAIL 项，登记供
   revalidation。
8. **RC 在体测量二次返工**（透明登记）：首测驱动幅度触 HC trace 钳位
   （τ=inf 假象）——低幅驱动+长窗修正后 τ 五位不变。教训与 W1 相对
   梯度归一同族：观测量必须避开钳位与公因子污染。
