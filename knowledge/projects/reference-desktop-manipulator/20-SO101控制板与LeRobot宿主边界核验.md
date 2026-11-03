# 20-SO101控制板与LeRobot宿主边界核验

> 状态：进行中
> 目的：根据 Hugging Face SO-101 官方装配/配置文档与 WaveShare Bus Servo Adapter (A) 官方资料，进一步收敛“控制板是什么、哪里运行控制逻辑、哪些配置实际写入舵机 EEPROM”的证据边界，并避免把 Adapter A 误写成具有运动控制固件的下位机。

## 1. 本轮新增证据

用户提供的资料方向是有价值的，但其中有几处需要用一手资料收紧措辞。本轮优先采用 Hugging Face 与 WaveShare 官方资料复核。

### 1.1 SO-101 官方确实使用 Bus Servo Adapter

Hugging Face 的 SO-101 官方文档要求为 leader 和 follower 各准备一块 bus servo adapter 与 6 个电机；连接时 USB 接入电脑、同时给 motor bus 提供电源，并通过 `lerobot-find-port` 识别对应串口。配置电机 ID/波特率时，官方文档明确说明参数写入电机内部的非易失性存储器（EEPROM），而不是把 ID/波特率作为控制板上的持久配置。citeturn663813search0turn663813search1

因此可以把 SO-101 的运行边界明确成：

`PC/主机上的 LeRobot → USB/串口 → Bus Servo Adapter → 单总线 → STS3215`。

这与此前 25-14 对 LeRobot/rustypot 调用链的结论一致：运动控制软件主要位于上位机，舵机负责实际闭环执行和自身寄存器/保护逻辑。

### 1.2 Adapter A 的官方硬件定位

WaveShare 官方 FAQ 明确称 Bus Servo Adapter (A) 使用 CH343 USB-to-serial 芯片；板上没有 driver chip，而是 serial port conversion IC；USB Type-C 接口也是 USB-to-serial；板卡没有板载稳压，输出电压与输入电压相同；最大可承受电流标称 5A。官方资源页还提供 Bus Servo Adapter (A) Schematic。citeturn663813search2turn663813search4

因此本项目可以较有把握地将 Adapter A 描述为：

- USB ↔ 总线串行接口/半双工物理层适配板；
- 同时承担舵机总线供电与连接；
- 不应把它描述成执行轨迹规划、IK 或六轴控制算法的机器人主控板。

但**不能仅凭 FAQ 中“serial port conversion IC / no driver chip”一句话，就进一步写成“已经证明板上绝对没有任何 MCU 或可升级固件”**。目前更稳妥的生产文档表述是“官方资料将其定位为串口转换/总线适配板；尚无证据表明它承担 SO-101 的运动控制算法或 LeRobot 运行时”。如果未来拿到官方 BOM/原理图完整器件清单，可以再把“是否存在可执行 MCU”收紧到器件级结论。

## 2. LeRobot 是实际的控制逻辑宿主

Hugging Face 官方 SO-101 文档要求安装 LeRobot，并额外安装 Feetech 支持；官方配置流程使用 `lerobot-find-port`、`lerobot-setup-motors`、`lerobot-calibrate` 等工具。官方文档说明电机 ID 和波特率写入电机内部 EEPROM。citeturn663813search0turn663813search3

LeRobot 官方 Motors API 又明确说明 `SerialMotorsBus` 是连接 Feetech/Dynamixel 串行舵机的低层接口，电机模型和控制表由 rustypot 管理，串口也由 rustypot 管理。citeturn663813search8

因此对于本项目的控制边界，应记录：

1. **轨迹/动作生成与 SO-101 应用控制逻辑：** 上位机 LeRobot；
2. **串行协议、控制表和串口访问：** LeRobot + rustypot；
3. **USB/总线物理转换与供电：** WaveShare Adapter A；
4. **位置闭环、保护阈值及舵机内部执行：** STS3215 本体固件/硬件。

这四层不能合并成“控制板固件”。

## 3. 一个重要的版本/电压边界

Hugging Face 当前 SO-101 文档同时覆盖 7.4V 与 12V STS3215 版本，并明确警告电源必须与舵机版本匹配；官方页面指出 leader arm 使用 7.4V 电机，并提醒错误电压可能损坏电机。citeturn663813search1

WaveShare Adapter A 官方 FAQ 则明确指出板上没有电压调节，输出电压与输入电压相同。citeturn663813search2

因此本项目后续 BOM/安全验证必须把以下项目绑定，而不能只记录“SO-101”：

`servo SKU/额定电压 + adapter SKU/PCB Rev + 输入电源电压 + 电源限流能力 + LeRobot 配置 + 电机固件`。

