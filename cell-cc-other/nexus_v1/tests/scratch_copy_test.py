"""Test: does copy() of NeuronConfig share mutable fields?"""
from copy import copy
from dataclasses import dataclass, field
from typing import List

@dataclass
class ChannelConfig:
    name: str = "default"
    v_threshold: float = 0.3
    gm: float = 1.0

@dataclass 
class NeuronConfig:
    neuron_id: str = ""
    channels: List[ChannelConfig] = field(default_factory=list)
    theta_m: float = 0.0

# Test 1: shallow copy shares list
c1 = NeuronConfig(neuron_id="parent", channels=[ChannelConfig("ch1", 0.3, 1.0)])
c2 = copy(c1)
c2.neuron_id = "child"

print("=== Shallow copy(NeuronConfig) ===")
print(f"c1.channels is c2.channels: {c1.channels is c2.channels}")
print(f"c1.channels[0] is c2.channels[0]: {c1.channels[0] is c2.channels[0]}")

# Mutate c2's channel
c2.channels[0].v_threshold = 999.0
print(f"\nAfter c2.channels[0].v_threshold = 999:")
print(f"  c1.channels[0].v_threshold = {c1.channels[0].v_threshold}")
print(f"  c2.channels[0].v_threshold = {c2.channels[0].v_threshold}")
print(f"  CONTAMINATION: {c1.channels[0].v_threshold == 999.0}")

# Mutate c2 scalar
c2.theta_m = 42.0
print(f"\nAfter c2.theta_m = 42:")
print(f"  c1.theta_m = {c1.theta_m}")
print(f"  c2.theta_m = {c2.theta_m}")
print(f"  CONTAMINATION: {c1.theta_m == 42.0}")

# Test 2: BundleConfig with silent_snapshot dict
@dataclass
class BundleConfig:
    bundle_id: str = ""
    silent_snapshot: dict = field(default_factory=dict)
    xin_tension: float = 0.0

b1 = BundleConfig(bundle_id="parent_bundle", silent_snapshot={"w": 0.5})
b2 = copy(b1)
b2.bundle_id = "child_bundle"

print("\n=== Shallow copy(BundleConfig) ===")
print(f"b1.silent_snapshot is b2.silent_snapshot: {b1.silent_snapshot is b2.silent_snapshot}")
b2.silent_snapshot["test"] = True
print(f"After b2.silent_snapshot['test'] = True:")
print(f"  b1.silent_snapshot = {b1.silent_snapshot}")
print(f"  CONTAMINATION: {'test' in b1.silent_snapshot}")

# Test 3: xin_tension (scalar) is safe
b2.xin_tension = 99.0
print(f"\nScalar xin_tension: b1={b1.xin_tension}, b2={b2.xin_tension}")
print(f"  CONTAMINATION: {b1.xin_tension == 99.0}")
