"""数据通道模型。

一个 Channel 对应用户固件中 Debug_Register_Channel 注册的一条数据通道。
"""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Channel:
    id: int
    name: str
    type: str          # "i16" / "u32" / "f32" / "str" 等
    unit: str
    visual: str = "text"  # 可视化方式: "text" / "gauge" / "chart"（Stage 3）
    value: Any = None  # 最新接收到的值
