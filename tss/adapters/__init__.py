"""tss.adapters — typed 端口与 D2 消费接口层（G0-R1 起）。

TYPE:INFRA。放置侧依据 G0-R1 评判 R-1 裁定（用户批准 2026-09-19）：
adapter 服务 G0（tss 侧消费者），放 tss/，只允许 import nexus_v1
（单向依赖铁律），nexus_v1 不得反向 import 本包。
"""
from .typed_ports import (  # noqa: F401
    DT_EXT, G_CANON, LIVE_CAUSAL_POLICY, REFERENCE_RECONSTRUCTION_POLICY,
    S_CANON, UdotTSample, UTSample, Y_REF, amplitude_port_stub,
    rate_port_series, u_dot_t, u_t)
