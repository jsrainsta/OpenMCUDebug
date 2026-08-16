<div align="center">

# 🛠️ MCU Debug Assistant

**面向嵌入式 MCU 开发的轻量级调试助手**

串口通信 · 实时日志查看 · 设备命令控制

A lightweight debugging assistant for embedded MCU development.

[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)]()
[![GUI](https://img.shields.io/badge/GUI-PyQt6-orange.svg)]()
[![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20Linux%20%7C%20macOS-lightgrey.svg)]()

来都来了，给个Star⭐吧~

</div>

---

## 📸 界面预览

![MCU Debug Assistant](docs/screenshot.png)

## ✨ 功能特性

- **串口连接**：自动检测 / 选择串口，波特率可设置（默认 115200），一键打开关闭
- **日志终端**：实时显示、自动滚动、一键清空，按 `[INFO]` / `[DATA]` / `[ERROR]` 分级着色
- **命令控制**：输入 `led on` 等文本命令直接下发，行尾可选（CRLF / LF / 无）
- **设备识别**：设备自动宣告身份（名称 / 版本），通道注册后实时显示数值
- **自动仪表盘**：设备只需在协议中描述显示方式（文本 / 仪表盘 / 实时曲线），PC 自动生成
- **会话记录与回放**：一键把接收数据记录为 CSV，离线回放进日志 / 设备面板 / 仪表盘，支持暂停与变速
- **参数调节面板**：设备注册 PID 等飞控参数后，PC 端分组编辑下发、回执反馈、本地预设保存/载入
- **MCU 端 SDK**：`Debug_Init()` / `Debug_Print()` / `Debug_Printf()` / 通道注册 / 参数注册，附 STM32 与 Quadcopter 完整示例
- **简单文本协议**：无需 JSON / 二进制协议，串口助手即可排查问题

## 🚀 快速开始

### PC 端

**双击 `start.bat` 一键启动**（Windows）；或手动：

```bash
pip install -r requirements.txt
python -m desktop.main
```

连接 STM32 后：点 **刷新** 选择串口 → 设置波特率 → **打开串口**，
即可实时查看 MCU 日志；在底部输入命令（如 `led on`）回车即可控制设备。

### MCU 端（STM32）

1. 将 `mcu-sdk/include` 与 `mcu-sdk/src` 加入工程编译
2. 实现 `Debug_UART_Send()`，用你的 UART 句柄发送：

```c
void Debug_UART_Send(const uint8_t *data, uint16_t len)
{
    HAL_UART_Transmit(&huart1, data, len, 100);
}
```

3. 串口初始化后调用 `Debug_Init()`，即可发送日志：

```c
Debug_Info("System Start");
Debug_Data("Temperature=%d", 25);
Debug_Error("Sensor Failed");
```

4. 注册数据通道并描述显示方式（PC 端自动生成仪表盘）：

```c
Debug_Device_Init("Quadcopter", "1.0");
Debug_Register_Channel(0, "Throttle", "u16", "us", DBG_VISUAL_GAUGE);
Debug_Register_Channel(1, "Roll",     "u16", "us", DBG_VISUAL_CHART);
Debug_Register_Channel(4, "Accel_X",  "i16", "raw", NULL);  // 文本显示

// 周期上报
Debug_Send_Val(0, throttle);
Debug_Send_Val_Float(3, 15.2f);
```

5. 命令接收（单字节中断 + 行缓冲）参考 `mcu-sdk/examples/stm32_example/main.c`

6. 注册飞控参数并处理 PC 下发（Stage 5，PC 端自动出现「参数」Tab）：

```c
Debug_Register_Param(0, "Roll_Kp", "f32", 0.0f, 10.0f, 1.5f, "Roll");
Debug_Register_Param(1, "Hover_Throttle", "u16", 800.0f, 2000.0f, 1200.0f, "Throttle");

// 命令接收处（收到一行 line 后）：
uint8_t id; float val;
if (Debug_Param_Parse(line, &id, &val)) {
    Apply_Param(id, val);            // 你自己的应用逻辑
    Debug_Param_Ack(id, 1, NULL);    // 回执，PC 端显示 ✓
}
```

7. PC 端「● 开始记录」把会话存为 CSV，之后可「▶ 回放…」离线复现任意一次调试过程

## 📡 通信协议

| 方向 | 格式 | 示例 |
|------|------|------|
| MCU → PC | `[TAG] 内容`（UTF-8，一行一条） | `[INFO] System Start` / `[DATA] Counter=10` |
| MCU → PC | `$DEV` 设备宣告 | `$DEV name=Quadcopter,ver=1.0` |
| MCU → PC | `$CH` 通道注册（可选 `visual`） | `$CH id=0,name=Throttle,type=u16,unit=us,visual=gauge` |
| MCU → PC | `$VAL` 数据更新 | `$VAL id=0,val=1500` |
| MCU → PC | `$P` 参数注册 / `$PV` 参数值 / `$PA` 下发回执 | `$P id=0,name=Roll_Kp,type=f32,min=0,max=10,val=1.5,group=Roll` |
| PC → MCU | `$PS` 参数下发 | `$PS id=0,val=2.0` |
| PC → MCU | 纯文本命令，一行一条 | `led on` / `motor 1000` / `pid kp 1.5` |

详细说明见 [docs/protocol.md](docs/protocol.md)。

## 📁 项目结构

```
desktop/            PC 端软件（Python + PyQt6 + pyserial）
  ├── main.py           入口
  ├── serial/           串口通信模块
  ├── parser/           日志解析模块
  ├── protocol/         设备协议解析（$DEV / $CH / $VAL / $P / $PV / $PA）
  ├── device/           设备模型与设备管理器
  ├── param/            参数模型与参数调节面板（Stage 5）
  ├── recorder/         会话记录（CSV）与离线回放（Stage 4）
  ├── visualization/    Dashboard 组件（文本 / 仪表盘 / 曲线）
  └── ui/               PyQt6 界面
mcu-sdk/            MCU 端 SDK（C）
  ├── include/          mcu_debug.h
  ├── src/              mcu_debug.c
  └── examples/         STM32 / Quadcopter 示例
docs/               协议文档、截图
tests/              无硬件测试（pyserial loop:// 虚拟串口）
```

## 🧪 测试

无需硬件，使用 pyserial 自带的 `loop://` 虚拟回路串口：

```bash
python -m tests.test_serial_manager   # 串口收发
python -m tests.test_parser           # 日志解析
python -m tests.test_protocol         # 设备/参数协议解析
python -m tests.test_device_manager   # 设备模型管理
python -m tests.test_param_manager    # 参数模型管理
python -m tests.test_recorder         # 会话记录与回放
python -m tests.test_dashboard        # 仪表盘组件
python -m tests.test_gui_smoke        # 界面冒烟（仪表盘 + 记录回放 + 参数面板）
```

## 🗺️ 路线图

| 版本 | 规划内容 |
|------|----------|
| v0.1 ✅ | 串口通信、日志查看、命令控制（Stage 1 MVP） |
| v0.2 ✅ | 标准化数据格式、设备模型（$DEV / $CH / $VAL） |
| v0.3 ✅ | 自动仪表盘（文本 / 仪表盘 / 实时曲线） |
| v0.4 ✅ | 数据保存与回放（CSV 记录 + 离线回放） |
| v0.5 ✅ | 参数调节面板（$P / $PV / $PS / $PA + 预设） |
| v1.0 | MCU SDK 完善、多设备支持、插件系统 |

## 📄 许可证

[MIT](LICENSE) © 2026 [jsrainsta](https://github.com/jsrainsta)
