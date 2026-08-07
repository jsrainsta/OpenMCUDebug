/**
 * @file mcu_debug.h
 * @brief MCU Debug Assistant 客户端 SDK 接口（STM32）
 *
 * 通信协议见 docs/protocol.md：
 *   MCU -> PC: [INFO] ... / [DATA] ... / [ERROR] ...
 *   PC  -> MCU: 纯文本命令，如 "led on"
 */
#ifndef MCU_DEBUG_H
#define MCU_DEBUG_H

#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

/** 初始化调试模块。 */
void Debug_Init(void);

/** 发送一行消息（自动补 \r\n）。 */
void Debug_Print(const char *msg);

/** 格式化输出一行（自动补 \r\n）。 */
void Debug_Printf(const char *fmt, ...);

/* 按级别输出的便捷宏，自动带上协议标签 */
#define Debug_Info(msg)    Debug_Printf("[INFO] %s", msg)
#define Debug_Data(...)    Debug_Printf("[DATA] " __VA_ARGS__)
#define Debug_Error(...)   Debug_Printf("[ERROR] " __VA_ARGS__)

/**
 * 底层串口发送函数。
 *
 * 用户必须在自己的工程中实现本函数（覆盖 mcu_debug.c 里的弱定义），
 * 例如通过 STM32 HAL 发送：HAL_UART_Transmit(&huart1, data, len, 100);
 */
void Debug_UART_Send(const uint8_t *data, uint16_t len);

#ifdef __cplusplus
}
#endif

#endif /* MCU_DEBUG_H */
