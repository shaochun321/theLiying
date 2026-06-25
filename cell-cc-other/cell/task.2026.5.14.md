# v37.4.95: Xin 闭环 + 因果链墓志铭

## 第一刀: node_necropolis + DNA
- [x] 新增 pipe_{ns}_node_necropolis 表 (含 dna_snapshot_json) ✅
- [x] run_hebbian_ab() 中对 dead node 提取 top-3 edges → DNA ✅
- [x] 写入 necropolis 记录 ✅

## Xin 生命周期闭环
- [x] IsolatedPipeline.run_xin_lifecycle_closure() ✅
- [x] 通过 self._xi_ids 精确隔离（非 LIKE 前缀） ✅
- [x] orchestrator Phase 5 调用 ✅
- [x] fluo: 3 discard + 1 recycle + 2 demote + 2 promote = 8
- [x] phc:  3 discard + 1 recycle + 2 demote + 2 promote = 8
- [x] usgs: 2 discard + 1 recycle + 1 demote + 1 promote = 5

## 验证
- [x] 多管线测试 44/44 ALL PASS ✅
- [x] AB 回归 46/46 ALL PASS ✅
- [x] 集成回归 8/8 ALL PASS ✅
- **总计: 98/98 ALL PASS**
