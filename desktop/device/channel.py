"""数据通道模型。

一个 Channel 对应用户固件中 Debug_Register_Channel 注册的一条数据通道。
"""

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class Channel:
    id: int
    name: str
    type: str          # "i16" / "u32" / "f32" / "str" 等
    unit: str
    visual: str = "text"  # 可视化方式: "text" / "gauge" / "chart"（Stage 3）
    value: Any = None  # 最新接收到的值（原始值，未换算）
    # Stage 6：物理量换算（可选，缺省 1/0/None 即不换算）
    scale: float = 1.0
    offset: float = 0.0
    minimum: Optional[float] = None   # 量程下限（gauge 优先使用）
    maximum: Optional[float] = None   # 量程上限

    def scaled(self, value):
        """原始值 → 物理量：value * scale + offset。

        字符串值（无法换算）原样返回；非法值原样返回。
        """
        if isinstance(value, str):
            return value
        try:
            return float(value) * self.scale + self.offset
        except (TypeError, ValueError):
            return value
