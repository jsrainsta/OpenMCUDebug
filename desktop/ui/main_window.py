"""主窗口界面。

Stage 3：串口连接 + 日志终端 + 命令发送 + 设备信息面板 + 通道数据面板 + 自动仪表盘。
Stage 4：会话记录（CSV）与离线回放。
Stage 5：参数调节面板（$P/$PV/$PA 协议 + 分组编辑 + 预设）。
"""

import json
import time
from html import escape

from PyQt6.QtCore import Qt, QObject, pyqtSignal
from PyQt6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QSplitter,
    QTabWidget,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from desktop.device.device_manager import DeviceManager
from desktop.param.param_manager import ParamManager
from desktop.param.param_panel import ParamPanel
from desktop.parser.log_parser import color_for, parse_line
from desktop.protocol.protocol import parse_line as parse_protocol
from desktop.recorder.replay import ReplayPlayer
from desktop.recorder.session_recorder import SessionRecorder
from desktop.serial.serial_manager import SerialManager
from desktop.visualization.base import fmt_value
from desktop.visualization.dashboard import DashboardWidget

# 常用波特率
BAUD_RATES = ["9600", "19200", "38400", "57600", "115200",
              "230400", "460800", "921600"]

LINE_ENDINGS = {
    "\\r\\n (CRLF)": "\r\n",
    "\\n (LF)": "\n",
    "无": "",
}

SYSTEM_COLOR = "#808080"
SEND_COLOR = "#5ac8fa"
PROTOCOL_LEVEL = "$PROTOCOL"


