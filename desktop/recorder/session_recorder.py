"""会话记录器：把接收到的每一行数据连同相对时间戳写入 CSV。

格式（CSV，首行表头）::

    time_ms,line
    0.0,[INFO] System Start
    12.4,$DEV name=Quadcopter,ver=1.0
    512.3,$VAL id=0,val=1500

line 字段经 csv 模块转义，可安全包含逗号 / 引号 / 换行。
回放时按 time_ms 的时间差重新注入数据链路，即可离线复现整个会话
（日志着色、设备面板、仪表盘全部照常工作）。

记录发生在主线程的数据路由处（_on_data），无需额外线程。
"""

import csv
import time


class SessionRecorder:
    """CSV 会话记录器。

    用法::

        rec = SessionRecorder()
        rec.start("session.csv")
        rec.record("$VAL id=0,val=1500")
        rec.stop()
    """

    def __init__(self, path=None):
        self._path = None
        self._file = None
        self._writer = None
        self._started_at = None
        if path:
            self.start(path)

    def start(self, path):
        """开始记录到 path（自动覆盖旧文件）。"""
        self.stop()
        self._path = path
        self._file = open(path, "w", newline="", encoding="utf-8")
        self._writer = csv.writer(self._file)
        self._writer.writerow(["time_ms", "line"])
        self._started_at = time.monotonic()
        return self

    def record(self, line):
        """记录一行（带相对时间戳）。未在记录中时静默忽略。"""
        if self._writer is None:
            return False
        elapsed = (time.monotonic() - self._started_at) * 1000.0
        self._writer.writerow(["%.1f" % elapsed, line])
        return True

    def flush(self):
        if self._file is not None:
            self._file.flush()

    def stop(self):
        """停止并关闭文件；可安全重复调用。"""
        if self._file is not None:
            self._file.close()
            self._file = None
            self._writer = None
            self._started_at = None

    @property
    def is_recording(self):
        return self._writer is not None

    @property
    def path(self):
        return self._path

    def __del__(self):
        try:
            self.stop()
        except Exception:
            pass
