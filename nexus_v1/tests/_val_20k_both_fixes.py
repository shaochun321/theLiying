import sys, math, time
sys.path.insert(0, 'd:\\cell-cc')
from nexus_v1.circuit.variant_adapter import VariantCircuit
c = VariantCircuit()

def tdist(a, b, size=100.0):
    t = 0.0
    for i in range(3):
        d = abs(a[i]-b[i])
        if d > size*0.5: d = size-d
        t += d*d
    return math.sqrt(t)

def in_zone(c):
    pos = c.world.body.position
    return any(tdist(pos,s.position)<s.radius for s in c.world.heat_sources if s.alive)

t0 = time.time()
fill_vals, in_zone_count, prev_level = [], 0, c.energy_store.level
pin_sum, pout_sum = 0.0, 0.0

init_fill = c.energy_store.fill_fraction
max_dep = c.energy_store.config.max_deposit_per_step
print(f"=== FIX-INITIAL-FILL+DEPOSIT-RATE validation (init={init_fill:.2f}, max_dep={max_dep}) ===")

for step in range(20000):
    c.step({}, 1.0)
    fill_vals.append(c.energy_store.fill_fraction)
    if in_zone(c):
        in_zone_count += 1
    cur = c.energy_store.level
    delta = cur - prev_level
    pin_sum += max(delta, 0)
    pout_sum += max(-delta, 0)
    prev_level = cur
    if (step+1) % 2000 == 0:
        fill = c.energy_store.fill_fraction
        da = c.dopamine.concentration
        agc = c.agc.gain
        sps = (step+1)/max(time.time()-t0, 0.01)
        zone_pct = in_zone_count/(step+1)*100
        print(f"step {step+1:6d}: fill={fill:.4f} DA={da:.5f} AGC={agc:.3f} zone={zone_pct:.1f}%  sps={sps:.0f}")

fill_min = min(fill_vals)
fill_max = max(fill_vals)
fill_final = fill_vals[-1]
fill_5k = fill_vals[4999]
slope = (fill_final - fill_5k) / 15000
p_net = (pin_sum - pout_sum) / 20000
elapsed = time.time()-t0

print("")
print(f"fill_min={fill_min:.4f}  fill_max={fill_max:.4f}  fill@20k={fill_final:.4f}")
print(f"P_net_mean={p_net:+.7f}/step")
c1 = "PASS" if fill_min > 0 else "FAIL"
c2 = "PASS" if fill_final > 0.30 else "FAIL"
c7 = "PASS" if slope > 0 else "FAIL"
print(f"C1 fill_min>0: {c1} (min={fill_min:.6f})")
print(f"C2 fill@end>0.30: {c2} (val={fill_final:.4f})")
print(f"C7 slope post-5k>0: {c7} (slope={slope:+.7f})")
print(f"Total time: {elapsed:.1f}s")
