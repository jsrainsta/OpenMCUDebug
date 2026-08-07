"""日志解析模块。

解析 MCU 发来的文本协议行（见 docs/protocol.md），
提取级别标签，供界面着色显示。

协议格式: [INFO] 内容 | [DATA] 内容 | [ERROR] 内容
"""

import re

_TAG_RE = re.compile(r"^\[(INFO|DATA|ERROR)\]\s*(.*)$")

# 级别 -> 显示颜色（日志窗口使用，深色背景）
LEVEL_COLORS = {
    "INFO": "#3dce7a",
    "DATA": "#4aa3f0",
    "ERROR": "#e55d5d",
    None: "#c8c8c8",
}


def parse_line(line):
    """解析一行日志，返回 (level, content)。

    - level: "INFO" / "DATA" / "ERROR"，无标签时为 None
    - content: 去掉标签后的内容
    """
    line = line.rstrip("\r\n")
    match = _TAG_RE.match(line)
    if match:
        return match.group(1), match.group(2)
    return None, line


def color_for(level):
    """返回级别对应的显示颜色。"""
    return LEVEL_COLORS.get(level, LEVEL_COLORS[None])
