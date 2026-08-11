"""GUI 冒烟测试（离屏运行，不显示窗口）。

覆盖 Stage 1 + Stage 2 + Stage 3 完整链路：
打开串口 → MCU 发送协议行 → 设备面板出现设备名 + 通道 → 数值更新
→ 仪表盘按 visual 自动生成组件并刷新。

运行方式（在项目根目录）::

    python -m tests.test_gui_smoke
"""

import os
import time

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication

from desktop.ui.main_window import MainWindow


def _wait_for_text(window, app, text, timeout=3.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        app.processEvents()
        if text in window._log_view.toPlainText():
            return True
        time.sleep(0.02)
    return False


def test_window_loopback():
    app = QApplication.instance() or QApplication([])
    window = MainWindow()
    window.show()

    assert window._baud_combo.currentText() == "115200"
    assert window._connect_btn.text() == "打开串口"

    # 用 loop:// 打开串口
    window._manager.open("loop://", 115200)
    window._update_connection_state()
    assert window._connect_btn.text() == "关闭串口"

    # --- Stage 1：命令发送 ---
    window._command_edit.setText("led on")
    window._ending_combo.setCurrentIndex(0)
    window._send_command()
    assert window._command_edit.text() == "", "发送后输入框应清空"
    assert _wait_for_text(window, app, "led on"), "日志窗口未出现命令回显"

    # --- Stage 2：MCU 发送模拟设备注册 ---
    window._manager.send("$DEV name=Quadcopter,ver=1.0\n")
    assert _wait_for_text(window, app, "$DEV"), "日志窗口未出现 $DEV 行"
    assert window._device_manager.device is not None
    assert window._device_manager.device.name == "Quadcopter"
    assert window._device_panel.isVisible(), "设备面板应可见"

    # 注册通道
    window._manager.send("$CH id=0,name=Throttle,type=u16,unit=us\n")
    window._manager.send("$CH id=1,name=Accel_X,type=i16,unit=raw\n")
    app.processEvents()
    time.sleep(0.1)
    app.processEvents()

    assert 0 in window._device_manager.device.channels
    assert 1 in window._device_manager.device.channels
    assert window._channel_tree.topLevelItemCount() == 2

    # --- MCU 周期重发注册信息（联调常见场景：每 2s 重发 $DEV/$CH） ---
    # 设备通道不应丢失、树与仪表盘不应产生重复
    window._manager.send("$DEV name=Quadcopter,ver=1.0\n")
    window._manager.send("$CH id=0,name=Throttle,type=u16,unit=us\n")
    window._manager.send("$CH id=1,name=Accel_X,type=i16,unit=raw\n")
    app.processEvents()
    time.sleep(0.1)
    app.processEvents()

    assert window._device_manager.device.name == "Quadcopter"
    assert 0 in window._device_manager.device.channels, "重复宣告不应清空通道"
    assert 1 in window._device_manager.device.channels
    assert window._channel_tree.topLevelItemCount() == 2, "重复注册不应新增树行"
    assert window._dashboard.count() == 2, "重复注册不应新增仪表盘组件"

    # 发送数据更新
    window._manager.send("$VAL id=0,val=1500\n")
    app.processEvents()
    time.sleep(0.1)
    app.processEvents()

    ch0 = window._device_manager.device.get_channel(0)
    assert ch0.value == 1500

    # 设备面板中有更新后的值
    found = False
    for i in range(window._channel_tree.topLevelItemCount()):
        item = window._channel_tree.topLevelItem(i)
        if item.data(0, Qt.ItemDataRole.UserRole) == 0:
            found = "1500" in item.text(1)
            break
    assert found, "通道树中 Throttle 值应更新为 1500 us"

    # --- 清空后协议仍然工作 ---
    window._log_view.clear()
    window._device_manager.reset()
    assert window._device_manager.device is None
    assert not window._device_panel.isVisible()
    assert window._channel_tree.topLevelItemCount() == 0
    assert window._dashboard.count() == 0, "reset 后仪表盘应清空"

    # --- Stage 3：带 visual 的通道注册 → 自动生成仪表盘 ---
    window._manager.send("$DEV name=Quadcopter,ver=1.0\n")
    window._manager.send("$CH id=0,name=Throttle,type=u16,unit=us,visual=gauge\n")
    window._manager.send("$CH id=1,name=Roll,type=i16,unit=degree,visual=chart\n")
    window._manager.send("$CH id=2,name=Status,type=str\n")
    app.processEvents()
    time.sleep(0.1)
    app.processEvents()

    assert window._dashboard.count() == 3
    from desktop.visualization.widgets.chart_widget import ChartWidget
    from desktop.visualization.widgets.gauge_widget import GaugeWidget
    from desktop.visualization.widgets.text_widget import TextWidget
    assert isinstance(window._dashboard._widgets[0], GaugeWidget)
    assert isinstance(window._dashboard._widgets[1], ChartWidget)
    assert isinstance(window._dashboard._widgets[2], TextWidget)
    assert window._tab_widget.count() == 2, "应包含 日志终端 / 仪表盘 两个 Tab"

    # 仪表盘随 $VAL 实时刷新
    window._manager.send("$VAL id=0,val=1500\n")
    window._manager.send("$VAL id=1,val=-512\n")
    app.processEvents()
    time.sleep(0.1)
    app.processEvents()

    assert window._dashboard._widgets[0]._value == 1500
    assert len(window._dashboard._widgets[1]._points) == 1
    assert window._dashboard._widgets[1]._points[0][1] == -512.0

    # 切换仪表盘 Tab 可见
    window._tab_widget.setCurrentIndex(1)
    assert window._tab_widget.currentIndex() == 1
    app.processEvents()

    window._manager.close()
    window.close()
    print("PASS: Stage 1 + Stage 2 + Stage 3 GUI 冒烟测试通过")


if __name__ == "__main__":
    test_window_loopback()