class _SerialBridge(QObject):
    data_received = pyqtSignal(str)
    error = pyqtSignal(str)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("MCU Debug Assistant")
        self.resize(1100, 650)

        # ---- 模型层 ----
        self._device_manager = DeviceManager()
        self._device_manager.device_updated.connect(self._on_device_updated)
        self._device_manager.channel_added.connect(self._on_channel_added)
        self._device_manager.value_updated.connect(self._on_value_updated)
        self._device_manager.device_reset.connect(self._on_device_reset)

        # ---- Stage 5：参数模型 ----
        self._param_manager = ParamManager()
        self._param_manager.param_reset.connect(self._on_param_reset)

        # ---- 串口桥接 ----
        self._bridge = _SerialBridge()
        self._manager = SerialManager(
            on_data=self._bridge.data_received.emit,
            on_error=self._bridge.error.emit,
        )
        self._bridge.data_received.connect(self._on_data)
        self._bridge.error.connect(self._on_error)

        # ---- Stage 4：会话记录与回放 ----
        self._recorder = SessionRecorder()
        self._replay = ReplayPlayer()
        self._replay.line_ready.connect(self._on_replay_line)
        self._replay.finished.connect(self._on_replay_finished)

        self._build_ui()
        self.refresh_ports()
        self._update_connection_state()

    # ====== 界面构建 ======

    def _build_ui(self):
        central = QWidget()
        layout = QVBoxLayout(central)
        layout.setContentsMargins(8, 8, 8, 8)

        # 先创建设备面板和日志控件（工具栏"清空日志"按钮需要引用 _log_view）
        self._device_panel = self._build_device_panel()
        self._device_panel.setVisible(False)

        self._log_view = QPlainTextEdit()
        self._log_view.setReadOnly(True)
        self._log_view.setMaximumBlockCount(5000)
        self._log_view.setStyleSheet(
            "QPlainTextEdit { background-color: #1e1f22; color: #c8c8c8;"
            " font-family: Consolas, 'Courier New'; font-size: 13px; }"
        )

        # Stage 3：自动仪表盘（日志终端 / 仪表盘 两个 Tab）
        self._dashboard = DashboardWidget()
        self._tab_widget = QTabWidget()
        self._tab_widget.addTab(self._log_view, "日志终端")
        self._tab_widget.addTab(self._dashboard, "仪表盘")

        # Stage 5：参数调节面板（第三个 Tab）
        self._param_panel = ParamPanel()
        self._param_panel.set_requested.connect(self._send_param_set)
        self._param_panel.save_preset_requested.connect(self._save_preset)
        self._param_panel.load_preset_requested.connect(self._load_preset)
        self._param_manager.param_added.connect(self._param_panel.add_param)
        self._param_manager.param_value_updated.connect(self._param_panel.update_value)
        self._param_manager.param_acked.connect(self._param_panel.set_ack)
        self._tab_widget.addTab(self._param_panel, "参数")

        layout.addLayout(self._build_toolbar())
        layout.addLayout(self._build_record_bar())

        # -- 左右分栏：设备面板 | 日志/仪表盘 --
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(self._device_panel)
        splitter.addWidget(self._tab_widget)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 3)
        splitter.setSizes([250, 850])

        layout.addWidget(splitter, stretch=1)

        layout.addLayout(self._build_command_bar())

        self.setCentralWidget(central)
        self.statusBar().showMessage("未连接")

    def _build_device_panel(self):
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 4, 0)

        self._device_label = QLabel("")
        self._device_label.setStyleSheet(
            "QLabel { font-weight: bold; font-size: 13px; color: #e0e0e0;"
            " padding: 4px 0; }"
        )
        layout.addWidget(self._device_label)

        self._channel_tree = QTreeWidget()
        self._channel_tree.setHeaderLabels(["通道", "值"])
        self._channel_tree.setRootIsDecorated(False)
        self._channel_tree.setAlternatingRowColors(True)
        self._channel_tree.setStyleSheet(
            "QTreeWidget { background-color: #1e1f22; color: #c8c8c8;"
            " font-family: Consolas, 'Courier New'; font-size: 12px;"
            " alternate-background-color: #232428; }"
            "QHeaderView::section { background-color: #2b2d30; color: #a0a0a0;"
            " border: none; padding: 3px 6px; }"
        )
        header = self._channel_tree.header()
        header.setStretchLastSection(True)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)

        layout.addWidget(self._channel_tree)
        return panel

    def _build_toolbar(self):
        bar = QHBoxLayout()

        bar.addWidget(QLabel("串口:"))
        self._port_combo = QComboBox()
        self._port_combo.setMinimumWidth(120)
        bar.addWidget(self._port_combo)

        refresh_btn = QPushButton("刷新")
        refresh_btn.clicked.connect(self.refresh_ports)
        bar.addWidget(refresh_btn)

        bar.addWidget(QLabel("波特率:"))
        self._baud_combo = QComboBox()
        self._baud_combo.addItems(BAUD_RATES)
        self._baud_combo.setCurrentText("115200")
        bar.addWidget(self._baud_combo)

        self._connect_btn = QPushButton("打开串口")
        self._connect_btn.clicked.connect(self._toggle_connection)
        bar.addWidget(self._connect_btn)

        bar.addStretch(1)

        clear_btn = QPushButton("清空日志")
        clear_btn.clicked.connect(self._log_view.clear)
        bar.addWidget(clear_btn)

        return bar

    def _build_record_bar(self):
        """Stage 4：会话记录 + 离线回放控件。"""
        bar = QHBoxLayout()

        self._record_btn = QPushButton("● 开始记录")
        self._record_btn.clicked.connect(self._start_recording)
        bar.addWidget(self._record_btn)

        self._stop_record_btn = QPushButton("■ 停止记录")
        self._stop_record_btn.setEnabled(False)
        self._stop_record_btn.clicked.connect(self._stop_recording)
        bar.addWidget(self._stop_record_btn)

        bar.addSpacing(12)

        self._replay_btn = QPushButton("▶ 回放…")
        self._replay_btn.clicked.connect(self._choose_replay_file)
        bar.addWidget(self._replay_btn)

        self._pause_btn = QPushButton("暂停/继续")
        self._pause_btn.setEnabled(False)
        self._pause_btn.clicked.connect(self._toggle_replay_pause)
        bar.addWidget(self._pause_btn)

        bar.addWidget(QLabel("速度:"))
        self._speed_combo = QComboBox()
        self._speed_combo.addItems(["0.5x", "1x", "2x", "4x"])
        self._speed_combo.setCurrentText("1x")
        self._speed_combo.setEnabled(False)
        self._speed_combo.currentTextChanged.connect(self._on_replay_speed)
        bar.addWidget(self._speed_combo)

        self._stop_replay_btn = QPushButton("■ 停止回放")
        self._stop_replay_btn.setEnabled(False)
        self._stop_replay_btn.clicked.connect(self._stop_replay)
        bar.addWidget(self._stop_replay_btn)

        bar.addStretch(1)

        self._record_status = QLabel("")
        self._record_status.setStyleSheet("QLabel { color: #a0a0a0; }")
        bar.addWidget(self._record_status)

        return bar

    def _build_command_bar(self):
        bar = QHBoxLayout()

        bar.addWidget(QLabel("命令:"))
        self._command_edit = QLineEdit()
        self._command_edit.setPlaceholderText("输入命令，如: led on")
        self._command_edit.returnPressed.connect(self._send_command)
        bar.addWidget(self._command_edit, stretch=1)

        bar.addWidget(QLabel("行尾:"))
        self._ending_combo = QComboBox()
        self._ending_combo.addItems(list(LINE_ENDINGS.keys()))
        bar.addWidget(self._ending_combo)

        send_btn = QPushButton("发送")
        send_btn.clicked.connect(self._send_command)
        bar.addWidget(send_btn)

        return bar

    # ====== 串口连接 ======

    def refresh_ports(self):
        current = self._port_combo.currentText()
        self._port_combo.clear()
        ports = SerialManager.list_ports()
        self._port_combo.addItems(ports)
        if current in ports:
            self._port_combo.setCurrentText(current)
        elif ports:
            self._port_combo.setCurrentIndex(0)

    def _toggle_connection(self):
        if self._manager.is_open():
            self._manager.close()
            self._device_manager.reset()
            self._param_manager.reset()
            self._update_connection_state()
            self._append_system("串口已关闭")
            return

        port = self._port_combo.currentText()
        baudrate = int(self._baud_combo.currentText())
        if not port:
            QMessageBox.warning(self, "提示", "没有可用的串口，请检查设备连接后点刷新。")
            return
        try:
            self._manager.open(port, baudrate)
        except Exception as exc:
            QMessageBox.critical(self, "打开失败", str(exc))
            return
        self._device_manager.reset()
        self._param_manager.reset()
        self._update_connection_state()
        self._append_system("已连接 %s @ %d" % (port, baudrate))

    def _update_connection_state(self):
        connected = self._manager.is_open()
        self._connect_btn.setText("关闭串口" if connected else "打开串口")
        self._port_combo.setEnabled(not connected)
        self._baud_combo.setEnabled(not connected)
        if connected:
            self.statusBar().showMessage(
                "已连接 %s @ %s"
                % (self._port_combo.currentText(), self._baud_combo.currentText())
            )
        else:
            self.statusBar().showMessage("未连接")

    # ====== 数据路由（Stage1 + Stage2）======

    def _on_data(self, line):
        """收到 MCU 行数据 → 记录 → 协议解析 → 日志显示。"""
        for sub in line.splitlines():
            if not sub:
                continue
            # Stage 4：记录原始行（含时间戳），供离线回放
            if self._recorder.is_recording:
                self._recorder.record(sub)
            # 尝试 Stage 2/5 协议解析
            kind, data = parse_protocol(sub)
            if kind:
                if kind in ("DEV", "CH", "VAL"):
                    self._device_manager.process_message(kind, data)
                elif kind in ("P", "PV", "PA"):
                    self._param_manager.process_message(kind, data)
            # 日志显示（Stage 1 着色 + 协议行以紫色显示）
            self._append_log(sub)

    # ====== Stage 4：会话记录 / 回放 ======

    def _start_recording(self):
        default_name = "session_%s.csv" % time.strftime("%Y%m%d_%H%M%S")
        path, _ = QFileDialog.getSaveFileName(
            self, "保存会话记录", default_name, "CSV 文件 (*.csv)")
        if not path:
            return
        self._recorder.start(path)
        self._record_btn.setEnabled(False)
        self._stop_record_btn.setEnabled(True)
        self._record_status.setText("● 记录中: %s" % path)
        self.statusBar().showMessage("开始记录: %s" % path)

    def _stop_recording(self):
        path = self._recorder.path
        self._recorder.stop()
        self._record_btn.setEnabled(True)
        self._stop_record_btn.setEnabled(False)
        self._record_status.setText("已保存: %s" % path)
        self.statusBar().showMessage("记录已保存: %s" % path)

    def _choose_replay_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "选择回放文件", "", "CSV 文件 (*.csv)")
        if not path:
            return
        self._replay.load(path)
        # 干净起点：清空设备/仪表盘/日志，避免与旧状态混合
        self._device_manager.reset()
        self._log_view.clear()
        self._on_replay_speed(self._speed_combo.currentText())
        self._set_replay_controls(True)
        self._replay.play()
        self.statusBar().showMessage("回放中: %s (%d 行)" % (path, self._replay.line_count))

    def _on_replay_line(self, line):
        """回放的一行数据 → 走与串口接收完全相同的数据链路。"""
        self._on_data(line)

    def _on_replay_finished(self):
        self._set_replay_controls(False)
        self.statusBar().showMessage("回放结束")

    def _toggle_replay_pause(self):
        if self._replay.is_playing:
            self._replay.pause()
            self._pause_btn.setText("继续")
            self.statusBar().showMessage("回放已暂停")
        else:
            self._replay.play()
            self._pause_btn.setText("暂停")
            self.statusBar().showMessage("回放中")

    def _stop_replay(self):
        self._replay.stop()
        self._set_replay_controls(False)
        self.statusBar().showMessage("回放已停止")

    def _on_replay_speed(self, text):
        self._replay.set_speed(float(text.rstrip("x")))

    def _set_replay_controls(self, playing):
        self._replay_btn.setEnabled(not playing)
        self._pause_btn.setEnabled(playing)
        self._pause_btn.setText("暂停" if playing else "继续")
        self._speed_combo.setEnabled(playing)
        self._stop_replay_btn.setEnabled(playing)

    def _append_log(self, line):
        level, content = parse_line(line)
        self._log_view.appendHtml(self._fmt(content, color_for(level), tag=level))

    def _append_system(self, message):
        self._log_view.appendHtml(self._fmt(message, SYSTEM_COLOR))

    def _append_send(self, command):
        self._log_view.appendHtml(self._fmt(command, SEND_COLOR))

    @staticmethod
    def _fmt(text, color, tag=None):
        if tag and tag == PROTOCOL_LEVEL:
            # 协议行不重复显示 tag
            return '<span style="color:%s">%s</span>' % (color, escape(text))
        prefix = "[%s] " % tag if tag else ""
        return '<span style="color:%s">%s%s</span>' % (color, prefix, escape(text))

    # ====== 设备面板回调 ======

    def _on_device_updated(self, name, version):
        self._device_panel.setVisible(True)
        label = name
        if version:
            label += " v" + version
        self._device_label.setText(label)

    def _on_channel_added(self, channel):
        # MCU 周期重发 $CH 时按 id 去重，避免通道树出现重复行
        for i in range(self._channel_tree.topLevelItemCount()):
            if self._channel_tree.topLevelItem(i).data(0, Qt.ItemDataRole.UserRole) == channel.id:
                return
        label = "%s (%s)" % (channel.name, channel.unit) if channel.unit else channel.name
        item = QTreeWidgetItem([label, "—"])
        item.setData(0, Qt.ItemDataRole.UserRole, channel.id)
        self._channel_tree.addTopLevelItem(item)
        # Stage 3：仪表盘按 visual 字段自动生成组件
        self._dashboard.add_channel(channel)

    def _on_value_updated(self, ch_id, raw_val, parsed_val):
        display = raw_val
        # Stage 6：显示换算后的物理量（value * scale + offset）+ 单位
        if self._device_manager.device:
            ch = self._device_manager.device.get_channel(ch_id)
            if ch:
                display = fmt_value(ch.scaled(parsed_val))
                if ch.unit:
                    display += " " + ch.unit
        # 在树中查找并更新
        for i in range(self._channel_tree.topLevelItemCount()):
            item = self._channel_tree.topLevelItem(i)
            if item.data(0, Qt.ItemDataRole.UserRole) == ch_id:
                item.setText(1, display)
                break
        # Stage 3：刷新仪表盘对应组件
        self._dashboard.update_value(ch_id, parsed_val)

    def _on_device_reset(self):
        self._device_panel.setVisible(False)
        self._device_label.setText("")
        self._channel_tree.clear()
        # Stage 3：清空仪表盘
        self._dashboard.reset()

    # ====== Stage 5：参数 ======

    def _on_param_reset(self):
        self._param_panel.reset()

    def _send_param_set(self, param_id, value_str):
        """下发参数：$PS id=..,val=..（CRLF 结尾，协议行固定行尾）。"""
        if not self._manager.is_open():
            QMessageBox.warning(self, "提示", "请先打开串口。")
            return
        line = "$PS id=%d,val=%s" % (param_id, value_str.strip())
        try:
            self._manager.send(line + "\r\n")
        except Exception as exc:
            QMessageBox.critical(self, "发送失败", str(exc))
            return
        self._append_send(line)

    def _save_preset(self, values):
        """把当前全部参数值保存为 JSON 预设文件。"""
        path, _ = QFileDialog.getSaveFileName(
            self, "保存参数预设", "pid_preset.json", "JSON 文件 (*.json)")
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(values, f, indent=2, ensure_ascii=False)
        except OSError as exc:
            QMessageBox.critical(self, "保存失败", str(exc))
            return
        self.statusBar().showMessage("预设已保存: %s" % path)

    def _load_preset(self):
        """载入 JSON 预设：按名称匹配参数，更新显示并（串口打开时）全部下发。"""
        path, _ = QFileDialog.getOpenFileName(
            self, "载入参数预设", "", "JSON 文件 (*.json)")
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                values = json.load(f)
        except (OSError, ValueError) as exc:
            QMessageBox.critical(self, "载入失败", str(exc))
            return
        if not isinstance(values, dict):
            QMessageBox.warning(self, "载入失败", "预设文件格式不正确。")
            return

        applied = self._param_panel.apply_preset(values)
        if applied == 0:
            QMessageBox.information(self, "提示", "预设中的参数在当前设备中不存在。")
            return

        # 串口打开时确认后全部下发
        if self._manager.is_open():
            reply = QMessageBox.question(
                self, "下发预设",
                "将下发 %d 个参数到设备，继续？" % applied,
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if reply == QMessageBox.StandardButton.Yes:
                by_name = {p.name: p for p in self._param_manager.params.values()}
                sent = 0
                for name, value in values.items():
                    param = by_name.get(name)
                    if param is not None:
                        self._send_param_set(param.id, str(value))
                        sent += 1
                self.statusBar().showMessage("已下发 %d 个参数" % sent)
        else:
            self.statusBar().showMessage(
                "预设已载入 %d 个参数（未连接，未下发）" % applied)

    # ====== 命令发送 ======

    def _send_command(self):
        if not self._manager.is_open():
            QMessageBox.warning(self, "提示", "请先打开串口。")
            return
        command = self._command_edit.text().strip()
        if not command:
            return
        line = command + LINE_ENDINGS[self._ending_combo.currentText()]
        try:
            self._manager.send(line)
        except Exception as exc:
            QMessageBox.critical(self, "发送失败", str(exc))
            return
        self._append_send(command)
        self._command_edit.clear()

    def _on_error(self, message):
        QMessageBox.warning(self, "串口错误", message)

    def closeEvent(self, event):
        self._manager.close()
        self._recorder.stop()
        self._replay.stop()
        super().closeEvent(event)
