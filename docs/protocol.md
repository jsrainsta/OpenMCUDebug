# 通信协议

## Stage 1：日志 + 命令（v0.1）

### MCU → PC（日志）

每行一条消息，格式：`[TAG] 内容`

| 标签    | 含义   | 界面显示颜色 |
|---------|--------|-------------|
| `[INFO]` | 普通信息 | 绿色       |
| `[DATA]` | 数据     | 蓝色       |
| `[ERROR]` | 错误    | 红色        |

无标签的行按普通日志显示（灰色）。

示例：
```
[INFO] System Start
[DATA] Counter=10
[ERROR] Sensor Failed
```

编码：UTF-8。行尾：`\n`（兼容 `\r\n`）。

### PC → MCU（命令）

纯文本命令，一行一条，MCU 端自行解析：
```
led on
pid kp 1.5
```

默认行尾 `\r\n`（PC 端界面可选 LF / CRLF / 无）。

---

## Stage 2：设备模型（v0.2）

在 Stage 1 基础上增加设备身份和数据模型的标准化传输。

### 设计原则

- **单行紧凑格式**：一条消息只占一行，MCU 一次 `snprintf` 即可发送
- **`$` 前缀区分**：与 Stage 1 的 `[INFO]` / `[DATA]` / `[ERROR]` 互不冲突
- **key=value 参数**：逗号或空格分隔，人类可读且易解析

### 消息类型

#### 1. DEVICE_INFO — 设备宣告

```
$DEV name=<设备名>,ver=<版本号>
```

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| name | string | 是 | 设备名称，如 `Quadcopter`、`STM32F411 Fan` |
| ver | string | 否 | 固件版本号，如 `1.0` |

示例：
```
$DEV name=Quadcopter,ver=1.0
$DEV name=STM32F411 Fan,ver=0.1
```

#### 2. CHANNEL_REGISTER — 通道注册

```
$CH id=<编号>,name=<名称>,type=<类型>,unit=<单位>
```

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| id | int | 是 | 通道编号（0~255），后续 DATA_UPDATE 使用此 ID |
| name | string | 是 | 通道名称，如 `Throttle`、`Accel_X`、`Battery` |
| type | string | 是 | 数据类型，取值见下表 |
| unit | string | 否 | 单位（如 `us`、`degree`、`volt`、`raw`），纯显示用途 |

**type 取值**：

| 值 | 含义 | 备注 |
|----|------|------|
| `i8` | int8 | 有符号 8 位 |
| `i16` | int16 | 有符号 16 位 |
| `i32` | int32 | 有符号 32 位 |
| `u8` | uint8 | 无符号 8 位 |
| `u16` | uint16 | 无符号 16 位 |
| `u32` | uint32 | 无符号 32 位 |
| `f32` | float | 32 位浮点 |
| `str` | string | 字符串 |

示例：
```
$CH id=0,name=Throttle,type=u16,unit=us
$CH id=1,name=Accel_X,type=i16,unit=raw
$CH id=3,name=Voltage,type=f32,unit=V
```

#### 3. DATA_UPDATE — 数据更新

```
$VAL id=<编号>,val=<数值>
```

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| id | int | 是 | 通道编号，必须与 CHANNEL_REGISTER 中的 id 一致 |
| val | int/float/str | 是 | 当前值 |

示例：
```
$VAL id=0,val=1500
$VAL id=1,val=-512
$VAL id=3,val=11.8
```

### 完整示例（Quadcopter 上电）

```
$DEV name=Quadcopter,ver=1.0
$CH id=0,name=Throttle,type=u16,unit=us,visual=gauge
$CH id=1,name=Accel_X,type=i16,unit=raw
$CH id=2,name=Accel_Y,type=i16,unit=raw
$CH id=3,name=Accel_Z,type=i16,unit=raw
...
$VAL id=0,val=1000
$VAL id=1,val=512
$VAL id=2,val=-45
```

### PC 端处理

- `$DEV` → 创建设备对象，在左侧面板显示设备名 + 版本
- `$CH` → 注册通道，在左侧面板的树形列表中新增一行
- `$VAL` → 更新对应通道的当前值，实时显示在面板中
- 所有 `$` 开头的协议行在日志窗口以紫色显示（区别于 Stage 1 的绿/蓝/红）
- 非协议行完全按 Stage 1 规则显示（向下兼容）

---

## Stage 3：可视化描述（v0.3）

### 设计原则

- **数据与界面分离**：设备在协议中描述"怎么显示"，PC 端自动生成对应组件
- **`visual` 是 `$CH` 的可选扩展**：不携带时行为与 Stage 2 完全一致（默认文本显示）
- **向后兼容**：旧固件（无 visual 字段）在 v0.3 PC 端上表现与 v0.2 相同

### CHANNEL_REGISTER 增加 visual 字段

```
$CH id=<编号>,name=<名称>,type=<类型>,unit=<单位>,visual=<可视化类型>
```

