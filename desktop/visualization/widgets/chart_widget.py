"""ChartWidget：实时曲线（QPainter 自绘，无第三方依赖）。

滚动窗口最近 MAX_POINTS 个采样点，Y 轴随数据自适应（带 10% 边距）。
X 轴按采样序号推进——设备以固定周期上报时即为时间轴。
"""

from collections import deque

from PyQt6.QtCore import QRectF, Qt
from PyQt6.QtGui import QColor, QFont, QPainter, QPen
from PyQt6.QtWidgets import QWidget

from desktop.visualization.base import BaseWidget, fmt_value

MAX_POINTS = 300      # 曲线窗口：300 个采样点
HORIZONTAL_GRIDS = 4  # 横向网格数
VERTICAL_GRIDS = 4    # 纵向网格数

GRID_COLOR = QColor("#2b2d30")
LABEL_COLOR = QColor("#808080")
LINE_COLOR = QColor("#4aa3f0")
TEXT_COLOR = QColor("#c8c8c8")

MARGIN_LEFT = 44
MARGIN_RIGHT = 44
MARGIN_TOP = 20
MARGIN_BOTTOM = 20


class ChartWidget(BaseWidget):
    def __init__(self, channel):
        super().__init__(channel)
        self._points = deque(maxlen=MAX_POINTS)  # [(sample_index, value)]
        self._count = 0
        self.setMinimumHeight(180)

    def update_value(self, value):
        if isinstance(value, str):
            return  # 字符串无法画曲线
        try:
            v = float(self.channel.scaled(value))
        except (TypeError, ValueError):
            return
        self._points.append((self._count, v))
        self._count += 1
        self.update()

    def reset(self):
        self._points.clear()
        self._count = 0
        self.update()

    # ====== 绘制 ======

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        if not self._points:
            self._draw_placeholder(painter)
            return

        plot = QRectF(self.rect()).adjusted(MARGIN_LEFT, MARGIN_TOP,
                                            -MARGIN_RIGHT, -MARGIN_BOTTOM)
        y_lo, y_hi = self._y_range()
        x_lo = self._points[0][0]
        x_hi = self._points[-1][0]
        if x_hi <= x_lo:
            x_hi = x_lo + 1

        self._draw_grid(painter, plot, y_lo, y_hi, x_lo, x_hi)
        self._draw_line(painter, plot, y_lo, y_hi, x_lo, x_hi)

        # 最新值（右上角）
        latest = self._points[-1][1]
        text = fmt_value(latest)
        if self.channel.unit:
            text += " " + self.channel.unit
        painter.setPen(QPen(TEXT_COLOR))
        painter.setFont(QFont("Consolas", 10))
        painter.drawText(QRectF(MARGIN_LEFT, 2, self.width() - MARGIN_LEFT - 4, 16),
                         Qt.AlignmentFlag.AlignRight, text)

    def _draw_placeholder(self, painter):
        painter.setPen(QPen(LABEL_COLOR))
        painter.setFont(QFont("Consolas", 11))
        painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "等待数据…")

    def _y_range(self):
        lo = min(p[1] for p in self._points)
        hi = max(p[1] for p in self._points)
        if hi - lo < 1e-9:
            lo, hi = lo - 1.0, hi + 1.0
        pad = (hi - lo) * 0.1
        return lo - pad, hi + pad

    def _draw_grid(self, painter, plot, y_lo, y_hi, x_lo, x_hi):
        painter.setFont(QFont("Consolas", 8))
        painter.setPen(QPen(GRID_COLOR, 1))

        for i in range(HORIZONTAL_GRIDS + 1):
            frac = i / HORIZONTAL_GRIDS
            y = plot.top() + plot.height() * frac
            painter.drawLine(int(plot.left()), int(y),
                             int(plot.right()), int(y))
            val = y_hi - (y_hi - y_lo) * frac
            painter.setPen(QPen(LABEL_COLOR))
            painter.drawText(QRectF(2, int(y) - 7, MARGIN_LEFT - 6, 14),
                             Qt.AlignmentFlag.AlignRight, "%.3g" % val)
            painter.setPen(QPen(GRID_COLOR, 1))

        for i in range(VERTICAL_GRIDS + 1):
            frac = i / VERTICAL_GRIDS
            x = plot.left() + plot.width() * frac
            painter.drawLine(int(x), int(plot.top()),
                             int(x), int(plot.bottom()))
            idx = x_lo + (x_hi - x_lo) * frac
            painter.setPen(QPen(LABEL_COLOR))
            painter.drawText(QRectF(int(x) - 20, int(plot.bottom()) + 2,
                                    40, 14),
                             Qt.AlignmentFlag.AlignCenter, str(int(idx)))
            painter.setPen(QPen(GRID_COLOR, 1))

    def _draw_line(self, painter, plot, y_lo, y_hi, x_lo, x_hi):
        painter.setPen(QPen(LINE_COLOR, 2))
        path = []
        for idx, val in self._points:
            x = plot.left() + plot.width() * (idx - x_lo) / (x_hi - x_lo)
            y = plot.top() + plot.height() * (y_hi - val) / (y_hi - y_lo)
            path.append((x, y))
        for (x0, y0), (x1, y1) in zip(path, path[1:]):
            painter.drawLine(int(x0), int(y0), int(x1), int(y1))
