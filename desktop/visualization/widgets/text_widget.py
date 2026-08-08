"""TextWidget：普通数值显示。

适用于不需要仪表或曲线的通道（如开关状态、传感器原始值）。
"""

from PyQt6.QtWidgets import QLabel, QVBoxLayout

from desktop.visualization.base import BaseWidget, fmt_value

VALUE_STYLE = (
    "QLabel { color: #e0e0e0; font-size: 22px; font-weight: bold;"
    " font-family: Consolas, 'Courier New'; }"
)


class TextWidget(BaseWidget):
    def __init__(self, channel):
        super().__init__(channel)
        self._value_label = QLabel("—")
        self._value_label.setStyleSheet(VALUE_STYLE)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.addWidget(self._value_label)
        layout.addStretch(1)

    def update_value(self, value):
        if value is None:
            return
        text = fmt_value(value)
        if self.channel.unit:
            text += " " + self.channel.unit
        self._value_label.setText(text)
