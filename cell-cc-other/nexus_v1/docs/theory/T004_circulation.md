# T004: 环流与时间尺度桥接

> 状态: ⚠️ 代码存在，未加入回归测试

## 环流 (Circulation)

信号在 Col → Bind → Motor → Col 间形成闭合环路。
环流强度 μ 度量信号的循环效率。

## 时间尺度桥接 (Temporal Coupler)

$$\tau_{couple} = C \times R_{leak}$$

三层结构：
- **Base layer**: RC 电容平滑 (fast→slow)
- **C-layer**: 自适应反馈 (MOSFET, 内源性大麻素)
- **B-layer**: 慢循环 (差分比较器, 突触缩放)

## 代码位置

| 文件 | 功能 |
|---|---|
| components/temporal_coupler.py | 三层 coupler 实现 |
| circuit/circulation.py | 环流测量 |

## 待验证

- 环流测量未加入回归测试
- Coupler B-layer 效果未独立量化
