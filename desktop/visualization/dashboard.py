"""自动生成的 Dashboard 仪表盘。

根据设备注册的通道（Channel.visual 字段）自动创建对应组件：

    text  → TextWidget    普通数值（默认）
    gauge → GaugeWidget   仪表盘
    chart → ChartWidget   实时曲线（占满整行，需要横向空间）

数据与界面分离：设备只需在协议中描述自己（visual 字段），
PC 端无需为具体设备写任何代码，组件随通道注册自动生成。
"""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QFrame,
    QGridLayout,
    QLabel,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from desktop.visualization.widgets.chart_widget import ChartWidget
from desktop.visualization.widgets.gauge_widget import GaugeWidget
from desktop.visualization.widgets.text_widget import TextWidget

CARDS_PER_ROW = 2

CARD_STYLE = (
    "QFrame { background-color: #232428; border: 1px solid #2b2d30;"
    " border-radius: 6px; }"
)
TITLE_STYLE = "QLabel { color: #a0a0a0; font-size: 11px; }"
HINT_STYLE = (
    "QLabel { color: #808080; font-size: 14px; background: transparent; }"
)


def create_widget(channel):
    """按通道的 visual 字段创建对应组件，未知类型回退为文本。"""
    if channel.visual == "gauge":
        return GaugeWidget(channel)
    if channel.visual == "chart":
        return ChartWidget(channel)
    return TextWidget(channel)


class DashboardWidget(QWidget):
    """仪表盘面板：网格布局，通道注册时动态添加卡片。"""

    def __init__(self):
        super().__init__()
        self._widgets = {}   # ch_id -> BaseWidget
        self._row = 0
        self._col = 0

        self._hint = QLabel("尚未连接设备\n\n打开串口并连接 MCU 后，"
                            "这里会自动生成仪表盘")
        self._hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._hint.setStyleSheet(HINT_STYLE)

        self._grid = QGridLayout()
        self._grid.setSpacing(8)

        container = QWidget()
        container.setLayout(self._grid)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(container)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("QScrollArea { background-color: #1e1f22; }"
                             "QWidget { background-color: #1e1f22; }")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._hint, stretch=1)
        layout.addWidget(scroll, stretch=1)
        self._scroll = scroll

    # ====== 对外接口 ======

    def add_channel(self, channel):
        """通道注册 → 创建组件卡片并加入网格。"""
        if channel.id in self._widgets:
            return
        widget = create_widget(channel)
        card = self._build_card(channel, widget)
        self._place_card(card, channel.visual)
        self._widgets[channel.id] = widget
        self._hint.hide()
        self._scroll.show()

    def update_value(self, ch_id, value):
        """通道值更新 → 路由到对应组件。"""
        widget = self._widgets.get(ch_id)
        if widget is not None:
            widget.update_value(value)

    def reset(self):
        """清空全部组件（串口关闭 / 设备断开时）。"""
        while self._grid.count():
            item = self._grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._widgets.clear()
        self._row = 0
        self._col = 0
        self._scroll.hide()
        self._hint.show()

    def count(self):
        """当前组件数量（测试用）。"""
        return len(self._widgets)

    # ====== 内部 ======

    def _build_card(self, channel, widget):
        title_text = channel.name
        if channel.unit:
            title_text += " (%s)" % channel.unit
        title = QLabel(title_text)
        title.setStyleSheet(TITLE_STYLE)

        card = QFrame()
        card.setStyleSheet(CARD_STYLE)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(10, 8, 10, 10)
        layout.setSpacing(6)
        layout.addWidget(title)
        layout.addWidget(widget, stretch=1)
        return card

    def _place_card(self, card, visual):
        """图表占满整行，其余组件按 2 列排布。

        注意：图表必须放在新的整行（先关闭当前未满的行），
        否则会覆盖该行已放置的卡片。
        """
        if visual == "chart":
            if self._col > 0:  # 关闭未满的当前行
                self._row += 1
                self._col = 0
            self._grid.addWidget(card, self._row, 0, 1, CARDS_PER_ROW)
            self._row += 1
        else:
            self._grid.addWidget(card, self._row, self._col, 1, 1)
            self._col += 1
            if self._col >= CARDS_PER_ROW:
                self._col = 0
                self._row += 1
