"""log_parser 单元测试。

运行方式（在项目根目录）::

    python -m tests.test_parser
"""

from desktop.parser.log_parser import color_for, parse_line


def test_parse_line():
    assert parse_line("[INFO] System Start") == ("INFO", "System Start")
    assert parse_line("[DATA] Counter=10") == ("DATA", "Counter=10")
    assert parse_line("[ERROR] Sensor Failed") == ("ERROR", "Sensor Failed")
    assert parse_line("[INFO] System Start\r\n") == ("INFO", "System Start")
    assert parse_line("plain text") == (None, "plain text")
    assert parse_line("[INFO] [DATA] nested") == ("INFO", "[DATA] nested")
    print("PASS: 解析测试通过")


def test_colors():
    assert color_for("INFO") == "#3dce7a"
    assert color_for("DATA") == "#4aa3f0"
    assert color_for("ERROR") == "#e55d5d"
    assert color_for(None) == "#c8c8c8"
    assert color_for("UNKNOWN") == "#c8c8c8"  # 未知级别回落为普通色
    print("PASS: 颜色测试通过")


if __name__ == "__main__":
    test_parse_line()
    test_colors()
