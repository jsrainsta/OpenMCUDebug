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


def test_ch_with_scale():
    """Stage 6：$CH 携带 scale/offset/min/max 换算字段。"""
    kind, data = parse_line(
        "$CH id=4,name=Accel_X,type=i16,unit=g,scale=6.10352e-05,offset=0,min=-2,max=2")
    assert kind == "CH"
    assert data["scale"] == "6.10352e-05"
    assert data["offset"] == "0"
    assert data["min"] == "-2"
    assert data["max"] == "2"
    kind, data = parse_line("$CH id=0,name=Throttle,type=u16,unit=us")
    assert "scale" not in data, "无换算字段时不应出现 scale"
    print("PASS: CHANNEL_REGISTER 带物理量换算字段")


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


def test_param_register():
    """Stage 5：$P 参数注册。"""
    kind, data = parse_line(
        "$P id=0,name=Roll_Kp,type=f32,min=0,max=10,val=1.5,group=Roll")
    assert kind == "P", kind
    assert data["id"] == "0"
    assert data["name"] == "Roll_Kp"
    assert data["type"] == "f32"
    assert data["min"] == "0"
    assert data["max"] == "10"
    assert data["val"] == "1.5"
    assert data["group"] == "Roll"
    print("PASS: 参数注册 $P 解析")


def test_param_register_minimal():
    """$P 只带 id/name/type，min/max/val/group 可省。"""
    kind, data = parse_line("$P id=1,name=Hover_Throttle,type=u16")
    assert kind == "P"
    assert data["name"] == "Hover_Throttle"
    assert "min" not in data
    assert "val" not in data
    print("PASS: 参数注册最小字段")


def test_param_value():
    kind, data = parse_line("$PV id=0,val=2.0")
    assert kind == "PV", kind
    assert data["id"] == "0"
    assert data["val"] == "2.0"
    print("PASS: 参数值更新 $PV 解析")


def test_param_ack_ok():
    kind, data = parse_line("$PA id=0,ok=1")
    assert kind == "PA", kind
    assert data["id"] == "0"
    assert data["ok"] == "1"
    print("PASS: 参数回执 $PA ok")


def test_param_ack_fail():
    # 协议值不允许空格/逗号（与字符串通道一致），错误原因用单词/下划线
    kind, data = parse_line("$PA id=0,ok=0,msg=out_of_range")
    assert kind == "PA"
    assert data["ok"] == "0"
    assert data["msg"] == "out_of_range"
    print("PASS: 参数回执 $PA 失败带原因")


def test_param_prefix_not_confused():
    """$P 不能误匹配 $PV/$PA；$VAL 也不能误匹配 $PV。"""
    assert parse_line("$PV id=0,val=1")[0] == "PV"
    assert parse_line("$PA id=0,ok=1")[0] == "PA"
    assert parse_line("$VAL id=0,val=1")[0] == "VAL"
    print("PASS: $P/$PV/$PA/$VAL 前缀互不误判")


if __name__ == "__main__":
    test_dev()
    test_dev_no_version()
    test_ch()
    test_ch_no_unit()
    test_ch_with_visual()
    test_ch_with_scale()
    test_val()
    test_val_negative()
    test_val_float()
    test_stage1_line()
    test_plain_line()
    test_empty()
    test_partial()
    test_param_register()
    test_param_register_minimal()
    test_param_value()
    test_param_ack_ok()
    test_param_ack_fail()
    test_param_prefix_not_confused()
