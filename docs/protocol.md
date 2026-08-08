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
$CH id=0,name=Throttle,type=u16,unit=us
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
