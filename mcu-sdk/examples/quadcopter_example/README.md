# Quadcopter Stage 2/3/5 集成示例

本示例展示如何将 Quadcopter 项目（`STM32F401 + uC/OS-II`）的串口输出
从自由格式 `snprintf` 升级为 Stage 2 标准协议，并在 Stage 3 中
通过 `visual` 字段让 PC 端自动生成仪表盘，在 Stage 5 中注册飞控参数
（PID 等）让 PC 端参数面板可以直接调节。

## 集成步骤

1. 将 `mcu-sdk/include` 和 `mcu-sdk/src` 复制到 Quadcopter 工程并加入编译
2. 在工程中实现 `Debug_UART_Send()`（即已有的 `HAL_UART_Transmit` 调用）
3. 用本示例的 `UartTask` 替换原 `Core/Src/main.c` 中的同名函数
4. 在工程原有的命令行接收处（收到一行后）调用 `Quadcopter_Handle_Command(line)`，
   参数面板下发的 `$PS` 行会被解析并应用，其余命令走原处理逻辑
5. **波特率建议提到 115200**（`Core/Src/usart.c` + CubeMX 同步，PC 工具默认值）：
   9600 波特率下 15 通道协议流已占用约 70% 带宽（约 660 B/s vs 960 B/s 上限），
   周期重发注册信息 + 参数 + 日志后余量不足
6. 重新编译 → 烧录 → PC 端打开串口即可看到设备信息面板、自动仪表盘与参数面板

> 注册信息（$DEV/$CH/$P）每 2s 周期重发（PC 可能在上电后才打开串口）；
> PC 端对重复注册按 id 去重，不会产生重复行/重复组件。

## 效果对比

### 原输出（自由格式，Stage 1）

```
THR:1000
Accel:0,0,16384
Gyro:0,0,0
Mag:0,0,0
Pre_RAW:0 Tem_RAW:0
```

PC 只能显示，无法自动理解数据含义。

### 新输出（Stage 2 协议）

```
$DEV name=Quadcopter,ver=1.0
$CH id=0,name=Throttle,type=u16,unit=us
$CH id=1,name=Roll,type=u16,unit=us
...
$CH id=14,name=Temperature,type=u32,unit=raw
$VAL id=0,val=1000
$VAL id=1,val=1500
$VAL id=4,val=512
...
```

PC 端自动显示设备名称和 15 个通道，实时更新数值。

### Stage 5 参数协议

```
$P id=0,name=Roll_Kp,type=f32,min=0,max=10,val=1.5,group=Roll   ← 参数注册（上电/周期）
$PV id=0,val=1.5                                                 ← 参数值更新（可选）
$PS id=0,val=2.0     ← PC 参数面板下发（PC → MCU）
$PA id=0,ok=1                                                   ← 回执（MCU → PC）
```

PC 端「参数」Tab 按 `group` 分组显示（Roll / Pitch / Yaw / Throttle），
可编辑值下发、查看回执、保存/载入本地预设（如「起飞快」「悬停稳」两套 PID）。

## 通道清单（Stage 3 起带可视化类型）

| ID | 名称 | 类型 | 单位 | 可视化 | 来源 |
|----|------|------|------|--------|------|
| 0 | Throttle | u16 | us | gauge 仪表盘 | PPM_Values[2] |
| 1 | Roll | u16 | us | chart 实时曲线 | PPM_Values[0] |
| 2 | Pitch | u16 | us | chart 实时曲线 | PPM_Values[1] |
| 3 | Yaw | u16 | us | chart 实时曲线 | PPM_Values[3] |
| 4 | Accel_X | i16 | raw | text | MPU6050 |
| 5 | Accel_Y | i16 | raw | text | MPU6050 |
| 6 | Accel_Z | i16 | raw | text | MPU6050 |
| 7 | Gyro_X | i16 | raw | text | MPU6050 |
| 8 | Gyro_Y | i16 | raw | text | MPU6050 |
| 9 | Gyro_Z | i16 | raw | text | MPU6050 |
| 10 | Mag_X | i16 | raw | text | HMC5883L |
| 11 | Mag_Y | i16 | raw | text | HMC5883L |
| 12 | Mag_Z | i16 | raw | text | HMC5883L |
| 13 | Pressure | u32 | raw | text | MS5611 |
| 14 | Temperature | u32 | raw | chart 实时曲线 | MS5611 |

PC 端收到带 `visual` 的 `$CH` 行后自动生成仪表盘：
Throttle 仪表、Roll/Pitch/Yaw 姿态曲线、Temperature 温度曲线，
其余通道以文本卡片显示。

## 参数清单（Stage 5）

| ID | 名称 | 类型 | 范围 | 分组 | 说明 |
|----|------|------|------|------|------|
| 0~2 | Roll_Kp/Ki/Kd | f32 | 0~10 / 0~1 | Roll | 横滚 PID |
| 3~5 | Pitch_Kp/Ki/Kd | f32 | 0~10 / 0~1 | Pitch | 俯仰 PID |
| 6~8 | Yaw_Kp/Ki/Kd | f32 | 0~10 / 0~1 | Yaw | 偏航 PID |
| 9 | Hover_Throttle | u16 | 800~2000 | Throttle | 悬停油门（us） |

> `Debug_Register_Param` 的 min == max（如 0/0）时省略范围字段，
> 表示该参数无限制。
