"""串口通信管理模块。

负责串口的枚举、打开、关闭、发送和后台接收。
不依赖 PyQt，通过回调把接收数据交给上层，保持模块低耦合。
"""

import threading

import serial
from serial.tools import list_ports


class SerialManager:
    """串口管理器。

    用法::

        mgr = SerialManager(on_data=callback, on_error=callback)
        mgr.open("COM3", 115200)
        mgr.send("led on")
        mgr.close()
    """

    def __init__(self, on_data=None, on_error=None):
        self._serial = None
        self._reader = None
        self._running = False
        self._on_data = on_data    # 收到一行数据: on_data(line: str)
        self._on_error = on_error  # 读取出错: on_error(msg: str)

    @staticmethod
    def list_ports():
        """返回系统当前可用的串口名列表。"""
        return [port.device for port in list_ports.comports()]

    def is_open(self):
        return self._serial is not None and self._serial.is_open

    def open(self, port, baudrate):
        """打开串口并启动后台接收线程。"""
        if self.is_open():
            self.close()
        try:
            # serial_for_url 同时支持真实串口（COM3 等）和
            # 测试用的虚拟串口（loop:// 回路），详见 tests/
            self._serial = serial.serial_for_url(port, baudrate, timeout=0.1)
        except (serial.SerialException, ValueError, OSError) as exc:
            raise serial.SerialException(
                "无法打开串口 %s: %s" % (port, exc)
            ) from exc
        self._running = True
        self._reader = threading.Thread(target=self._read_loop, daemon=True)
        self._reader.start()

    def close(self):
        """关闭串口并停止接收线程。"""
        self._running = False
        if self._reader is not None:
            self._reader.join(timeout=1.0)
            self._reader = None
        if self._serial is not None:
            try:
                self._serial.close()
            except Exception:
                pass
            self._serial = None

    def send(self, text):
        """发送一段文本（UTF-8 编码）。串口未打开时抛出 RuntimeError。"""
        if not self.is_open():
            raise RuntimeError("串口未打开")
        self._serial.write(text.encode("utf-8"))

    def _read_loop(self):
        while self._running:
            try:
                line = self._serial.readline()
            except (serial.SerialException, OSError) as exc:
                if self._running and self._on_error:
                    self._on_error("串口读取失败: %s" % exc)
                break
            if line:
                text = line.decode("utf-8", errors="replace")
                if self._on_data:
                    self._on_data(text)