特别是 Adapter A 本身不负责把 12V 转成 7.4V；电源选择错误不能归因给 LeRobot 软件。

## 4. 对用户提供资料的逐条判定

| 用户提供的说法 | 本项目判定 | 处理 |
|---|---|---|
| 官方板卡是 WaveShare Bus Servo Adapter (A) | 与 Hugging Face/WaveShare 官方资料方向一致 | 可作为当前工作基线，但仍需目标套件实物 SKU/PCB Rev 绑定 |
| 板卡是供电 + 通信协议转换，而非运动控制主控 | 基本成立 | 采用“串口转换/总线适配与供电板”更严谨 |
| 板上使用 CH343 | 官方 FAQ 明确支持 | 可写入硬件基线 |
| 有官方 Adapter A Schematic | 官方资源页明确提供 | 可写入来源台账；详细器件级结论需继续读取原理图 |
| 板上没有运行传统意义上的下位机运动固件 | 方向正确，但“绝对没有可执行 MCU/固件”证据尚未完整闭合 | 文档暂写为“未发现其承担运动控制固件的证据” |
| LeRobot 在 PC/Jetson 等上位机运行控制逻辑 | 与官方 SO-101 文档和 Motors API 一致 | 纳入架构边界 |
| ID/波特率写入舵机 EEPROM | 官方文档明确 | 纳入配置基线 |
| `pip install -e ".[feetech]"` | 官方 SO-101 文档当前仍明确要求 Feetech 支持 | 纳入安装记录，但实际项目锁定版本仍以 13 号审计为准 |
| “通常 1M” | 官方 WaveShare FAQ 说明其舵机默认出厂波特率为 1,000,000 | 可作为默认/出厂资料，不等同于目标六轴实物当前状态；实机仍需扫描确认 |
| Adapter A 是“高电流供电管理” | 可以描述为供电/总线供电接口，但不能把它等同于带复杂电源管理/稳压/保护控制器 | FAQ 明确没有板载稳压，最大承受电流 5A |

## 5. 对 25-14 安全边界的影响

这批信息使此前“控制板固件/运行时依赖”这一待核问题可以进一步拆成两个独立问题：

### A. Adapter A 本体

主要核验：

- SKU 与 PCB Rev；
- 原理图和 BOM；
- CH343 与半双工收发方向控制电路；
- 输入电压、电源路径、连接器与 5A 标称边界；
- USB/串口异常时是否可能保持总线供电；
- 板上是否存在任何可执行 MCU/可升级固件器件。

### B. STS3215 舵机本体

主要核验：

- 准确 STS3215 SKU/额定电压；
- 电机固件版本；
- 地址 13/14/15/19/28/34/35/36/38 保护参数；
- 地址 65 `Status`；
- 协议 Status Packet error byte；
- Torque Enable 与保护触发后的实际行为。

因此，**Adapter A 的“无运动控制算法”结论不能替代 STS3215 固件安全行为核验**；同样，STS3215 的保护行为也不能归因给 Adapter A。

## 6. 对“控制板固件”的项目术语修正

从本轮证据开始，本项目不再把 SO-101 的 Adapter A 简写成“下位机控制板”。建议统一使用：

> **Bus Servo Adapter (A)：USB/串行总线适配与舵机供电板。**

如果必须写“控制板”，则首次出现写成：

> **SO-101 所用控制/适配板（WaveShare Bus Servo Adapter (A)）**

并立即注明其主要职责是 USB/串行转换、总线连接和供电，而不是运行 LeRobot 六轴运动控制算法。

## 7. 尚未闭合的关键证据

本轮不能把以下项目标记为完成：

- 目标 SO-101 套件实物是否确为 Adapter A；
- 实物 PCB Rev 与官方原理图版本对应关系；
- 完整 BOM 中是否存在任何可执行 MCU；
- Adapter A 的真实输入电压/瞬态电流/短路保护行为；
- 目标六个 STS3215 的准确 SKU、额定电压、固件版本；
- 目标舵机地址65 `Status` bit 级定义；
- 保护触发后的 Torque Enable、输出扭矩和恢复行为；
- USB/串口断连时六轴的真实物理状态。

因此 25-14 继续保持“进行中”。

## 8. 下一步

1. 读取并归档 WaveShare Adapter A 官方原理图，建立器件级 BOM/信号路径核验表；
2. 继续核对 STS3215 保护寄存器的默认值、单位、阈值与 C044/C046 型号差异；
3. 将 Adapter A 的供电边界与 STS3215 7.4V/12V 版本绑定到 BOM/验证计划；
4. 获取目标实物 SKU/PCB Rev/电机固件后，再决定哪些“官方资料结论”可以升级为“目标硬件已确认”。
