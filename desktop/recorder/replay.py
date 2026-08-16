"""回放器：按录制时间戳把 CSV 中的行重新注入数据链路。

用单个 QTimer 轮询推进（避免为每一行创建定时器）：
每次 tick 把「已录制时间」前进 interval_ms × speed，
然后把所有时间戳 <= 当前录制时间的行一次性发出。

支持暂停 / 变速（0.5x ~ 4x）/ 停止；回放结束后发出 finished 信号。

测试可绕过 Qt 事件循环直接调用 advance()。
"""

import csv

from PyQt6.QtCore import QObject, QTimer, pyqtSignal


class ReplayPlayer(QObject):
    """CSV 会话回放器。

    用法::

        player = ReplayPlayer()
        player.line_ready.connect(on_line)   # 注入数据链路
        player.finished.connect(on_finish)
        player.load("session.csv")
        player.play()
    """

    line_ready = pyqtSignal(str)      # 一行录制数据
    finished = pyqtSignal()           # 全部播放完毕
    progress = pyqtSignal(int, int)   # (已播放行数, 总行数)

    DEFAULT_INTERVAL_MS = 40

    def __init__(self, interval_ms=DEFAULT_INTERVAL_MS, parent=None):
        super().__init__(parent)
        self._interval_ms = max(10, int(interval_ms))
        self._lines = []       # [(time_ms, line)]
        self._index = 0        # 下一个待发送的行下标
        self._elapsed = 0.0    # 已推进的录制时间（ms）
        self._speed = 1.0
        self._source = None
        self._timer = QTimer(self)
        self._timer.setInterval(self._interval_ms)
        self._timer.timeout.connect(self._tick)

    # ====== 状态 ======

    @property
    def is_playing(self):
        return self._timer.isActive()

    @property
    def speed(self):
        return self._speed

    def set_speed(self, speed):
        self._speed = max(0.1, float(speed))

    @property
    def line_count(self):
        return len(self._lines)

    @property
    def position(self):
        return self._index

    @property
    def source(self):
        return self._source

    # ====== 控制 ======

    def load(self, path):
        """载入 CSV 文件；time_ms 为毫秒，可带表头（忽略）。"""
        self.stop()
        self._lines = []
        with open(path, "r", encoding="utf-8", newline="") as f:
            reader = csv.reader(f)
            header = next(reader, None)
            if header and header[0].strip().lower() == "time_ms":
                pass  # 表头行，跳过
            elif header:
                self._append(header)
            for row in reader:
                self._append(row)
        self._index = 0
        self._elapsed = 0.0
        self._source = path
        return self

    def play(self):
        """开始回放（未载入数据或已在播放中则忽略）。"""
        if not self._lines or self._timer.isActive():
            return
        self._timer.start()

    def pause(self):
        self._timer.stop()

    def stop(self):
        self._timer.stop()
        self._index = 0
        self._elapsed = 0.0

    def advance(self, real_ms):
        """推进 real_ms（真实毫秒，已按速度折算）对应的录制时间。

        返回本次发出的行数；测试可直接调用，无需事件循环。
        播放完最后一行时停止定时器并发出 finished。
        """
        if self._index >= len(self._lines):
            return 0
        self._elapsed += real_ms * self._speed
        emitted = 0
        while (self._index < len(self._lines)
               and self._lines[self._index][0] <= self._elapsed):
            self.line_ready.emit(self._lines[self._index][1])
            self._index += 1
            emitted += 1
        self.progress.emit(self._index, len(self._lines))
        if self._index >= len(self._lines):
            self._timer.stop()
            self.finished.emit()
        return emitted

    # ====== 内部 ======

    def _append(self, row):
        if not row:
            return
        try:
            t = float(row[0])
        except (ValueError, IndexError):
            return
        line = row[1] if len(row) > 1 else ""
        self._lines.append((t, line))

    def _tick(self):
        self.advance(self._interval_ms)
