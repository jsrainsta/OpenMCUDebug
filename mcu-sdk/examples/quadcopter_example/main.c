/**
 * @file main.c
 * @brief Quadcopter 集成 Stage 2/3/5 SDK 示例
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
 * Stage 5（参数调节）:
 *   注册 PID 等飞控参数（$P），PC 端「参数」Tab 可分组编辑并下发;
 *   PC 下发 $PS 行后由 Quadcopter_Handle_Command() 解析应用并回执 $PA。
 *
 * 集成步骤:
 *   1. 把 mcu-sdk/include 与 mcu-sdk/src 加入 Quadcopter 工程编译
 *   2. 在工程中实现 Debug_UART_Send（即已有的 HAL_UART_Transmit）
 *   3. 替换 UartTask 为下面的实现
 *   4. PC 端打开串口后自动显示设备名、15 个通道，并自动生成仪表盘
 *   5. 在工程原有的命令接收路径（收到一行后）调用 Quadcopter_Handle_Command
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

    /* 加速度计：MPU6050 ±2g 满量程，16384 LSB/g → 显示为 g */
    Debug_Register_Channel_Ex(4, "Accel_X", "i16", "g", NULL,
                              1.0f / 16384.0f, 0.0f, -2.0f, 2.0f);
    Debug_Register_Channel_Ex(5, "Accel_Y", "i16", "g", NULL,
                              1.0f / 16384.0f, 0.0f, -2.0f, 2.0f);
    Debug_Register_Channel_Ex(6, "Accel_Z", "i16", "g", NULL,
                              1.0f / 16384.0f, 0.0f, -2.0f, 2.0f);

    /* 陀螺仪：±250°/s，131 LSB/(°/s) → 显示为 deg/s */
    Debug_Register_Channel_Ex(7, "Gyro_X", "i16", "deg/s", NULL,
                              1.0f / 131.0f, 0.0f, -250.0f, 250.0f);
    Debug_Register_Channel_Ex(8, "Gyro_Y", "i16", "deg/s", NULL,
                              1.0f / 131.0f, 0.0f, -250.0f, 250.0f);
    Debug_Register_Channel_Ex(9, "Gyro_Z", "i16", "deg/s", NULL,
                              1.0f / 131.0f, 0.0f, -250.0f, 250.0f);

    /* 磁力计（原始值） */
    Debug_Register_Channel(10, "Mag_X", "i16", "raw", NULL);
    Debug_Register_Channel(11, "Mag_Y", "i16", "raw", NULL);
    Debug_Register_Channel(12, "Mag_Z", "i16", "raw", NULL);

    /* 气压计文本显示 + 温度实时曲线
     * 注：MS5611 的原始值→物理量换算非纯线性，示例中保持 raw，
     * 如固件已算出气压/温度可直接用 Debug_Send_Val_Float 上报。 */
    Debug_Register_Channel(13, "Pressure",    "u32", "raw", NULL);
    Debug_Register_Channel(14, "Temperature", "u32", "raw", DBG_VISUAL_CHART);
}

/* ====================== Stage 5：飞控参数（PID 等） ====================== */

/* 示例飞控参数（实际工程中替换为你的全局变量） */
static float g_roll_kp = 1.5f, g_roll_ki = 0.02f, g_roll_kd = 0.1f;
static float g_pitch_kp = 1.5f, g_pitch_ki = 0.02f, g_pitch_kd = 0.1f;
static float g_yaw_kp = 2.0f, g_yaw_ki = 0.01f, g_yaw_kd = 0.0f;
static uint16_t g_hover_throttle = 1200;   /* 悬停油门（us） */

static void Quadcopter_Register_Params(void)
{
    /* min == max（0/0）时省略范围字段，表示无限制 */
    Debug_Register_Param(0,  "Roll_Kp",  "f32", 0.0f, 10.0f,  g_roll_kp,  "Roll");
    Debug_Register_Param(1,  "Roll_Ki",  "f32", 0.0f, 1.0f,   g_roll_ki,  "Roll");
    Debug_Register_Param(2,  "Roll_Kd",  "f32", 0.0f, 1.0f,   g_roll_kd,  "Roll");
    Debug_Register_Param(3,  "Pitch_Kp", "f32", 0.0f, 10.0f,  g_pitch_kp, "Pitch");
    Debug_Register_Param(4,  "Pitch_Ki", "f32", 0.0f, 1.0f,   g_pitch_ki, "Pitch");
    Debug_Register_Param(5,  "Pitch_Kd", "f32", 0.0f, 1.0f,   g_pitch_kd, "Pitch");
    Debug_Register_Param(6,  "Yaw_Kp",   "f32", 0.0f, 10.0f,  g_yaw_kp,   "Yaw");
    Debug_Register_Param(7,  "Yaw_Ki",   "f32", 0.0f, 1.0f,   g_yaw_ki,   "Yaw");
    Debug_Register_Param(8,  "Yaw_Kd",   "f32", 0.0f, 1.0f,   g_yaw_kd,   "Yaw");
    Debug_Register_Param(9,  "Hover_Throttle", "u16", 800.0f, 2000.0f,
                         (float)g_hover_throttle, "Throttle");
}

/* 应用一个参数值到飞控（按 id 分发，范围校验后回执） */
static void Quadcopter_Apply_Param(uint8_t id, float val)
{
    switch (id) {
    case 0:  g_roll_kp = val;  break;
    case 1:  g_roll_ki = val;  break;
    case 2:  g_roll_kd = val;  break;
    case 3:  g_pitch_kp = val; break;
    case 4:  g_pitch_ki = val; break;
    case 5:  g_pitch_kd = val; break;
    case 6:  g_yaw_kp = val;   break;
    case 7:  g_yaw_ki = val;   break;
    case 8:  g_yaw_kd = val;   break;
    case 9:
        if (val < 800.0f || val > 2000.0f) {
            Debug_Param_Ack(id, 0, "out_of_range");
            return;
        }
        g_hover_throttle = (uint16_t)val;
        break;
    default:
        Debug_Param_Ack(id, 0, "unknown");
        return;
    }
    Debug_Param_Ack(id, 1, NULL);
}

/* 命令处理入口：在工程原有的命令行接收处（收到一行）调用。
 * 支持 PC 端参数面板下发的 $PS 行，其余命令交给原处理逻辑。 */
void Quadcopter_Handle_Command(const char *line)
{
    uint8_t id;
    float val;

    if (Debug_Param_Parse(line, &id, &val)) {
        Quadcopter_Apply_Param(id, val);
        return;
    }
    /* 原有文本命令（led on 等）继续走原处理 */
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
    uint32_t cycle = 0;

    (void)p_arg;

    /* 上电后告知 PC 设备信息 + 注册全部通道 + 注册飞控参数 */
    Quadcopter_Register_Channels();
    Quadcopter_Register_Params();

    while (1)
    {
        /*
         * 每 4 个周期（2s）重发一次注册信息。
         * 原因：PC 端可能在上电后才打开串口，只注册一次会漏掉 $DEV/$CH/$P；
         * PC 端对重复注册是幂等的（按 id 去重），可放心周期重发。
         */
        if ((cycle++ & 3) == 0) {
            Quadcopter_Register_Channels();
            Quadcopter_Register_Params();
        }

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
