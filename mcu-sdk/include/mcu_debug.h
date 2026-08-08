/**
 * @file mcu_debug.h
 * @brief MCU Debug Assistant 客户端 SDK 接口（STM32）
 *
 * 通信协议见 docs/protocol.md。
 *
 * Stage 1（日志）:
 *   MCU -> PC: [INFO] ... / [DATA] ... / [ERROR] ...
 *   PC  -> MCU: 纯文本命令，如 "led on"
 *
 * Stage 2（设备模型）:
 *   MCU -> PC: $DEV name=...,ver=...  /  $CH id=...,name=...,type=...,unit=...  /  $VAL id=...,val=...
 */
#ifndef MCU_DEBUG_H
#define MCU_DEBUG_H

#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

/* ======================== Stage 1：基础日志 ======================== */

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

/* ======================== Stage 2：设备模型 ======================== */

/**
 * @brief 宣告设备身份。
 * @param name    设备名称（如 "Quadcopter"）
 * @param version 固件版本（如 "1.0"，可为 NULL）
 *
 * 使用示例:
 *   Debug_Device_Init("Quadcopter", "1.0");
 *
 * 发送协议行:
 *   $DEV name=Quadcopter,ver=1.0
 */
void Debug_Device_Init(const char *name, const char *version);

/**
 * @brief 注册一个数据通道。
 * @param id   通道编号（0~255）
 * @param name 通道名称（如 "Roll"、"Battery"）
 * @param type 数据类型（"i8"/"i16"/"i32"/"u8"/"u16"/"u32"/"f32"/"str"）
 * @param unit 单位（如 "degree"、"volt"、"us"、"raw"，可为 NULL）
 *
 * 使用示例:
 *   Debug_Register_Channel(0, "Throttle", "u16", "us");
 *
 * 发送协议行:
 *   $CH id=0,name=Throttle,type=u16,unit=us
 */
void Debug_Register_Channel(uint8_t id, const char *name,
                            const char *type, const char *unit);

/**
 * @brief 发送一个整数通道值。
 * @param id    通道编号（0~255）
 * @param value 整数值（int32，传感器原始数据可直接传入）
 *
 * 使用示例:
 *   Debug_Send_Val(0, throttle);
 *
 * 发送协议行:
 *   $VAL id=0,val=1000
 */
void Debug_Send_Val(uint8_t id, int32_t value);

/**
 * @brief 发送一个浮点通道值。
 * @param id    通道编号（0~255）
 * @param value 浮点值
 *
 * 使用示例:
 *   Debug_Send_Val_Float(3, 15.2f);
 *
 * 发送协议行:
 *   $VAL id=3,val=15.2
 */
void Debug_Send_Val_Float(uint8_t id, float value);

/**
 * @brief 发送一个字符串通道值。
 * @param id    通道编号（0~255）
 * @param value 字符串值
 *
 * 使用示例:
 *   Debug_Send_Val_Str(5, "armed");
 *
 * 发送协议行:
 *   $VAL id=5,val=armed
 */
void Debug_Send_Val_Str(uint8_t id, const char *value);

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
