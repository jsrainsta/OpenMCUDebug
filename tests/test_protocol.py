"""协议解析器单元测试。

运行方式（在项目根目录）::

    python -m tests.test_protocol
"""

from desktop.protocol.protocol import parse_line


def test_dev():
    kind, data = parse_line("$DEV name=Quadcopter,ver=1.0")
    assert kind == "DEV", kind
    assert data["name"] == "Quadcopter"
    assert data["ver"] == "1.0"
    print("PASS: DEVICE_INFO 解析")


def test_dev_no_version():
    kind, data = parse_line("$DEV name=STM32")
    assert kind == "DEV"
    assert data["name"] == "STM32"
    assert "ver" not in data
    print("PASS: DEVICE_INFO 无版本号")


def test_ch():
    kind, data = parse_line("$CH id=0,name=Throttle,type=u16,unit=us")
    assert kind == "CH", kind
    assert data["id"] == "0"
    assert data["name"] == "Throttle"
    assert data["type"] == "u16"
    assert data["unit"] == "us"
    print("PASS: CHANNEL_REGISTER 解析")


def test_ch_no_unit():
    kind, data = parse_line("$CH id=1,name=Accel_X,type=i16")
    assert kind == "CH"
    assert "unit" not in data
    print("PASS: CHANNEL_REGISTER 无单位")


def test_ch_with_visual():
    """Stage 3：$CH 携带可视化类型。"""
    kind, data = parse_line("$CH id=0,name=Throttle,type=u16,unit=us,visual=gauge")
    assert kind == "CH"
    assert data["visual"] == "gauge"
    kind, data = parse_line("$CH id=1,name=Roll,type=i16,unit=degree,visual=chart")
    assert data["visual"] == "chart"
    kind, data = parse_line("$CH id=2,name=Status,type=str,visual=text")
    assert data["visual"] == "text"
    print("PASS: CHANNEL_REGISTER 带可视化类型")


def test_val():
    kind, data = parse_line("$VAL id=0,val=1000")
    assert kind == "VAL", kind
    assert data["id"] == "0"
    assert data["val"] == "1000"
    print("PASS: DATA_UPDATE 解析")


def test_val_negative():
    kind, data = parse_line("$VAL id=3,val=-512")
    assert kind == "VAL"
    assert data["val"] == "-512"
    print("PASS: DATA_UPDATE 负数值")


def test_val_float():
    kind, data = parse_line("$VAL id=1,val=15.2")
    assert kind == "VAL"
    assert data["val"] == "15.2"
    print("PASS: DATA_UPDATE 浮点数")


def test_stage1_line():
    """Stage 1 日志行不被当做协议行。"""
    kind, text = parse_line("[INFO] System Start")
    assert kind is None
    assert isinstance(text, str)
    print("PASS: Stage1 [INFO] 行透传")


def test_plain_line():
    """普通文本不被当做协议行。"""
    kind, text = parse_line("THR:1000")
    assert kind is None
    assert isinstance(text, str)
    print("PASS: 普通文本透传")


def test_empty():
    kind, text = parse_line("")
    assert kind is None
    print("PASS: 空行透传")


def test_partial():
    """非 $ 开头的 key=value 不做协议解析。"""
    kind, text = parse_line("key=value")
    assert kind is None
    assert text == "key=value"
    print("PASS: 非 $ 前缀不透传")


if __name__ == "__main__":
    test_dev()
    test_dev_no_version()
    test_ch()
    test_ch_no_unit()
    test_ch_with_visual()
    test_val()
    test_val_negative()
    test_val_float()
    test_stage1_line()
    test_plain_line()
    test_empty()
    test_partial()
