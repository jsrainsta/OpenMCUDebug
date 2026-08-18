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
 *
 * Stage 3（可视化）:
 *   $CH 可选携带 visual 字段，PC 端据此自动生成仪表盘:
 *   $CH id=0,name=Throttle,type=u16,unit=us,visual=gauge
 *   $CH id=1,name=Roll,type=u16,unit=us,visual=chart
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

/* ======================== Stage 3：可视化类型 ======================== */

/** 通道可视化类型（Debug_Register_Channel 的 visual 参数，可为 NULL）。
 *  PC 端据此自动生成仪表盘组件，未知类型回退为文本显示。 */
#define DBG_VISUAL_TEXT   "text"    /* 普通数值显示（默认） */
#define DBG_VISUAL_GAUGE  "gauge"   /* 仪表盘：电压 / 电量 / 百分比 */
#define DBG_VISUAL_CHART  "chart"   /* 实时曲线：温度 / 速度 / 姿态 */

/* ======================== Stage 2：设备模型 ======================== *//**
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
 * @param id     通道编号（0~255）
 * @param name   通道名称（如 "Roll"、"Battery"）
 * @param type   数据类型（"i8"/"i16"/"i32"/"u8"/"u16"/"u32"/"f32"/"str"）
 * @param unit   单位（如 "degree"、"volt"、"us"、"raw"，可为 NULL）
 * @param visual 可视化类型（DBG_VISUAL_TEXT / _GAUGE / _CHART，可为 NULL）
 *
 * 使用示例:
 *   Debug_Register_Channel(0, "Throttle", "u16", "us", DBG_VISUAL_GAUGE);
 *   Debug_Register_Channel(1, "Roll",     "u16", "us", DBG_VISUAL_CHART);
 *
 * 发送协议行（visual 为 text 或 NULL 时省略该字段，保持兼容）:
 *   $CH id=0,name=Throttle,type=u16,unit=us,visual=gauge
 *   $CH id=1,name=Roll,type=u16,unit=us,visual=chart
 */
void Debug_Register_Channel(uint8_t id, const char *name,
                            const char *type, const char *unit,
                            const char *visual);

/**
 * @brief 注册一个带物理量换算的数据通道（Stage 6）。
 *
 * 除 Debug_Register_Channel 的参数外，额外描述原始值到物理量的换算:
 *
 *   物理量 = 原始值 × scale + offset
 *
 * @param id     通道编号（0~255）
 * @param name   通道名称
 * @param type   数据类型
 * @param unit   单位（如 "g"、"deg/s"、"m"、可为 NULL）
 * @param visual 可视化类型（可为 NULL）
 * @param scale  换算系数（如 MPU6050 加速度 1/16384 ≈ 0.000061，即 LSB → g）
 * @param offset 换算偏移（一般 0）
 * @param min    量程下限（仪表盘优先使用；与 max 相等时省略）
 * @param max    量程上限（如 ±2g → -2, 2）
 *
 * 使用示例:
 *   Debug_Register_Channel_Ex(4, "Accel_X", "i16", "g", NULL,
 *                             1.0f / 16384.0f, 0.0f, -2.0f, 2.0f);
 *
 * 发送协议行（scale=1 且 offset=0 且 min==max 时省略全部换算字段，
 * 输出与 Debug_Register_Channel 逐字节一致）:
 *   $CH id=4,name=Accel_X,type=i16,unit=g,scale=6.10352e-05,offset=0,min=-2,max=2
 */
void Debug_Register_Channel_Ex(uint8_t id, const char *name,
                               const char *type, const char *unit,
                               const char *visual,
                               float scale, float offset,
                               float min, float max);

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

/* ======================== Stage 5：参数调节 ======================== */

/**
 * @brief 注册一个可调参数。
 * @param id    参数编号（0~255）
 * @param name  参数名称（如 "Roll_Kp"）
 * @param type  数据类型描述（"f32" / "u16" 等，仅用于 PC 端显示与输入提示）
 * @param min   最小值；max 无限制时传 0 且 max=0（此时 min/max 字段省略）
 * @param max   最大值
 * @param val   当前值
 * @param group 分组名（如 "Roll"，可为 NULL 归入 PC 端默认组）
 *
 * 使用示例:
 *   Debug_Register_Param(0, "Roll_Kp", "f32", 0.0f, 10.0f, 1.5f, "Roll");
 *
 * 发送协议行:
 *   $P id=0,name=Roll_Kp,type=f32,min=0,max=10,val=1.5,group=Roll
 */
void Debug_Register_Param(uint8_t id, const char *name, const char *type,
                          float min, float max, float val, const char *group);

/**
 * @brief 上报参数当前值（$PV）。
 * 适合 MCU 内部修改参数后主动告知 PC，或在周期上报任务中刷新数值。
 *
 * 发送协议行:
 *   $PV id=0,val=1.8
 */
void Debug_Param_Update(uint8_t id, float val);

/**
 * @brief 发送参数下发回执（$PA）。
 * @param id  参数编号
 * @param ok  1=接受 0=拒绝
 * @param msg 拒绝原因（单词，不能含逗号/空格，可为 NULL）
 *
 * 发送协议行:
 *   $PA id=0,ok=1
 *   $PA id=0,ok=0,msg=out_of_range
 */
void Debug_Param_Ack(uint8_t id, uint8_t ok, const char *msg);

/**
 * @brief 解析 PC 下发的参数设置行（$PS id=..,val=..）。
 * @param line 收到的命令行（不含行尾）
 * @param id   输出参数编号
 * @param val  输出值
 * @return 1=命中 $PS 并解析成功，0=不是 $PS 行
 *
 * 用法（用户命令处理函数中）:
 *   uint8_t id; float val;
 *   if (Debug_Param_Parse(line, &id, &val)) {
 *       Apply_Param(id, val);
 *       Debug_Param_Ack(id, 1, NULL);
 *   }
 */
int Debug_Param_Parse(const char *line, uint8_t *id, float *val);

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
