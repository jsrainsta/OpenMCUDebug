"""Dashboard 仪表盘单元测试（离屏运行）。

覆盖 Stage 3 核心链路：
按 visual 字段创建组件 → 数据更新路由 → reset 清空。

运行方式（在项目根目录）::

    python -m tests.test_dashboard
"""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication

# PyQt6 要求先创建 QApplication 才能实例化任何 QWidget，否则直接崩溃
_app = QApplication.instance() or QApplication([])

from desktop.device.channel import Channel
from desktop.visualization.dashboard import DashboardWidget, create_widget
from desktop.visualization.widgets.chart_widget import ChartWidget
from desktop.visualization.widgets.gauge_widget import GaugeWidget
from desktop.visualization.widgets.text_widget import TextWidget


def test_create_widget_factory():
    assert isinstance(create_widget(Channel(0, "V", "f32", "V", visual="gauge")),
                      GaugeWidget)
    assert isinstance(create_widget(Channel(1, "Roll", "i16", "degree", visual="chart")),
                      ChartWidget)
    assert isinstance(create_widget(Channel(2, "S", "str", "", visual="text")),
                      TextWidget)
    assert isinstance(create_widget(Channel(3, "X", "i16", "", visual="hologram")),
                      TextWidget), "未知类型应回退文本"
    print("PASS: create_widget 工厂按 visual 创建组件")


def test_dashboard_lifecycle():
    dash = DashboardWidget()
    dash.show()

    assert dash.count() == 0
    assert dash._hint.isVisible(), "空仪表盘应显示提示"

    # 注册三种类型通道
    dash.add_channel(Channel(0, "Voltage", "f32", "V", visual="gauge"))
    dash.add_channel(Channel(1, "Roll", "i16", "degree", visual="chart"))
    dash.add_channel(Channel(2, "Status", "str", "", visual="text"))
    assert dash.count() == 3
    assert not dash._hint.isVisible(), "有组件后隐藏提示"
    assert isinstance(dash._widgets[0], GaugeWidget)
    assert isinstance(dash._widgets[1], ChartWidget)
    assert isinstance(dash._widgets[2], TextWidget)

    # 数据更新路由
    dash.update_value(0, 11.8)
    dash.update_value(1, -25.5)
    dash.update_value(2, "armed")
    _app.processEvents()

    assert dash._widgets[0]._value == 11.8
    assert len(dash._widgets[1]._points) == 1
    assert dash._widgets[1]._points[0][1] == -25.5
    assert dash._widgets[2]._value_label.text() == "armed"

    # 字符串不能进仪表/曲线
    dash.update_value(0, "not-a-number")
    assert dash._widgets[0]._value == 11.8, "非法值应被忽略"

    # reset 清空
    dash.reset()
    assert dash.count() == 0
    assert dash._hint.isVisible()
    print("PASS: Dashboard 生命周期（注册/更新/重置）")


def test_grid_no_overlap():
    """图表占整行时不应覆盖同行的其它卡片（回归测试）。"""
    dash = DashboardWidget()
    dash.add_channel(Channel(0, "Voltage", "f32", "V", visual="gauge"))
    dash.add_channel(Channel(1, "Roll", "i16", "degree", visual="chart"))
    dash.add_channel(Channel(2, "Pitch", "i16", "degree", visual="chart"))

    # 网格中实际存在的卡片数应等于注册的通道数（无卡片被覆盖移除）
    grid_cards = sum(1 for i in range(dash._grid.count())
                     if dash._grid.itemAt(i).widget())
    assert grid_cards == 3, "网格应有 3 张卡片，实际 %d" % grid_cards

    # 第 0 行应该是仪表卡片（chart 在下一行整行）
    first = dash._grid.itemAtPosition(0, 0)
    assert first is not None and first.widget() is not None
    print("PASS: 图表整行布局不覆盖其它卡片")


def test_dashboard_duplicate_channel():
    dash = DashboardWidget()
    dash.add_channel(Channel(0, "Voltage", "f32", "V", visual="gauge"))
    dash.add_channel(Channel(0, "Voltage", "f32", "V", visual="gauge"))
    assert dash.count() == 1, "重复注册同一通道应忽略"
    print("PASS: 重复通道注册忽略")


def test_dashboard_scale_display():
    """Stage 6：组件按 scale/offset 换算后显示，gauge 优先使用声明量程。"""
    dash = DashboardWidget()

    # 带换算的文本通道：16384 LSB → 1 g
    dash.add_channel(Channel(4, "Accel_X", "i16", "g", visual="text",
                             scale=1.0 / 16384.0, offset=0.0,
                             minimum=-2.0, maximum=2.0))
    dash.update_value(4, 16384)
    _app.processEvents()
    assert dash._widgets[4]._value_label.text() == "1 g", \
        "换算后应显示 1 g，实际 %s" % dash._widgets[4]._value_label.text()

    # 带换算 + 声明量程的仪表
    dash.add_channel(Channel(5, "Voltage", "f32", "V", visual="gauge",
                             scale=0.001, offset=0.0,
                             minimum=0.0, maximum=5.0))
    g = dash._widgets[5]
    assert g._lo == 0.0 and g._hi == 5.0, "gauge 应使用声明量程"
    dash.update_value(5, 3300)   # 3300 mV → 3.3 V
    _app.processEvents()
    assert abs(g._value - 3.3) < 1e-9
    assert g._lo == 0.0 and g._hi == 5.0, "声明量程后不应再自适应扩展"

    # 无声明量程的仪表仍自适应
    dash.add_channel(Channel(6, "Raw", "i16", "raw", visual="gauge"))
    dash.update_value(6, 120)
    assert dash._widgets[6]._hi >= 120, "无声明量程应自适应扩展"

    # 曲线按换算值采样
    dash.add_channel(Channel(7, "Gyro_Z", "i16", "deg/s", visual="chart",
                             scale=1.0 / 131.0, offset=0.0))
    dash.update_value(7, 131)
    _app.processEvents()
    assert len(dash._widgets[7]._points) == 1
    assert abs(dash._widgets[7]._points[0][1] - 1.0) < 1e-9, "曲线点应为换算值"
    print("PASS: 组件按物理量换算显示（文本/仪表/曲线 + 声明量程）")


if __name__ == "__main__":
    test_create_widget_factory()
    test_dashboard_lifecycle()
    test_grid_no_overlap()
    test_dashboard_duplicate_channel()
    test_dashboard_scale_display()
