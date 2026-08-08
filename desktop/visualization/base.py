"""可视化组件基类与数值格式化工具。

所有 Dashboard 组件都继承 BaseWidget，统一暴露 update_value / reset 接口，
Dashboard 只依赖这两个方法，不关心具体组件实现。
"""

from PyQt6.QtWidgets import QWidget


def fmt_value(value):
    """数值格式化。

    - int 直接显示（如 "1500"）
    - float 保留 6 位有效数字（与 MCU 端 %.6g 的发送格式一致）
    - 其它类型原样转字符串
    """
    if isinstance(value, float):
        return "%.6g" % value
    return str(value)


class BaseWidget(QWidget):
    """Dashboard 组件的统一接口。"""

    def __init__(self, channel):
        super().__init__()
        self.channel = channel

    def update_value(self, value):
        """收到通道新值（已解析为 int / float / str）。子类覆写。"""
        raise NotImplementedError

    def reset(self):
        """清空历史数据。子类按需覆写。"""
