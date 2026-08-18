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
    assert window._tab_widget.count() == 3, "应包含 日志终端 / 仪表盘 / 参数 三个 Tab"

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


def test_record_replay_roundtrip():
    """Stage 4：会话记录 → 离线回放 → 日志/设备面板/仪表盘全链路恢复。"""
    app = QApplication.instance() or QApplication([])
    window = MainWindow()
    window.show()

    rec_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), ".tmp_run", "smoke_session.csv")
    os.makedirs(os.path.dirname(rec_path), exist_ok=True)

    # --- 记录：直接注入数据行（确定性更强，不依赖串口） ---
    window._recorder.start(rec_path)
    assert window._recorder.is_recording
    window._on_data("$DEV name=Quadcopter,ver=1.0")
    window._on_data("$CH id=0,name=Throttle,type=u16,unit=us,visual=gauge")
    window._on_data("$VAL id=0,val=1500")
    window._stop_recording()
    assert not window._recorder.is_recording
    assert os.path.exists(rec_path)
    assert window._record_btn.isEnabled(), "停止记录后「开始记录」应恢复可用"

    # --- 回放：载入 → 推进到末尾（不依赖真实定时器） ---
    window._device_manager.reset()
    window._log_view.clear()
    window._replay.load(rec_path)
    assert window._replay.line_count == 3
    window._set_replay_controls(True)
    window._replay.play()
    window._replay.advance(10 ** 9)
    app.processEvents()
    time.sleep(0.1)
    app.processEvents()

    assert window._device_manager.device is not None
    assert window._device_manager.device.name == "Quadcopter", "回放应重建设备"
    assert 0 in window._device_manager.device.channels
    assert window._dashboard.count() == 1, "回放应重建仪表盘组件"
    assert window._dashboard._widgets[0]._value == 1500, "回放应恢复仪表盘数值"
    assert "$DEV" in window._log_view.toPlainText(), "回放行应进入日志终端"

    window._replay.stop()
    window.close()
    print("PASS: 会话记录 + 离线回放冒烟测试通过")


def test_param_panel():
    """Stage 5：参数协议全链路——注册 → 分组树 → 值更新 → 下发 → ACK → 预设。"""
    app = QApplication.instance() or QApplication([])
    window = MainWindow()
    window.show()

    # 下发需要串口（loop:// 回环，命令会回显到日志）
    window._manager.open("loop://", 115200)
    window._update_connection_state()

    # --- 参数注册 → 分组树 ---
    window._manager.send("$P id=0,name=Roll_Kp,type=f32,min=0,max=10,val=1.5,group=Roll\n")
    window._manager.send("$P id=1,name=Yaw_Kp,type=f32,min=0,max=10,val=1.0,group=Yaw\n")
    app.processEvents()
    time.sleep(0.1)
    app.processEvents()

    assert 0 in window._param_manager.params
    assert window._param_manager.get(0).minimum == 0.0
    assert window._param_panel._tree.topLevelItemCount() == 2, "应有两个分组"

    # --- 周期重发 $P 不产生重复 ---
    window._manager.send("$P id=0,name=Roll_Kp,type=f32,min=0,max=10,val=1.5,group=Roll\n")
    app.processEvents()
    time.sleep(0.05)
    app.processEvents()
    assert window._param_panel._tree.topLevelItemCount() == 2, "重复注册不应新增分组"

    # --- $PV 值更新 ---
    window._manager.send("$PV id=0,val=1.8\n")
    app.processEvents()
    time.sleep(0.1)
    app.processEvents()
    assert window._param_manager.get(0).value == 1.8

    # --- 下发 $PS → 日志回显 ---
    window._send_param_set(0, "2.0")
    assert _wait_for_text(window, app, "$PS id=0,val=2.0"), "下发行应回显到日志"

    # --- ACK → 状态列 ✓ ---
    window._manager.send("$PA id=0,ok=1\n")
    app.processEvents()
    time.sleep(0.1)
    app.processEvents()
    assert "✓" in window._param_panel._items[0].text(3), "ACK 成功应显示 ✓"

    # --- 预设：直接按名称应用（不经文件对话框） ---
    applied = window._param_panel.apply_preset({"Roll_Kp": "9.9", "NotExist": "1"})
    assert applied == 1, "应只匹配到存在的参数"
    assert window._param_panel._items[0].text(1) == "9.9"

    # --- reset 清空 ---
    window._param_manager.reset()
    assert window._param_panel._tree.topLevelItemCount() == 0

    window._manager.close()
    window.close()
    print("PASS: 参数调节面板冒烟测试通过")


def test_channel_scale_smoke():
    """Stage 6：$CH 带换算字段 → 通道树显示换算后的物理量。"""
    app = QApplication.instance() or QApplication([])
    window = MainWindow()
    window.show()

    window._manager.open("loop://", 115200)
    window._update_connection_state()

    window._on_data("$DEV name=Quadcopter,ver=1.0")
    window._on_data(
        "$CH id=4,name=Accel_X,type=i16,unit=g,scale=6.10352e-05,offset=0,min=-2,max=2")
    window._on_data("$VAL id=4,val=16384")
    app.processEvents()
    time.sleep(0.1)
    app.processEvents()

    # 通道树应显示换算后的 "1 g"（而非 16384 raw）
    found = False
    for i in range(window._channel_tree.topLevelItemCount()):
        item = window._channel_tree.topLevelItem(i)
        if item.data(0, Qt.ItemDataRole.UserRole) == 4:
            assert item.text(1) == "1 g", "换算后应显示 1 g，实际 %s" % item.text(1)
            found = True
            break
    assert found, "通道树中应有 Accel_X"

    # 设备模型中的通道持有换算元信息
    ch = window._device_manager.device.get_channel(4)
    assert ch.minimum == -2.0 and ch.maximum == 2.0

    window._manager.close()
    window.close()
    print("PASS: 通道物理量换算冒烟测试通过")


if __name__ == "__main__":
    test_window_loopback()
    test_record_replay_roundtrip()
    test_param_panel()
    test_channel_scale_smoke()
