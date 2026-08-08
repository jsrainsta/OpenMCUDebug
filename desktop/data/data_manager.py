"""数据管理器。

保存所有通道的当前值，提供查询接口。
后续 Stage 3（Dashboard / 曲线）将以此模块为数据源。
"""


class DataManager:
    """轻量级当前数据快照。

    用法::

        dm = DataManager()
        dm.update(0, 1000)
        dm.update(1, 16384)
        dm.get(0)  # → 1000
    """

    def __init__(self):
        self._values = {}  # channel_id → value

    def update(self, channel_id, value):
        self._values[channel_id] = value

    def get(self, channel_id):
        return self._values.get(channel_id)

    def all_values(self):
        return dict(self._values)

    def reset(self):
        self._values.clear()
