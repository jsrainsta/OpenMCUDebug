# STM32 示例工程

配合 STM32CubeMX 生成的 HAL 工程使用（Keil / IAR / CMake 均可）。

## 集成步骤

1. 把 `mcu-sdk/include` 加入头文件搜索路径，把 `mcu-sdk/src/mcu_debug.c`
   加入工程编译
2. 在你的工程中实现 `Debug_UART_Send()`，把数据交给 HAL 发送
   （见 `main.c` 中 `Debug_UART_Send` 的实现，串口句柄换成你自己的）
3. 串口初始化完成后调用 `Debug_Init()`，即可使用 `Debug_Info` /
   `Debug_Data` / `Debug_Error` / `Debug_Printf` 发送日志
4. 命令接收使用单字节中断 + 行缓冲（见 `main.c`），
   在 `HAL_UART_RxCpltCallback` 中按行解析命令

## 联调验证

上电后 PC 端（MCU Debug Assistant）应显示：

```
[INFO] System Start
[DATA] Temperature=25
```

PC 发送 `led on`，LED 点亮，并回显：

```
[INFO] LED ON
```

## 协议

收发格式见 `docs/protocol.md`。
