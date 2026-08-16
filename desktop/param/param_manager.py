"""参数管理器（Stage 5 / v0.5）。

管理 MCU 注册的参数（$P）、参数值更新（$PV）与下发回执（$PA），
通过 PyQt 信号通知 UI（参数面板）。线程安全（信号跨线程）。

与 DeviceManager 同构：周期重发注册幂等（按 id 去重）、
异常输入静默容错。参数与设备解耦——MCU 可以只注册参数不宣告设备。
"""

from dataclasses import dataclass, field
from typing import Any, Optional

from PyQt6.QtCore import QObject, pyqtSignal


@dataclass
class Param:
    """一个可调节参数。

    字段对应协议 $P id=..,name=..,type=..,min=..,max=..,val=..,group=..，
    min / max / group 可选。
    """

    id: int
    name: str
    type: str = "f32"
    minimum: Optional[float] = None
    maximum: Optional[float] = None
    value: Any = None          # 最新值（int/float/str）
    group: str = ""


class ParamManager(QObject):
    """参数管理器。

    用法::

        pm = ParamManager()
        pm.param_added.connect(on_param)
        pm.process_message("P", {"id": "0", "name": "Roll_Kp", "type": "f32",
                                 "min": "0", "max": "10", "val": "1.5"})
        pm.process_message("PV", {"id": "0", "val": "2.0"})
        pm.process_message("PA", {"id": "0", "ok": "1"})
    """

    param_added = pyqtSignal(object)            # (Param)
    param_value_updated = pyqtSignal(int, str, object)  # (id, raw_str, parsed_value)
    param_acked = pyqtSignal(int, bool, str)    # (id, ok, msg)
    param_reset = pyqtSignal()                  # 清除全部参数

    def __init__(self):
        super().__init__()
        self.params = {}   # id -> Param

    def reset(self):
        self.params.clear()
        self.param_reset.emit()

    def get(self, param_id):
        return self.params.get(param_id)

    def process_message(self, kind, data):
        if not data:
            return
        if kind == "P":
            self._handle_register(data)
        elif kind == "PV":
            self._handle_value(data)
        elif kind == "PA":
            self._handle_ack(data)

    def _handle_register(self, data):
        try:
            param_id = int(data.get("id", -1))
        except (ValueError, TypeError):
            return
        if param_id < 0:
            return
        name = data.get("name", "?")
        minimum = self._opt_float(data.get("min"))
        maximum = self._opt_float(data.get("max"))
        raw_val = data.get("val", data.get("value", ""))

        param = self.params.get(param_id)
        if param is None:
            param = Param(
                id=param_id,
                name=name,
                type=data.get("type", "f32"),
                minimum=minimum,
                maximum=maximum,
                value=self._coerce(raw_val) if raw_val != "" else None,
                group=data.get("group", ""),
            )
            self.params[param_id] = param
            self.param_added.emit(param)
        else:
            # 周期重发注册：更新元信息，保留（或更新）当前值
            param.name = name
            param.type = data.get("type", param.type)
            param.minimum = minimum
            param.maximum = maximum
            param.group = data.get("group", param.group)
            if raw_val != "":
                param.value = self._coerce(raw_val)
            self.param_value_updated.emit(param_id, raw_val, param.value)

    def _handle_value(self, data):
        try:
            param_id = int(data.get("id", -1))
        except (ValueError, TypeError):
            return
        if param_id < 0:
            return
        raw_val = data.get("val", data.get("value", ""))
        parsed = self._coerce(raw_val)
        param = self.params.get(param_id)
        if param is not None:
            param.value = parsed
        self.param_value_updated.emit(param_id, raw_val, parsed)

    def _handle_ack(self, data):
        try:
            param_id = int(data.get("id", -1))
        except (ValueError, TypeError):
            return
        if param_id < 0:
            return
        ok = data.get("ok", "").lower() in ("1", "true", "ok", "yes")
        msg = data.get("msg", "")
        self.param_acked.emit(param_id, ok, msg)

    @staticmethod
    def _opt_float(raw):
        if raw in (None, ""):
            return None
        try:
            return float(raw)
        except (ValueError, TypeError):
            return None

    @staticmethod
    def _coerce(raw):
        if not raw:
            return raw
        try:
            if "." in raw or "e" in raw.lower():
                return float(raw)
            return int(raw)
        except (ValueError, TypeError):
            return raw
