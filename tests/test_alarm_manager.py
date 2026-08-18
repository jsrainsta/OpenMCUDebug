"""阈值告警管理器单元测试（Stage 6 / v0.6）。

运行方式（在项目根目录）::

    python -m tests.test_alarm_manager
"""

from desktop.alarm.alarm_manager import AlarmManager


def test_alarm_enter_and_recover():
    alarms = AlarmManager()
    alarms.set_limit(0, 1100.0, 1900.0)   # 油门合理范围 us

    # 正常值：不告警
    assert alarms.check(0, 1500) == (False, False)
    # 越限：新进入
    assert alarms.check(0, 2500) == (True, True)
    # 持续越限：仍告警但不重复"进入"
    assert alarms.check(0, 2600) == (True, False)
    # 恢复
    assert alarms.check(0, 1500) == (False, False)
    # 再次越限：重新进入
    assert alarms.check(0, 800) == (True, True)
    print("PASS: 告警进入/持续/恢复状态机")


def test_alarm_single_side_limit():
    alarms = AlarmManager()
    alarms.set_limit(1, None, 3.5)   # 只限上限（如电压 ≤ 3.5V）
    assert alarms.check(1, 3.4) == (False, False)
    assert alarms.check(1, 3.6) == (True, True)

    alarms.set_limit(2, 20.0, None)  # 只限下限（如温度 ≥ 20℃）
    assert alarms.check(2, 25.0) == (False, False)
    assert alarms.check(2, 19.9) == (True, True)
    print("PASS: 单侧阈值（仅上限 / 仅下限）")


def test_alarm_boundary():
    alarms = AlarmManager()
    alarms.set_limit(0, 0.0, 100.0)
    assert alarms.check(0, 0.0) == (False, False), "等于下限不算越限"
    assert alarms.check(0, 100.0) == (False, False), "等于上限不算越限"
    print("PASS: 边界值等于阈值不告警")


def test_alarm_clear_limit():
    alarms = AlarmManager()
    alarms.set_limit(0, 0.0, 10.0)
    assert alarms.check(0, 99) == (True, True)
    alarms.set_limit(0, None, None)   # 清除限制
    assert alarms.check(0, 99) == (False, False)
    assert alarms.get_limit(0) is None
    print("PASS: 清除阈值后不再告警")


def test_alarm_non_numeric():
    alarms = AlarmManager()
    alarms.set_limit(0, 0.0, 10.0)
    assert alarms.check(0, "armed") == (False, False), "字符串值不告警"
    assert alarms.check(0, None) == (False, False), "None 不告警"
    # 无阈值的通道
    assert alarms.check(9, 12345) == (False, False)
    print("PASS: 字符串/None/无阈值通道不告警")


def test_alarm_clear():
    alarms = AlarmManager()
    alarms.set_limit(0, 0.0, 10.0)
    alarms.check(0, 99)               # 进入告警状态
    alarms.clear()
    assert alarms.get_limit(0) is None
    assert alarms.check(0, 99) == (False, False), "clear 后状态与阈值一并清空"
    print("PASS: clear 清空全部阈值与状态")


if __name__ == "__main__":
    test_alarm_enter_and_recover()
    test_alarm_single_side_limit()
    test_alarm_boundary()
    test_alarm_clear_limit()
    test_alarm_non_numeric()
    test_alarm_clear()
