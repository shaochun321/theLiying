# 剩余改进顺序执行

## A4: d_σ_t 系数敏感性分析
- [ ] 在 runner 中新增 sweep 阶段：对 c4 在 [0.5, 2.0] 做 5 点扫描
- [ ] 验证 V_Φ 随 c4 的单调性
- [ ] 输出 sensitivity CSV
- [ ] 新增验证检查

## B2: V_Φ 异常检测触发器
- [ ] Engine B 新增 v_phi_alerts 列表
- [ ] dead-node alert: V_Φ 连续 K tick 为零
- [ ] phase-transition alert: V_Φ > 10× 移动平均
- [ ] DB 表: v_phi_alert_log
- [ ] harness flush 方法
- [ ] runner 中调用并验证

## B3: 引擎文件拆分 (§17)
- [ ] 拆分 hebbian_ab_engine.py → 独立引擎文件
- [ ] 保持 import 兼容性
- [ ] 验证 51/51 不退步

## C1: v37.5 解锁
- [ ] 🔒 BLOCKED — 需要外部数据流扩展
