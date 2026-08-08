"""GUI 冒烟测试（离屏运行，不显示窗口）。

覆盖 Stage 1 + Stage 2 完整链路：
打开串口 → MCU 发送协议行 → 设备面板出现设备名 + 通道 → 数值更新。

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

    window._manager.close()
    window.close()
    print("PASS: Stage 1 + Stage 2 GUI 冒烟测试通过")


if __name__ == "__main__":
    test_window_loopback()
