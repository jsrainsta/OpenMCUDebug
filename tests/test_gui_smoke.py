"""GUI 冒烟测试（离屏运行，不显示窗口）。

用 pyserial 的 loop:// 虚拟串口走完整链路：
打开串口 -> 发送命令 -> 收到回路回显 -> 日志窗口出现内容。

运行方式（在项目根目录）::

    python -m tests.test_gui_smoke
"""

import os
import time

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

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

    # 初始状态
    assert window._baud_combo.currentText() == "115200"
    assert window._connect_btn.text() == "打开串口"

    # 用 loop:// 打开，走完整收发链路
    window._manager.open("loop://", 115200)
    window._update_connection_state()
    assert window._connect_btn.text() == "关闭串口"

    window._command_edit.setText("led on")
    window._ending_combo.setCurrentIndex(0)  # CRLF
    window._send_command()
    assert window._command_edit.text() == "", "发送后命令输入框应清空"

    # 日志窗口中应出现命令回显 + loop:// 原样返回的命令行（两处均含 "led on"）
    assert _wait_for_text(window, app, "led on"), "日志窗口未出现命令回显"

    window._manager.close()
    window.close()
    print("PASS: 界面 + 回路收发冒烟测试通过")


if __name__ == "__main__":
    test_window_loopback()
