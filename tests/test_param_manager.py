"""参数管理器单元测试（Stage 5 / v0.5）。

覆盖：参数注册（含周期重发幂等）、值更新、下发回执、reset、异常容错。

运行方式（在项目根目录）::

    python -m tests.test_param_manager
"""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication

_app = QApplication.instance() or QApplication([])

from desktop.param.param_manager import Param, ParamManager


def test_param_register():
    pm = ParamManager()
    events = []
    pm.param_added.connect(lambda p: events.append(("added", p)))
    pm.param_value_updated.connect(lambda i, r, v: events.append(("updated", i, v)))

    pm.process_message("P", {"id": "0", "name": "Roll_Kp", "type": "f32",
                             "min": "0", "max": "10", "val": "1.5",
                             "group": "Roll"})
    assert 0 in pm.params
    p = pm.get(0)
    assert p.name == "Roll_Kp"
    assert p.type == "f32"
    assert p.minimum == 0.0
    assert p.maximum == 10.0
    assert p.value == 1.5
    assert p.group == "Roll"
    assert events == [("added", p)], "首次注册应触发 param_added"
    print("PASS: 参数注册（含 min/max/val 解析）")


def test_param_reregister_idempotent():
    """MCU 周期重发 $P：不重复新增，仅更新元信息/值。"""
    pm = ParamManager()
    added = []
    pm.param_added.connect(added.append)
    pm.process_message("P", {"id": "0", "name": "Roll_Kp", "type": "f32",
                             "min": "0", "max": "10", "val": "1.5"})
    pm.process_message("P", {"id": "0", "name": "Roll_Kp", "type": "f32",
                             "min": "0", "max": "10", "val": "1.8"})
    assert len(added) == 1, "重复注册不应触发 param_added"
    assert len(pm.params) == 1
    assert pm.get(0).value == 1.8, "重复注册应更新值"
    print("PASS: 参数周期重发幂等（按 id 去重）")


def test_param_value_update():
    pm = ParamManager()
    pm.process_message("P", {"id": "1", "name": "Hover", "type": "u16", "val": "1200"})
    got = []
    pm.param_value_updated.connect(lambda i, r, v: got.append((i, r, v)))
    pm.process_message("PV", {"id": "1", "val": "1300"})
    assert pm.get(1).value == 1300
    assert got == [(1, "1300", 1300)]
    # 未注册的参数值更新：不崩溃，仍发信号
    pm.process_message("PV", {"id": "99", "val": "1.0"})
    print("PASS: 参数值更新 $PV")


def test_param_ack():
    pm = ParamManager()
    got = []
    pm.param_acked.connect(lambda i, ok, msg: got.append((i, ok, msg)))
    pm.process_message("PA", {"id": "0", "ok": "1"})
    pm.process_message("PA", {"id": "0", "ok": "0", "msg": "out_of_range"})
    assert got == [(0, True, ""), (0, False, "out_of_range")]
    print("PASS: 参数回执 $PA（成功/失败带原因）")


def test_param_reset():
    pm = ParamManager()
    pm.process_message("P", {"id": "0", "name": "Kp", "type": "f32", "val": "1"})
    resets = []
    pm.param_reset.connect(lambda: resets.append(True))
    pm.reset()
    assert pm.params == {}
    assert resets == [True]
    print("PASS: reset 清除全部参数")


def test_param_bad_input():
    """无效输入静默容错，不崩溃。"""
    pm = ParamManager()
    pm.process_message("P", {})
    pm.process_message("P", {"id": "abc", "name": "x"})
    pm.process_message("P", {"id": "-1", "name": "x"})
    pm.process_message("PV", {"id": "x", "val": "1"})
    pm.process_message("PA", {"id": "x"})
    pm.process_message(None, None)
    assert pm.params == {}
    print("PASS: 参数无效输入容错")


if __name__ == "__main__":
    test_param_register()
    test_param_reregister_idempotent()
    test_param_value_update()
    test_param_ack()
    test_param_reset()
    test_param_bad_input()
