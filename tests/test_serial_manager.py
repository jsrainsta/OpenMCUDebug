"""SerialManager 无硬件回路测试。

利用 pyserial 自带的 loop:// 虚拟串口：写入的数据会被原样读回，
无需真实硬件即可验证打开、收发、关闭逻辑。

运行方式（在项目根目录）::

    python -m tests.test_serial_manager
"""

import threading

from desktop.serial.serial_manager import SerialManager


def test_loopback():
    received = []
    done = threading.Event()

    def on_data(line):
        received.append(line)
        if "PING" in line:
            done.set()

    manager = SerialManager(on_data=on_data)
    manager.open("loop://", 115200)
    try:
        manager.send("PING 1\n")
        assert done.wait(timeout=3), "未在 3 秒内收到回路返回的数据"

        manager.send("[INFO] System Start\r\n")
        assert done.wait(timeout=3), "第二次发送后接收超时"
    finally:
        manager.close()

    assert received == ["PING 1\n", "[INFO] System Start\r\n"], received
    assert not manager.is_open(), "close 后串口应已关闭"

    # 关闭状态下发送应当报错
    try:
        manager.send("x")
    except RuntimeError:
        pass
    else:
        raise AssertionError("串口关闭后 send 应当抛出 RuntimeError")

    print("PASS: 回路收发测试通过")


if __name__ == "__main__":
    test_loopback()
