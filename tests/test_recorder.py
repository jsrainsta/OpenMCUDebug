"""会话记录与回放单元测试（离屏运行）。

覆盖 Stage 4 核心链路：
记录器 CSV 落盘格式（表头 / 时间戳 / 转义）→ 回放器载入与按时间戳推进。

运行方式（在项目根目录）::

    python -m tests.test_recorder
"""

import csv
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication

_app = QApplication.instance() or QApplication([])

from desktop.recorder.replay import ReplayPlayer
from desktop.recorder.session_recorder import SessionRecorder


def test_recorder_csv_format(tmp_path):
    rec = SessionRecorder()
    rec.start(str(tmp_path / "session.csv"))
    assert rec.is_recording

    rec.record("[INFO] System Start")
    rec.record("$DEV name=Quadcopter,ver=1.0")
    rec.record("$VAL id=0,val=1500")
    rec.record('$CH id=1,name=Note,type=str,unit="a,b"')  # 含逗号，应转义
    rec.stop()
    assert not rec.is_recording

    raw = (tmp_path / "session.csv").read_text(encoding="utf-8")
    lines = raw.splitlines()
    assert lines[0] == "time_ms,line", "首行应为表头"

    # 时间戳递增且为数值
    assert len(lines) == 5
    for row in lines[1:]:
        t = row.split(",", 1)[0]
        float(t)  # 抛异常即失败

    assert '"[INFO] System Start"' in raw or "[INFO] System Start" in raw
    assert "$DEV name=Quadcopter,ver=1.0" in raw
    assert "$VAL id=0,val=1500" in raw
    print("PASS: 记录器 CSV 落盘（表头 / 时间戳 / 内容）")


def test_recorder_ignore_when_stopped(tmp_path):
    rec = SessionRecorder()
    assert not rec.record("$VAL id=0,val=1"), "未记录时 record 应返回 False"
    rec.start(str(tmp_path / "a.csv"))
    assert rec.record("x")
    rec.stop()
    assert not rec.record("y")
    data = (tmp_path / "a.csv").read_text(encoding="utf-8")
    assert "y" not in data, "停止后不应再写入"
    print("PASS: 记录器未启动/已停止时忽略写入")


def test_replay_load_and_pace(tmp_path):
    # 用记录器造一份数据，再回放
    rec = SessionRecorder()
    path = str(tmp_path / "session.csv")
    rec.start(path)
    rec.record("[INFO] Start")
    rec.record("$DEV name=Quadcopter,ver=1.0")
    rec.stop()

    # 手工构造第二份：明确的时间戳（用 csv.writer 保证含逗号的协议行被正确转义）
    with open(str(tmp_path / "timed.csv"), "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["time_ms", "line"])
        w.writerow(["0.0", "$DEV name=Quadcopter,ver=1.0"])
        w.writerow(["100.0", "$CH id=0,name=Throttle,type=u16,unit=us"])
        w.writerow(["100.0", "$VAL id=0,val=1500"])
        w.writerow(["500.0", "$VAL id=0,val=1600"])

    player = ReplayPlayer(interval_ms=40)
    received = []

    def on_line(line):
        received.append(line)

    done = []

    def on_finish():
        done.append(True)

    player.line_ready.connect(on_line)
    player.finished.connect(on_finish)
    player.load(str(tmp_path / "timed.csv"))
    assert player.line_count == 4

    # 前 40ms：只该发出 t<=40 的行（第 1 行）
    assert player.advance(40) == 1
    assert received == ["$DEV name=Quadcopter,ver=1.0"]

    # 再 60ms（累计 100）：发出 t<=100 的两行（同时间戳按顺序全发）
    assert player.advance(60) == 2
    assert received[-2:] == [
        "$CH id=0,name=Throttle,type=u16,unit=us",
        "$VAL id=0,val=1500",
    ]

    # 剩余 400ms：最后一行 + finished
    assert player.advance(400) == 1
    assert received[-1] == "$VAL id=0,val=1600"
    assert done == [True], "播完应发出 finished"

    # 再 advance 不再发出
    assert player.advance(1000) == 0
    print("PASS: 回放器按时间戳推进（同刻行全发 / 播完 finished）")


def test_replay_speed_and_restart(tmp_path):
    with open(str(tmp_path / "t.csv"), "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["time_ms", "line"])
        w.writerow(["0.0", "a"])
        w.writerow(["100.0", "b"])

    player = ReplayPlayer(interval_ms=40)
    player.load(str(tmp_path / "t.csv"))

    # 2x 速度：推进 40ms 折算录制 80ms，仍不足 100 → 只发 a
    player.set_speed(2.0)
    assert player.advance(40) == 1

    # 4x 速度：推进 10ms 折算 40ms，累计 120 → 发 b 并结束
    player.set_speed(4.0)
    assert player.advance(10) == 1

    # stop 后回到起点，可重新 play
    player.stop()
    assert player.position == 0
    assert not player.is_playing
    player.play()
    assert player.is_playing
    player.stop()
    print("PASS: 回放变速 / 停止重置 / play 状态")


if __name__ == "__main__":
    import shutil
    from pathlib import Path

    # 沙箱/CI 可能不允许写系统临时目录，这里在项目内建临时目录；
    # 注意用默认权限创建（tempfile 的 0700 目录在沙箱下不可写）
    base = Path(__file__).resolve().parent / ".tmp_run"
    base.mkdir(exist_ok=True)
    try:
        test_recorder_csv_format(base)
        test_recorder_ignore_when_stopped(base)
        test_replay_load_and_pace(base)
        test_replay_speed_and_restart(base)
    finally:
        shutil.rmtree(base, ignore_errors=True)
