"""
T-065：物理驱逐实验（热源瞬移）

目的：验证体在填充饱和（fill=1.0）后，当热源瞬移至对侧时，
      体是否能自动寻找并到达新热源（涌现行为测试）。

实验流程：
  Phase 1 (0~50k):  正常运行，等待体填充饱和 + 第一次 STDP 学习
  Phase 2 (50k):    热源瞬移：src_pos [70,50,25] → [10,50,25]（体当前在热源旁）
  Phase 3 (50k~100k): 观察体是否能从旧源位置移动到新源

判定标准：
  J1: Phase1 末填充率 > 0.5（体找到了热源并有效填充）
  J2: 瞬移后 30k 步内体进入新热源（dist_to_new < 30）
  J3: 体在 Phase3 期间最小距离新热源 < 30（成功接近）
  J4: fill 在瞬移后 10k 步内有下降（开始消耗，表明脱离旧源）

步数：100k（两个50k区段）
"""
import sys
sys.path.insert(0, '.')

from nexus_v1.circuit.variant_adapter import VariantCircuit
from nexus_v1.components.world import HeatSource, Body, World

DT = 1.0

def main():
    print("="*68)
    print("  T-065: 物理驱逐实验（热源瞬移）")
    print("  判定: J1 Phase1填充 | J2 30k内接近新源 | J3 最近距 | J4 fill下降")
    print("="*68)

    ORIG_POS = [70.0, 50.0, 25.0]
    NEW_POS  = [10.0, 50.0, 25.0]   # 瞬移目标（原 body 出发点）

    src = HeatSource(position=ORIG_POS[:], energy=1_000_000.0,
                     temperature=5.0, radius=30.0)
    src._drift = [0.0, 0.0, 0.0]
    body = Body(position=[10.0, 50.0, 25.0])   # body 从旧源对侧出发
    world = World(heat_sources=[src], body=body)
    world.MIN_ALIVE = 0
    world.REGEN_PROB = 0.0

    c = VariantCircuit()
    c.world = world

    TELEPORT_STEP = 50000
    TOTAL_STEPS   = 100000
    SAMPLE        = 2000

    fill_phase1_end = 0.0
    phase3_dist_to_new  = []
    fill_at_teleport    = 0.0
    fill_phase3_min     = 1.0
    first_enter_new_src = None  # step when body first enters new source

    print(f"\n  {'step':>7} | {'phase':>7} | {'dist_orig':>9} | {'dist_new':>8} | {'fill':>6} | {'omega':>8} | {'note':>12}")
    print("  " + "-" * 75)

    for step in range(1, TOTAL_STEPS + 1):
        # Phase 2: 热源瞬移
        if step == TELEPORT_STEP:
            c.world.heat_sources[0].position = NEW_POS[:]
            fill_at_teleport = c.energy_store.fill_fraction if hasattr(c, 'energy_store') else 0.0
            print(f"\n  *** 步 {step}: 热源瞬移 {ORIG_POS} → {NEW_POS} ***")
            print(f"  *** 瞬移时 fill = {fill_at_teleport:.4f} ***\n")

        c.step({}, DT)

        pos = c.world.body.position
        src_pos = c.world.heat_sources[0].position
        dist_orig = ((pos[0] - ORIG_POS[0])**2 + (pos[1] - ORIG_POS[1])**2) ** 0.5
        dist_new  = ((pos[0] - src_pos[0])**2 + (pos[1] - src_pos[1])**2) ** 0.5
        fill = c.energy_store.fill_fraction if hasattr(c, 'energy_store') else 0.0
        omega = c.world.body.angular_velocity

        if step == TELEPORT_STEP:
            fill_phase1_end = fill

        if step > TELEPORT_STEP:
            phase3_dist_to_new.append(dist_new)
            if dist_new < 30.0 and first_enter_new_src is None:
                first_enter_new_src = step
            fill_phase3_min = min(fill_phase3_min, fill)

        if step % SAMPLE == 0:
            phase = "Phase1" if step <= TELEPORT_STEP else "Phase3"
            note  = "AT_SRC" if dist_new < 30 else ("->" if step > TELEPORT_STEP else "")
            print(f"  {step:>7} | {phase:>7} | {dist_orig:>9.1f} | {dist_new:>8.1f} | {fill:>6.3f} | {omega:>8.5f} | {note:>12}")

    # 判定
    dist_to_new_min = min(phase3_dist_to_new) if phase3_dist_to_new else 999.0
    steps_to_find = (first_enter_new_src - TELEPORT_STEP) if first_enter_new_src else None

    j1 = fill_phase1_end > 0.5
    j2 = first_enter_new_src is not None and (first_enter_new_src - TELEPORT_STEP) <= 30000
    j3 = dist_to_new_min < 30.0
    j4 = fill_phase3_min < fill_at_teleport - 0.05  # fill 至少下降 5%

    print(f"\n  ── 结果统计 ──")
    print(f"  Phase1末 fill:        {fill_phase1_end:.4f}")
    print(f"  瞬移时 fill:          {fill_at_teleport:.4f}")
    print(f"  Phase3最近新源距:    {dist_to_new_min:.1f}")
    print(f"  Phase3最低fill:      {fill_phase3_min:.4f}")
    print(f"  首次进入新源（步）:  {first_enter_new_src if first_enter_new_src else 'NEVER'}")
    print(f"  找到新源耗时:        {steps_to_find if steps_to_find else 'N/A'} 步")
    print()

    print(f"  J1  Phase1末 fill>0.5       {fill_phase1_end:.4f}  → {'PASS ✅' if j1 else 'FAIL ❌'}")
    print(f"  J2  30k内进入新源           {'PASS ✅' if j2 else 'FAIL ❌' }  （{steps_to_find if steps_to_find else 'NEVER'} 步）")
    print(f"  J3  最近距新源<30           {dist_to_new_min:.1f}  → {'PASS ✅' if j3 else 'FAIL ❌'}")
    print(f"  J4  fill下降>5%             {fill_at_teleport:.4f}→{fill_phase3_min:.4f}  → {'PASS ✅' if j4 else 'FAIL ❌'}")

    passed = sum([j1, j2, j3, j4])
    print(f"\n  总计: {passed}/4 PASS")
    print("="*68)


if __name__ == '__main__':
    main()
