"""Stage 3：可视化组件包。

根据设备通道描述的 visual 字段自动生成 Dashboard 组件：

    text  → TextWidget    普通数值显示
    gauge → GaugeWidget   仪表盘（电压 / 电量 / 百分比）
    chart → ChartWidget   实时曲线（温度 / 速度 / 姿态）
"""
