# 通信协议 v1

第一阶段采用简单文本协议，便于调试和移植。

## MCU -> PC（日志）

每行一条消息，格式：`[TAG] 内容`

| 标签    | 含义     | 界面显示颜色 |
|---------|----------|--------------|
| `[INFO]` | 普通信息 | 绿色         |
| `[DATA]` | 数据     | 蓝色         |
| `[ERROR]` | 错误    | 红色         |

无标签的行按普通日志显示（灰色）。

示例：

```
[INFO] System Start
[INFO] MPU6050 OK
[DATA] Counter=10
[ERROR] Sensor Failed
```

编码：UTF-8；行尾：`\n`（兼容 `\r\n`）。

## PC -> MCU（命令）

纯文本命令，一行一条，由 MCU 端自行解析：

```
led on
motor 1000
pid kp 1.5
sensor reset
```

行尾：默认 `\r\n`（PC 端界面可选 LF / CRLF / 无）。
MCU 端命令解析参考 `mcu-sdk/examples/stm32_example/main.c`。
