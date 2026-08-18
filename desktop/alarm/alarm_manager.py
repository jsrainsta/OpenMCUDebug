"""阈值告警（Stage 6 / v0.6）。

PC 端本地功能：按通道设置 [min, max] 阈值（物理量，即换算后的值），
越限时通知 UI 变色并提示。不涉及协议——MCU 无需感知。

纯逻辑模块，不依赖 Qt，便于单元测试。
"""

from typing import Tuple


class AlarmManager:
    """通道阈值告警管理器。

    用法::

        alarms = AlarmManager()
        alarms.set_limit(0, 1100.0, 1900.0)          # 设置范围
        in_alarm, entered = alarms.check(0, 1500.0)  # (是否越限, 是否新进入)
        alarms.clear()                                # 断开连接时清空
    """

    def __init__(self):
        self._limits = {}   # ch_id -> (lo, hi)，None 表示不限
        self._state = {}    # ch_id -> bool 当前是否处于告警

    def set_limit(self, ch_id, lo, hi):
        """设置通道阈值范围；lo / hi 为 None 表示该侧不限，都为 None 时清除。"""
        if lo is None and hi is None:
            self._limits.pop(ch_id, None)
        else:
            self._limits[ch_id] = (lo, hi)
        self._state.pop(ch_id, None)

    def get_limit(self, ch_id):
        return self._limits.get(ch_id)

    def check(self, ch_id, value) -> Tuple[bool, bool]:
        """检查值是否越限。

        Returns:
            (in_alarm, entered)：
              in_alarm — 当前是否越限；
              entered  — 是否新进入告警（上一状态正常）。
            字符串值 / None 无法比较，返回 (False, False) 且不改变状态。
        """
        limit = self._limits.get(ch_id)
        if limit is None or value is None or isinstance(value, str):
            return False, False
        try:
            v = float(value)
        except (TypeError, ValueError):
            return False, False

        lo, hi = limit
        lo_ok = lo is None or v >= lo
        hi_ok = hi is None or v <= hi
        in_alarm = not (lo_ok and hi_ok)

        entered = in_alarm and not self._state.get(ch_id, False)
        self._state[ch_id] = in_alarm
        return in_alarm, entered

    def clear(self):
        """清空全部阈值与状态（串口断开 / 设备重置时调用）。"""
        self._limits.clear()
        self._state.clear()
