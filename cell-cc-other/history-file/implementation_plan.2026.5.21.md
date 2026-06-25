# 阶段 0 + 阶段 2a 实施计划

## 发现: 项目已有前庭系统

[vestibular_system.py](file:///D:/cell-cc/Morphosphere_v37_0_native_runtime_prototype_flat_complete/morphosphere_v2pp/engines/vestibular_system.py) 已存在，是一个 6 轴物理 IMU（3 半规管 + 3 耳石器官）。

```
已有的前庭系统:
  物理层 → 从粒子数据计算 angular velocity + linear acceleration
  输出: 6 个浮点通道 (vest_canal_yaw/pitch/roll, vest_oto_x/y/z)

缺失的:
  信息层 → 从 HebbianCircuit 环流中固化的运动状态参考模式
  这是 VestibularStore 要做的事
```

两层的关系:
```
VestibularSystem (已有) = 物理传感器, 输出原始信号
VestibularStore  (新建) = 信息层存储, 存固化的环流模式作为坐标系
```

---

## 阶段 0: CircuitObserver (外部观测模块)

> [!IMPORTANT]
> 纯外部模块，不修改 HebbianCircuit 任何代码。只读取，不写入。

### [NEW] [rlis_observer.py](file:///D:/cell-cc/Morphosphere_v37_0_native_runtime_prototype_flat_complete/morphosphere_v2pp/engines/rlis_observer.py)

**职责**: 每 tick 读取 HebbianCircuit 状态，计算 ρ 测度，追踪 Xin 守恒。

```python
class CircuitObserver:
    """RLIS 外部观测器 — 读取主线状态，不反写。"""
    
    def observe(self, circuit: HebbianCircuit) -> TickSnapshot:
        """每 tick 调用，生成快照。"""
    
    def compute_rho(self, snapshot: TickSnapshot) -> RhoMeasure:
        """从环流数据计算 ρ = (p_c, p_b, r_c, r_b, m_b, x, u)。"""
    
    def track_xin_conservation(self, prev: TickSnapshot, curr: TickSnapshot) -> XinFlow:
        """对比两个 tick 的 xin_tension，记录流向。"""
    
    @property
    def ledger(self) -> List[LedgerEntry]:
        """返回完整记录。"""
```

**数据结构**:

```python
@dataclass
class TickSnapshot:
    tick: int
    p_circulation: Optional[List[str]]     # P 路径 bundle IDs
    r_circulation: Optional[List[str]]     # R 路径 bundle IDs  
    circulation_measure: float              # 总环流量
    all_cycle_measures: List[Dict]          # 所有环路的流量
    xin_tensions: Dict[str, float]          # 每个 bundle 的 tension
    activated_fruits: List[Dict]            # 本 tick 激活的果实
    neuron_activations: Dict[str, float]    # 所有神经元的 activation
    temperature: float
    free_energy: float

@dataclass 
class RhoMeasure:
    """ρ = 7 分量归一化测度, sum = 1。"""
    p_core: float      # P 路径中稳定流量占比
    p_band: float      # P 路径中新增/边沿流量占比
    r_core: float      # R 路径中稳定流量占比
    r_band: float      # R 路径中边沿流量占比
    masking: float      # P/R 转换中过渡流量占比
    xin: float          # 未被解释的残余占比
    unresolved: float   # 完全未参与环流的占比

@dataclass
class XinFlow:
    """Xin 守恒记录: 每份 tension 的来源和去向。"""
    tick: int
    sources: Dict[str, float]        # bundle_id → 新增 tension
    absorbed_by_p: Dict[str, float]  # bundle_id → 被 P 吸收的 tension
    absorbed_by_r: Dict[str, float]  # bundle_id → 被 R 消解的 tension
    dissipated: Dict[str, float]     # bundle_id → 衰减消散的 tension
    fruit_activated: Dict[str, float] # bundle_id → 果实激活消耗的 tension
    net_change: float                 # 总 Xin 变化
```

---

## 阶段 2a: VestibularStore (参考模式存储)

> [!IMPORTANT]
> 纯新增模块。存储固化的环流模式，为后续比对提供基础。

### [NEW] [vestibular_store.py](file:///D:/cell-cc/Morphosphere_v37_0_native_runtime_prototype_flat_complete/morphosphere_v2pp/engines/vestibular_store.py)

**职责**: 存储已固化的环流模式作为运动状态参考。

```python
class VestibularStore:
    """固化的运动状态存储 — 系统的坐标系。"""
    
    def store_pattern(self, pattern: SolidifiedPattern) -> str:
        """存入一个通过验证的环流模式。返回 pattern_id。"""
    
    def get_all_patterns(self) -> List[SolidifiedPattern]:
        """返回所有已固化的模式。"""
    
    def compare_snapshot(self, snapshot: TickSnapshot) -> List[PatternDistance]:
        """将当前快照与所有固化模式做结构性比对。"""
    
    def get_nearest_pattern(self, snapshot: TickSnapshot) -> Optional[Tuple[str, float]]:
        """返回最近的固化模式 ID 和距离。"""
```

**数据结构**:

```python
@dataclass
class CirculationBaseline:
    """环流的 activation 时序基线 (历史切片)。"""
    neuron_ids: List[str]                    # 参与的神经元
    activation_sequence: List[Dict[str, float]]  # 时序: [{nid: act, ...}, ...]
    mean_activations: Dict[str, float]       # 每个神经元的均值
    phase_order: List[str]                   # 峰值顺序

@dataclass
class SolidifiedPattern:
    """一个固化的运动状态参考模式。"""
    pattern_id: str
    
    # 结构
    member_neuron_ids: List[str]            # 参与的元单元
    bundle_path: List[str]                  # 环流路径 (bundle IDs)
    baseline: CirculationBaseline           # activation 时序基线
    
    # 健康分数 (来自前神经的 4 分数模式)
    continuity_score: float                 # 空间连续性
    conservation_score: float               # 能量守恒
    phase_coherence_score: float            # 相位一致性
    
    # 固化元数据
    solidified_at_tick: int                 # 固化时间
    validation_count: int                   # 通过验证的次数
    masking_stability: float                # 屏蔽验证稳定性
    
    # 统计
    match_count: int = 0                    # 被匹配为最近模式的次数
    last_matched_tick: int = 0              # 最后一次匹配时间

@dataclass
class PatternDistance:
    """当前快照与一个固化模式的比对结果。"""
    pattern_id: str
    distance: float                         # 结构性距离 (XOR 等价)
    activation_diff: Dict[str, float]       # 每个神经元的基线偏差
    phase_alignment: float                  # 相位对齐度
```

**比对机制** (结构性比较 = XOR 等价):

```python
def _structural_compare(self, snapshot: TickSnapshot, 
                         pattern: SolidifiedPattern) -> PatternDistance:
    """结构性比对: 当前环流 vs 固化基线。
    
    不用数值减法。用的是:
    1. 哪些神经元在基线中活跃但现在不活跃? (XOR = 1)
    2. 哪些神经元在基线中不活跃但现在活跃? (XOR = 1)
    3. 相位顺序是否匹配?
    
    距离 = XOR 结果的信息量 (活跃状态不一致的比例)
    """
```

---

## 验证计划

### 自动测试
```bash
python -m pytest tests/test_rlis_observer.py -v
python -m pytest tests/test_vestibular_store.py -v
```

### 测试要点
1. CircuitObserver 读取后 HebbianCircuit 状态不变（只读验证）
2. ρ 的 7 分量之和 = 1.0（归一化验证）
3. Xin 守恒: sources - absorbed - dissipated = net_change（守恒验证）
4. VestibularStore 存入模式后可检索
5. 结构性比对: 相同模式 → distance ≈ 0; 不同模式 → distance > 0
