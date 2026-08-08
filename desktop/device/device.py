"""设备模型。

一个 Device 代表一个通过串口连接的 MCU 设备。
"""

from dataclasses import dataclass, field

from desktop.device.channel import Channel


@dataclass
class Device:
    name: str
    version: str = ""
    channels: dict = field(default_factory=dict)  # id(int) → Channel

    def add_channel(self, channel: Channel):
        self.channels[channel.id] = channel

    def get_channel(self, channel_id: int):
        return self.channels.get(channel_id)
