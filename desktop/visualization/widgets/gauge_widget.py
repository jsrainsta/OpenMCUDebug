"""GaugeWidget：圆弧仪表盘（QPainter 自绘，无第三方依赖）。

适合电压、电量、百分比等标量数据。量程自适应：初始为 0~100，
收到的值超出范围时自动扩展，始终覆盖历史数据。
"""

import math

from PyQt6.QtCore import Qt, QRectF
from PyQt6.QtGui import QColor, QFont, QPainter, QPen
from PyQt6.QtWidgets import QWidget

from desktop.visualization.base import BaseWidget, fmt_value

# 配色（与界面深色主题一致）
TRACK_COLOR = QColor("#2b2d30")    # 底弧
VALUE_COLOR = QColor("#3dce7a")    # 数值弧
LABEL_COLOR = QColor("#808080")    # 刻度文字
TEXT_COLOR = QColor("#e0e0e0")     # 数值文字

START_ANGLE = 135          # 起始角（度），左下
SWEEP_ANGLE = 270          # 弧长（度）
PEN_WIDTH = 8              # 弧线宽度


class GaugeWidget(BaseWidget):
    def __init__(self, channel):
        super().__init__(channel)
        self._lo = 0.0            # 量程下限（自适应扩展）
        self._hi = 100.0          # 量程上限
        self._value = None
        self.setMinimumHeight(150)

    def update_value(self, value):
        if isinstance(value, str):
            return  # 字符串无法画仪表
        try:
            v = float(value)
        except (TypeError, ValueError):
            return
        self._value = v
        if v < self._lo:
            self._lo = v
        if v > self._hi:
            self._hi = v
        self.update()

    # ====== 绘制 ======

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = QRectF(self.rect()).adjusted(14, 14, -14, -14)
        center = rect.center()
        radius = min(rect.width(), rect.height()) / 2

        # 底弧
        self._draw_arc(painter, center, radius, 0.0, 1.0, TRACK_COLOR)

        # 数值弧
        if self._value is not None:
            frac = (self._value - self._lo) / (self._hi - self._lo)
            frac = max(0.0, min(1.0, frac))
            self._draw_arc(painter, center, radius, 0.0, frac, VALUE_COLOR)

        self._draw_ticks(painter, center, radius)
        self._draw_value_text(painter, center, radius)

    def _draw_arc(self, painter, center, radius, frac_from, frac_to, color):
        painter.setPen(QPen(color, PEN_WIDTH))
        rect = QRectF(center.x() - radius, center.y() - radius,
                      2 * radius, 2 * radius)
        span = int(SWEEP_ANGLE * (frac_to - frac_from) * 16)
        start = int((START_ANGLE + SWEEP_ANGLE * frac_from) * 16)
        painter.drawArc(rect, start, span)

    def _draw_ticks(self, painter, center, radius):
        """绘制量程上限 / 中点 / 下限标签。"""
        painter.setPen(QPen(LABEL_COLOR))
        painter.setFont(QFont("Consolas", 9))
        label_r = radius + PEN_WIDTH + 12
        for frac, text in ((0.0, fmt_value(self._lo)),
                           (0.5, fmt_value((self._lo + self._hi) / 2)),
                           (1.0, fmt_value(self._hi))):
            angle = math.radians(START_ANGLE + SWEEP_ANGLE * frac)
            x = center.x() + label_r * math.cos(angle)
            y = center.y() - label_r * math.sin(angle)
            painter.drawText(QRectF(x - 30, y - 8, 60, 16),
                             Qt.AlignmentFlag.AlignCenter, text)

    def _draw_value_text(self, painter, center, radius):
        """绘制中心数值 + 单位。"""
        if self._value is None:
            return
        text = fmt_value(self._value)
        if self.channel.unit:
            text += " " + self.channel.unit

        painter.setPen(QPen(TEXT_COLOR))
        painter.setFont(QFont("Consolas", 20, QFont.Weight.Bold))
        painter.drawText(QRectF(center.x() - radius + 10, center.y() - 30,
                                2 * radius - 20, 32),
                         Qt.AlignmentFlag.AlignCenter, text)
