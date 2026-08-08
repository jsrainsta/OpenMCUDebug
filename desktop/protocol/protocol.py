"""Stage 2/3 协议解析器。

解析 MCU 发来的 $DEV / $CH / $VAL 协议行，返回结构化的消息，
供 DeviceManager / DataManager 消费。
非协议行原样透传，由 log_parser 处理。

协议格式（单行紧凑 key=value）::

    $DEV name=Quadcopter,ver=1.0
    $CH id=0,name=Throttle,type=u16,unit=us,visual=chart
    $VAL id=0,val=1000

Stage 3 起 $CH 可选携带 visual 字段（text/gauge/chart，默认 text），
解析器无需特殊处理——key=value 通配提取即可。其余字段向后兼容。
"""

import re

# ---- 正则 ----

_DEV_RE = re.compile(r"^\$DEV\b")
_CH_RE  = re.compile(r"^\$CH\b")
_VAL_RE = re.compile(r"^\$VAL\b")

# 提取 key=value（兼容逗号分隔和空格分隔，值可包含非分隔字符）
_KV_RE = re.compile(r"(\w[\w.]*)=([^, \t]+)")


def parse_line(line):
    """解析一行协议数据。

    Returns:
        (kind, data) — 其中 kind 为 "DEV" / "CH" / "VAL" / None。
        data 为解析出的键值对 dict，非协议行 data 为原始字符串（已去行尾）。
    """
    text = line.rstrip("\r\n")
    if not text:
        return None, text

    if _DEV_RE.match(text):
        return "DEV", _parse_kv(text)
    if _CH_RE.match(text):
        return "CH", _parse_kv(text)
    if _VAL_RE.match(text):
        return "VAL", _parse_kv(text)

    return None, text


def _parse_kv(raw):
    """从 "$DEV name=Quadcopter,ver=1.0" 提取 {"name":"Quadcopter","ver":"1.0"}。"""
    pairs = {}
    for match in _KV_RE.finditer(raw):
        pairs[match.group(1)] = match.group(2)
    return pairs
