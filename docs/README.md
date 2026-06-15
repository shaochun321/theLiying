# Morphosphere 项目文档索引

## 文件夹结构

```
docs/
├── versions/
│   ├── v41.1_structural_coupling/       # CPG 相位门控
│   ├── v41.1_column_forward_model/      # Column 小脑前向模型
│   ├── v41.1_bcm_feedback_emergence/    # 异质介质 + BCM + 反馈涌现
│   ├── v41.2_shadow_delta_descriptor/   # 影子层分析 + 沉积理论
│   │   ├── README.md                    # Δ-descriptor 设计
│   │   └── deep_sediment_analysis.md    # 沉积网络现实参照分析
│   └── v41.3_sediment_layer/            # 沉积层实现
│
├── db_snapshots/
│   ├── v41.1_20260519_003420/           # v40_integrated.db
│   └── v41.3_20260519_014510/           # v40_integrated.db
│
└── README.md
```

## 版本历史

| 版本 | 日期 | 主要变更 | 降级变化 |
|------|------|---------|---------|
| v40 | 2026-05 | 传播延迟, 代谢能量池 | -2 |
| v41.0 | 2026-05 | 代谢闭环, 饥饿驱动 | 0 |
| v41.1 | 2026-05-18 | CPG门控, Column前向模型, 异质介质, BCM, 反馈涌现 | **-4** |
| v41.2 | 2026-05-19 | 影子压缩 (hand-label → system coords) | 0 |
| v41.3 | 2026-05-19 | **沉积层** — 真正的赫布超图深层记忆区域 | 0 |

## 约定

每个版本文件夹包含：
- `README.md` — 路线/理念/讨论/实施/测试
- (可选) 额外分析文件

DB 快照在每次重大版本变更后自动保存。
