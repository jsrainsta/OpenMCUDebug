"""主窗口界面。

包含串口选择、波特率设置、打开/关闭、日志终端和命令发送。
"""

from html import escape

from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from desktop.parser.log_parser import color_for, parse_line
from desktop.serial.serial_manager import SerialManager

# 常用波特率
BAUD_RATES = ["9600", "19200", "38400", "57600", "115200",
              "230400", "460800", "921600"]

# 行尾选项: 界面显示文本 -> 实际追加内容
LINE_ENDINGS = {
    "\\r\\n (CRLF)": "\r\n",
    "\\n (LF)": "\n",
    "无": "",
}

SYSTEM_COLOR = "#808080"  # 系统提示（连接状态等）
SEND_COLOR = "#5ac8fa"    # 发送命令回显


class _SerialBridge(QObject):
    """把后台接收线程的调用桥接为 Qt 信号（线程安全）。"""

    data_received = pyqtSignal(str)
    error = pyqtSignal(str)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("MCU Debug Assistant")
        self.resize(900, 600)

        self._bridge = _SerialBridge()
        self._manager = SerialManager(
            on_data=self._bridge.data_received.emit,
            on_error=self._bridge.error.emit,
        )
        self._bridge.data_received.connect(self._on_data)
        self._bridge.error.connect(self._on_error)

        self._build_ui()
        self.refresh_ports()
        self._update_connection_state()

    # ---------- 界面构建 ----------

    def _build_ui(self):
        central = QWidget()
        layout = QVBoxLayout(central)
        layout.setContentsMargins(8, 8, 8, 8)

        # 先创建日志控件，工具栏里的“清空日志”按钮要引用它
        self._log_view = QPlainTextEdit()
        self._log_view.setReadOnly(True)
        self._log_view.setMaximumBlockCount(5000)  # 防止长时间运行内存膨胀
        self._log_view.setStyleSheet(
            "QPlainTextEdit { background-color: #1e1f22; color: #c8c8c8;"
            " font-family: Consolas, 'Courier New'; font-size: 13px; }"
        )

        layout.addLayout(self._build_toolbar())
        layout.addWidget(self._log_view, stretch=1)

        layout.addLayout(self._build_command_bar())

        self.setCentralWidget(central)
        self.statusBar().showMessage("未连接")

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

    # ---------- 串口连接 ----------

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
            self._update_connection_state()
            self._append_system("串口已关闭")
            return

        port = self._port_combo.currentText()
        baudrate = int(self._baud_combo.currentText())
        if not port:
            QMessageBox.warning(
                self, "提示", "没有可用的串口，请检查设备连接后点“刷新”。"
            )
            return
        try:
            self._manager.open(port, baudrate)
        except Exception as exc:
            QMessageBox.critical(self, "打开失败", str(exc))
            return
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

    # ---------- 日志显示 ----------

    def _on_data(self, line):
        """收到 MCU 数据（后台线程 -> Qt 信号）。"""
        for sub in line.splitlines():
            self._append_log(sub)

    def _append_log(self, line):
        level, content = parse_line(line)
        self._log_view.appendHtml(self._fmt(content, color_for(level), tag=level))

    def _append_system(self, message):
        self._log_view.appendHtml(self._fmt(message, SYSTEM_COLOR))

    def _append_send(self, command):
        self._log_view.appendHtml(self._fmt(command, SEND_COLOR))

    @staticmethod
    def _fmt(text, color, tag=None):
        prefix = "[%s] " % tag if tag else ""
        return '<span style="color:%s">%s%s</span>' % (color, prefix, escape(text))

    def _on_error(self, message):
        QMessageBox.warning(self, "串口错误", message)

    # ---------- 命令发送 ----------

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

    # ---------- 窗口关闭 ----------

    def closeEvent(self, event):
        self._manager.close()
        super().closeEvent(event)
