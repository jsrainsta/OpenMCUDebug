"""设备管理器。

集中管理当前连接的设备信息、通道注册和数值更新。
通过 PyQt 信号通知 UI，线程安全（信号跨线程）。
"""

from PyQt6.QtCore import QObject, pyqtSignal

from desktop.device.channel import Channel
from desktop.device.device import Device


class DeviceManager(QObject):
    """设备管理器。

    用法::

        dm = DeviceManager()
        dm.device_updated.connect(on_device)
        dm.channel_added.connect(on_channel)
        dm.value_updated.connect(on_value)
        dm.process_message("DEV", {"name": "Quadcopter", "ver": "1.0"})
        dm.process_message("CH", {"id": "0", "name": "Throttle", "type": "u16", "unit": "us"})
        dm.process_message("VAL", {"id": "0", "val": "1000"})
    """

    device_updated = pyqtSignal(str, str)   # (name, version)
    channel_added = pyqtSignal(object)       # (Channel)
    value_updated = pyqtSignal(int, str, object)  # (channel_id, raw_str, parsed_value)
    device_reset = pyqtSignal()              # 设备断开

    def __init__(self):
        super().__init__()
        self.device = None
        self._pending_channels = {}  # 连接前收到 $CH 的行暂存（几乎不会发生）

    def reset(self):
        self.device = None
        self._pending_channels.clear()
        self.device_reset.emit()

    def process_message(self, kind, data):
        if not data:
            return

        if kind == "DEV":
            self._handle_device(data)
        elif kind == "CH":
            self._handle_channel(data)
        elif kind == "VAL":
            self._handle_value(data)

    def _handle_device(self, data):
        name = data.get("name", "") or data.get("device", "")
        version = data.get("ver", "") or data.get("version", "")
        if not name:
            return
        # 同一设备重复宣告（MCU 周期重发注册信息）：保留已注册通道，仅更新版本
        if self.device is not None and self.device.name == name:
            self.device.version = version
            self.device_updated.emit(name, version)
            return
        self.device = Device(name=name, version=version)
        # 合并暂存通道
        for ch in self._pending_channels.values():
            self.device.add_channel(ch)
        self._pending_channels.clear()
        self.device_updated.emit(name, version)

    def _handle_channel(self, data):
        try:
            ch_id = int(data.get("id", -1))
        except (ValueError, TypeError):
            return
        if ch_id < 0:
            return
        # Stage 3：可视化类型，未知值回退为 text
        visual = data.get("visual", "text")
        if visual not in ("text", "gauge", "chart"):
            visual = "text"
        ch = Channel(
            id=ch_id,
            name=data.get("name", "?"),
            type=data.get("type", "i32"),
            unit=data.get("unit", ""),
            visual=visual,
        )
        if self.device:
            self.device.add_channel(ch)
        else:
            self._pending_channels[ch_id] = ch
        self.channel_added.emit(ch)

    def _handle_value(self, data):
        try:
            ch_id = int(data.get("id", -1))
            raw_val = data.get("val", data.get("value", ""))
        except (ValueError, TypeError):
            return
        if ch_id < 0:
            return
        parsed = self._coerce(raw_val)
        # 回写通道最新值
        if self.device:
            ch = self.device.get_channel(ch_id)
            if ch:
                ch.value = parsed
        self.value_updated.emit(ch_id, raw_val, parsed)

    def _coerce(self, raw):
        """把字符串值转为 Python 类型（int/float/str）。"""
        if not raw:
            return raw
        try:
            if "." in raw or "e" in raw.lower():
                return float(raw)
            return int(raw)
        except (ValueError, TypeError):
            return raw
