/**
 * @file main.c
 * @brief Quadcopter 集成 Stage 2 SDK 示例
 *
 * 展示将原 UartTask 的自由格式 snprintf 替换为 Stage 2 协议的方法。
 * 本文件仅为参考示例，不修改原 Quadcopter 项目。
 *
 * 原输出（Stage 1 自由格式）:
 *   THR:1000
 *   Accel:0,0,16384
 *   Gyro:0,0,0
 *   Mag:0,0,0
 *   Pre_RAW:0 Tem_RAW:0
 *
 * 改为 Stage 2/3 协议后:
 *   $DEV name=Quadcopter,ver=1.0          ← 上电发一次
 *   $CH id=0,name=Throttle,type=u16,unit=us,visual=gauge  ← 上电发一次
 *   $CH id=1,name=Roll,type=u16,unit=us,visual=chart      ← 上电发一次
 *   ...（共 15 个通道）
 *   $VAL id=0,val=1000                    ← 每 500ms
 *   $VAL id=1,val=512                     ← 每 500ms
 *   ...
 *
 * Stage 3（可视化）:
 *   通道注册时通过 visual 参数描述显示方式，PC 端自动生成仪表盘:
 *   - Throttle  → 仪表盘（油门位置）
 *   - Roll/Pitch/Yaw → 实时曲线（姿态）
 *   - Temperature → 实时曲线
 *   - 其余通道  → 文本显示
 *
 * 集成步骤:
 *   1. 把 mcu-sdk/include 与 mcu-sdk/src 加入 Quadcopter 工程编译
 *   2. 在工程中实现 Debug_UART_Send（即已有的 HAL_UART_Transmit）
 *   3. 替换 UartTask 为下面的实现
 *   4. PC 端打开串口后自动显示设备名、15 个通道，并自动生成仪表盘
 */
#include "mcu_debug.h"
#include "main.h"    /* CubeMX 生成 */
#include "bsp.h"     /* Quadcopter BSP */
#include "ucos_ii.h"
#include <string.h>

extern UART_HandleTypeDef huart1;

/* 底层发送实现 */
void Debug_UART_Send(const uint8_t *data, uint16_t len)
{
    HAL_UART_Transmit(&huart1, data, len, 100);
}

/* ====================== 注册阶段（上电执行一次） ====================== */

static void Quadcopter_Register_Channels(void)
{
    Debug_Device_Init("Quadcopter", "1.0");

    /* 遥控通道：油门用仪表盘，姿态角用实时曲线 */
    Debug_Register_Channel(0, "Throttle", "u16", "us", DBG_VISUAL_GAUGE);
    Debug_Register_Channel(1, "Roll",     "u16", "us", DBG_VISUAL_CHART);
    Debug_Register_Channel(2, "Pitch",    "u16", "us", DBG_VISUAL_CHART);
    Debug_Register_Channel(3, "Yaw",      "u16", "us", DBG_VISUAL_CHART);

    /* 加速度计（原始值，LSB） */
    Debug_Register_Channel(4, "Accel_X", "i16", "raw", NULL);
    Debug_Register_Channel(5, "Accel_Y", "i16", "raw", NULL);
    Debug_Register_Channel(6, "Accel_Z", "i16", "raw", NULL);

    /* 陀螺仪（原始值，LSB） */
    Debug_Register_Channel(7, "Gyro_X", "i16", "raw", NULL);
    Debug_Register_Channel(8, "Gyro_Y", "i16", "raw", NULL);
    Debug_Register_Channel(9, "Gyro_Z", "i16", "raw", NULL);

    /* 磁力计（原始值） */
    Debug_Register_Channel(10, "Mag_X", "i16", "raw", NULL);
    Debug_Register_Channel(11, "Mag_Y", "i16", "raw", NULL);
    Debug_Register_Channel(12, "Mag_Z", "i16", "raw", NULL);

    /* 气压计文本显示 + 温度实时曲线 */
    Debug_Register_Channel(13, "Pressure",    "u32", "raw", NULL);
    Debug_Register_Channel(14, "Temperature", "u32", "raw", DBG_VISUAL_CHART);
}

/* ====================== 数据上报任务（每 500ms） ====================== */

#define UART_TASK_STK_SIZE  384
#define UART_TASK_PRIO      9

static OS_STK UartTaskStk[UART_TASK_STK_SIZE];

void UartTask(void *p_arg)
{
    OS_CPU_SR cpu_sr = 0;
    int16_t ax, ay, az;
    int16_t gx, gy, gz;
    int16_t mx, my, mz;
    uint32_t p_raw, t_raw;
    uint16_t throttle, roll, pitch, yaw;

    (void)p_arg;

    /* 上电后告知 PC 设备信息 + 注册全部通道 */
    Quadcopter_Register_Channels();

    while (1)
    {
        OS_ENTER_CRITICAL();
        ax = Accel_X_RAW;  ay = Accel_Y_RAW;  az = Accel_Z_RAW;
        gx = Gyro_X_RAW;   gy = Gyro_Y_RAW;   gz = Gyro_Z_RAW;
        mx = Mag_X_RAW;    my = Mag_Y_RAW;    mz = Mag_Z_RAW;
        p_raw = D1_Pressure_RAW;
        t_raw = D2_Temperature_RAW;
        throttle = PPM_Values[2];
        roll     = PPM_Values[0];
        pitch    = PPM_Values[1];
        yaw      = PPM_Values[3];
        OS_EXIT_CRITICAL();

        /* 所有数据走 Stage 2 协议 */
        Debug_Send_Val(0, throttle);
        Debug_Send_Val(1, roll);
        Debug_Send_Val(2, pitch);
        Debug_Send_Val(3, yaw);

        Debug_Send_Val(4, ax);
        Debug_Send_Val(5, ay);
        Debug_Send_Val(6, az);

        Debug_Send_Val(7, gx);
        Debug_Send_Val(8, gy);
        Debug_Send_Val(9, gz);

        Debug_Send_Val(10, mx);
        Debug_Send_Val(11, my);
        Debug_Send_Val(12, mz);

        Debug_Send_Val(13, (int32_t)p_raw);
        Debug_Send_Val(14, (int32_t)t_raw);

        OSTimeDlyHMSM(0, 0, 0, 500);
    }
}
