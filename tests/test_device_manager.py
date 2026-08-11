"""设备管理器单元测试。

运行方式（在项目根目录）::

    python -m tests.test_device_manager
"""

from desktop.device.device_manager import DeviceManager


def test_device_registration():
    dm = DeviceManager()
    dm.process_message("DEV", {"name": "Quadcopter", "ver": "1.0"})
    assert dm.device is not None
    assert dm.device.name == "Quadcopter"
    assert dm.device.version == "1.0"
    print("PASS: 设备注册")


def test_channel_registration():
    dm = DeviceManager()
    dm.process_message("DEV", {"name": "Quadcopter"})
    dm.process_message("CH", {"id": "0", "name": "Throttle", "type": "u16", "unit": "us"})
    assert 0 in dm.device.channels
    ch = dm.device.get_channel(0)
    assert ch.name == "Throttle"
    assert ch.type == "u16"
    assert ch.unit == "us"
    print("PASS: 通道注册")


def test_channels_before_device():
    """通道在设备宣告之前到达（暂存后合并）。"""
    dm = DeviceManager()
    dm.process_message("CH", {"id": "0", "name": "Roll", "type": "i16", "unit": "degree"})
    assert dm.device is None
    assert 0 in dm._pending_channels

    dm.process_message("DEV", {"name": "Drone"})
    assert dm.device is not None
    ch = dm.device.get_channel(0)
    assert ch.name == "Roll"
    assert not dm._pending_channels  # 暂存队列已清空
    print("PASS: 通道早于设备到达")


def test_value_update():
    dm = DeviceManager()
    dm.process_message("DEV", {"name": "Quadcopter"})
    dm.process_message("CH", {"id": "0", "name": "Throttle", "type": "u16", "unit": "us"})
    dm.process_message("VAL", {"id": "0", "val": "1000"})

    ch = dm.device.get_channel(0)
    assert ch.value == 1000  # int 转换
    print("PASS: 通道值更新（int）")


def test_value_float():
    dm = DeviceManager()
    dm.process_message("DEV", {"name": "Test"})
    dm.process_message("CH", {"id": "0", "name": "Voltage", "type": "f32", "unit": "V"})
    dm.process_message("VAL", {"id": "0", "val": "11.8"})

    ch = dm.device.get_channel(0)
    assert ch.value == 11.8  # float 转换
    print("PASS: 通道值更新（float）")


def test_channel_visual():
    """Stage 3：visual 字段透传 + 非法值回退。"""
    dm = DeviceManager()
    dm.process_message("DEV", {"name": "Quadcopter"})
    dm.process_message("CH", {"id": "0", "name": "Throttle", "type": "u16", "unit": "us",
                              "visual": "gauge"})
    dm.process_message("CH", {"id": "1", "name": "Roll", "type": "i16", "unit": "degree",
                              "visual": "chart"})
    dm.process_message("CH", {"id": "2", "name": "Pressure", "type": "u32"})  # 无 visual
    dm.process_message("CH", {"id": "3", "name": "X", "type": "i16",
                              "visual": "hologram"})  # 未知类型
    assert dm.device.get_channel(0).visual == "gauge"
    assert dm.device.get_channel(1).visual == "chart"
    assert dm.device.get_channel(2).visual == "text", "缺省应为 text"
    assert dm.device.get_channel(3).visual == "text", "未知类型应回退 text"
    print("PASS: 通道可视化类型解析")


def test_device_reenrollment():
    """MCU 周期重发 $DEV 时，同名设备应保留已注册通道。"""
    dm = DeviceManager()
    dm.process_message("DEV", {"name": "FanController", "ver": "1.0"})
    dm.process_message("CH", {"id": "0", "name": "Switch", "type": "u8", "unit": ""})
    dm.process_message("CH", {"id": "1", "name": "ServoAngle", "type": "u8", "unit": "degree"})

    # 2s 后设备重复宣告（版本更新），通道不应丢失
    dm.process_message("DEV", {"name": "FanController", "ver": "1.1"})
    assert dm.device.version == "1.1"
    assert 0 in dm.device.channels and 1 in dm.device.channels, "重复宣告不应清空通道"

    # 通道重发 → 仍是同一对象，不产生重复
    dm.process_message("CH", {"id": "0", "name": "Switch", "type": "u8", "unit": ""})
    assert len(dm.device.channels) == 2, "通道重发不应重复注册"
    print("PASS: 设备重复宣告保留通道")


def test_reset():
    dm = DeviceManager()
    dm.process_message("DEV", {"name": "Quadcopter"})
    dm.process_message("CH", {"id": "0", "name": "Throttle", "type": "u16", "unit": "us"})
    dm.reset()
    assert dm.device is None
    assert not dm._pending_channels
    print("PASS: reset 清除设备")


def test_invalid_messages():
    dm = DeviceManager()
    dm.process_message("CH", {"id": "bad", "name": "X"})  # id 非数字 → 忽略
    dm.process_message("VAL", {"id": "0"})               # 缺 val → ch_id < 0 则忽略
    dm.process_message("VAL", {})                         # 空 data → 忽略
    dm.process_message(None, None)                         # None → 忽略
    print("PASS: 无效消息不崩溃")


if __name__ == "__main__":
    test_device_registration()
    test_channel_registration()
    test_channels_before_device()
    test_value_update()
    test_value_float()
    test_channel_visual()
    test_device_reenrollment()
    test_reset()
    test_invalid_messages()