| visual | 含义 | PC 端生成组件 | 适合场景 |
|--------|------|--------------|----------|
| `text`（默认） | 普通数值 | 文本卡片（大字号数值 + 单位） | 开关状态、原始传感器值 |
| `gauge` | 仪表盘 | 270° 圆弧仪表，量程随数据自适应 | 电压、电量、百分比、油门位置 |
| `chart` | 实时曲线 | 滚动曲线（最近 300 个采样点，Y 轴自适应） | 温度、速度、姿态角 |

示例：

```
$CH id=0,name=Throttle,type=u16,unit=us,visual=gauge
$CH id=1,name=Roll,type=i16,unit=degree,visual=chart
$CH id=2,name=Status,type=str,visual=text
```

规则：

- `visual` 可省略，缺省为 `text`
- 未知类型按 `text` 处理（容错）
- 仪表/曲线忽略字符串值（如 `$VAL id=0,val=armed`）

### PC 端自动生成流程

```
$CH id=0,name=Throttle,type=u16,unit=us,visual=gauge
        ↓
  通道注册（DeviceManager）
        ↓
  仪表盘按 visual 创建组件（Dashboard）
        ↓
$VAL id=0,val=1500  → 实时刷新对应组件
```

仪表盘位于主窗口"仪表盘"Tab，与"日志终端"Tab 并列；
断开串口时自动清空，重连后按新的 `$CH` 重新生成。

---

## Stage 4：会话记录与回放（v0.4）

协议零改动。PC 端把串口接收的每一行连同相对时间戳写入 CSV
（首行表头 `time_ms,line`，line 字段按 CSV 规则转义）：

```
time_ms,line
0.0,[INFO] System Start
12.4,$DEV name=Quadcopter,ver=1.0
512.3,$VAL id=0,val=1500
```

「回放」按录制时间差把行重新注入数据链路（日志着色、设备面板、
仪表盘全部照常工作），支持暂停 / 变速（0.5x ~ 4x）。

---

## Stage 5：参数调节（v0.5）

在 Stage 2 的 `$` 协议家族中增加参数类消息，实现 PC 端调节飞控参数
（PID 等）的完整闭环：MCU 注册参数 → PC 展示与编辑 → 下发 → 回执。

### 设计原则

- **`$P` / `$PV` / `$PA` / `$PS` 与前缀不冲突**：`$P` 用 `\b` 边界匹配，
  `$PV` / `$PA` 不会误判
- **范围由 MCU 声明**：min/max 只在有意义时携带（SDK 约定 min==max 即省略），
  PC 端据此显示范围提示；实际校验由 MCU 执行
- **回执闭环**：PC 下发后必须收到 `$PA` 才知道参数是否被接受
- **值与通道值同规则**：字符串形式传输，PC 自动转 int/float

### 消息类型

#### 1. PARAM_REGISTER — 参数注册

```
$P id=<编号>,name=<名称>,type=<类型>,min=<最小>,max=<最大>,val=<当前值>,group=<分组>
```

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| id | int | 是 | 参数编号（0~255） |
| name | string | 是 | 参数名，如 `Roll_Kp` |
| type | string | 是 | 数据类型描述（`f32` / `u16` 等），仅用于 PC 端显示与输入提示 |
| min / max | float | 否 | 取值范围；无限制时省略（SDK 约定 min==max 即省略） |
| val | float | 否 | 当前值 |
| group | string | 否 | 分组名（如 `Roll` / `Pitch` / `Yaw`），PC 端按组分树 |

示例：
```
$P id=0,name=Roll_Kp,type=f32,min=0,max=10,val=1.5,group=Roll
$P id=9,name=Hover_Throttle,type=u16,val=1200
```

#### 2. PARAM_VALUE — 参数值更新

```
$PV id=<编号>,val=<数值>
```

MCU 内部修改参数后可主动上报，或随周期注册刷新当前值。

#### 3. PARAM_SET — 参数下发（PC → MCU）

```
$PS id=<编号>,val=<数值>
```

PC 参数面板编辑后发送，行尾固定 `\r\n`。MCU 端用
`Debug_Param_Parse()` 解析，应用后必须回执。

#### 4. PARAM_ACK — 下发回执

```
$PA id=<编号>,ok=<0|1>
$PA id=<编号>,ok=0,msg=<原因>
```

| 参数 | 说明 |
|------|------|
| ok | 1=接受，0=拒绝 |
| msg | 拒绝原因（单词，不能含逗号/空格，如 `out_of_range` / `unknown`） |

### 完整闭环示例

```
MCU → PC:  $P id=0,name=Roll_Kp,type=f32,min=0,max=10,val=1.5,group=Roll
PC 面板:  显示分组 Roll 下 Roll_Kp，当前值 1.5，范围 0 ~ 10
PC → MCU:  $PS id=0,val=2.0
MCU:      应用成功 → $PA id=0,ok=1           （失败 → $PA id=0,ok=0,msg=out_of_range）
```

### PC 端处理

- `$P` → 注册参数，按 `group` 分组显示在「参数」Tab（第三个 Tab）
- `$PV` → 刷新参数当前值列
- `$PA` → 状态列着色显示 ✓ 已应用 / ✗ 原因
- 周期重发 `$P` 按 id 去重；断开串口时清空全部参数
- 预设：当前全部参数值可保存为 JSON（`{参数名: 值}`），
  载入后按名称匹配，串口打开时确认后全部下发
