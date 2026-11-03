# 19-STS3215-Status位与保护报警语义核验

> 状态：进行中
> 目的：核实 STS3215 地址65 `Status` 的证据边界，以及它与保护寄存器、协议状态包 error field 的关系，避免把未经型号/固件确认的位定义直接用于安全判定。

## 1. 证据范围

本轮核对 rustypot 当前 STS3215 定义、其 `Status` 读取接口以及公开的 STS/Feetech 资料线索。仍属于文档与源码静态核验，没有连接 SO-101、没有读取真实地址65、没有触发保护故障，也没有验证 C046 固件的具体位行为。

## 2. 地址65在 rustypot 中的准确语义边界

rustypot 将 STS3215 地址65定义为只读 `status`，类型为 `u8`，并提供 `read_status` / `sync_read_status`；同时 STS3215 定义标记 `status_alarms_only: true`。因此当前库能够可靠表达“读取一个8位 Status 值”，但该源码本身没有进一步把地址65的每一 bit 解码成具体报警名称。citeturn846248search0turn846248search2turn846248search3

这一区别非常重要：**不能因为寄存器名称叫 `Status`，就直接把某个 bit 的含义写成过压、过热、过载或过流，除非该 bit 定义能够追溯到准确型号/固件的官方资料。**

## 3. Status 与协议 error field 不是同一数据

本项目此前已经区分两条状态通道：

1. 协议 Status Packet 中随响应返回的 1-byte error/status 字段；
2. STS3215 控制表地址65的 `Status` 寄存器。

rustypot 的 API 同时支持带 error field 的读取接口，因此日志层可以同时保存两者；但两者来源、时序和语义不同，不能互相替代。rustypot 的 README 也明确说明 `*_with_error` API 会额外返回 status error byte。fileciteturn493file0

## 4. 保护参数与 Status 的关系

STS3215 控制表中与保护相关的字段至少包括：

| 地址 | 字段 | 当前可确认的用途 |
|---:|---|---|
| 13 | `Max_Temperature_Limit` | 温度阈值配置 |
| 14/15 | `Max/Min_Voltage_Limit` | 电压阈值配置 |
| 19 | `Unloading_Condition` | 卸载条件配置 |
| 20 | `LED_Alarm_Condition` | LED 报警条件配置 |
| 28 | `Protection_Current` | 保护电流配置 |
| 34 | `Protective_Torque` | 保护扭矩配置 |
| 35 | `Protection_Time` | 保护时间配置 |
| 36 | `Overload_Torque` | 过载扭矩配置 |
| 38 | `Over_Current_Protection_Time` | 过流保护时间配置 |
| 65 | `Status` | 运行时状态字节 |

rustypot 对这些寄存器的地址、访问属性和数据类型有明确映射。citeturn846248search0turn846248search3

但是“保护配置字段存在”并不等于“某个 Status bit 一定对应该保护项”，更不能证明达到阈值后的 Torque Enable、输出扭矩或恢复行为。后者必须以准确型号/固件资料和实测为准。

## 5. 当前最可靠的软件判定层级

在没有完成 C046/目标 SO-101 实机验证前，建议软件把状态分成以下层级，而不是直接生成未经证实的报警名称：

- `STATUS_UNREAD`：没有取得地址65；
- `STATUS_READ_OK`：成功取得原始8位值；
- `STATUS_NONZERO_UNCLASSIFIED`：读取成功且值非零，但缺少经过型号/固件确认的 bit 映射；
- `STATUS_CLASSIFIED`：只有存在准确官方 bit 定义并完成版本绑定时才使用；
- `COMM_FAULT`：根本没有获得有效响应；
- `PROTOCOL_ERROR`：响应包 error field 表明协议层错误；
- `FAULT_LATCHED`：经过项目安全规则判定需要停止控制并锁存。

这样可以避免把“非零状态值”错误地解释成某一个具体保护故障。

## 6. 与 `status_alarms_only` 的关系

rustypot 的 `status_alarms_only: true` 是 Feetech 状态字节解释策略的重要信息：状态字节用于报告报警，而不能简单按照“只要非零就意味着写入被拒绝”解释。此前 25-14 核验已经据此将“报警”和“写入拒绝”分开处理。

因此，即使地址65或协议 error byte 非零，也不能仅凭该值推断：

- 电机一定已经卸载扭矩；
- Torque Enable 一定变成0；
- 当前轴一定停止运动；
- 其他轴一定没有继续执行 Sync Write；
- 清除报警后可以自动恢复控制。

这些都必须独立读取/验证。

## 7. 最小健康采集建议

在目标硬件确认后，建议健康记录至少保留：

`timestamp + motor_id + firmware + Status(raw) + protocol_error(raw) + Torque_Enable + Present_Current + Present_Temperature + Present_Voltage + Present_Position`

保护配置则单独记录：

`Max_Temperature_Limit + Max/Min_Voltage_Limit + Unloading_Condition + Protection_Current + Protective_Torque + Protection_Time + Overload_Torque + Over_Current_Protection_Time`

不要把配置值和运行时状态值混成一个字段，也不要用配置值推导“保护已经触发”。

## 8. 对公开第三方 bit 映射的处理原则

公开资料中可以找到把地址65若干 bit 映射为电压、传感器、温度、电流、角度、过载等名称的第三方实现；例如 OpenBricks 的 ST3215 驱动给出了这种解码方式。该资料可以作为**测试假设线索**，但不是本项目当前接受的 Feetech C046/SO-101 官方证据。citeturn846248search4

因此当前文档不把这些第三方 bit 名称写成已验证的生产判据。下一阶段必须取得准确型号/固件对应的官方控制表、SDK 或供应商书面确认，并在实机上用故障注入验证 bit 与物理行为的一致性。

## 9. 实机验收矩阵

目标 SO-101 确认后至少执行：

1. 正常空载：记录地址65基线、协议 error byte、Torque Enable、电流、温度、电压；
2. 受控负载：记录 Status 与 Current/Temperature/Position 的时间关联；
3. 保护触发：记录触发前后 Status、Torque Enable、Current、Position 和是否停止输出；
4. 单轴保护：其他五轴同时发送动作，验证异常轴与正常轴的隔离行为；
5. 清除/恢复：验证报警清除后是否自动恢复，还是必须重新使能/人工复位；
6. 断连：区分“无响应”与“有响应但 Status 非零”；
7. 连续周期：验证异常发生后控制循环是否停止发送下一帧。

所有测试都应保留原始报文、时间戳、配置快照和固件版本。

## 10. 当前结论

目前可以确认的最强结论是：**STS3215 地址65是可读取的8位运行时 Status 寄存器，rustypot 提供单轴和 Sync Read 读取接口，并将 Feetech 状态字节标记为 alarm-only；但当前 rustypot STS3215 定义没有替本项目提供经官方型号/固件绑定的 bit 级故障解码。** citeturn846248search0turn846248search2turn846248search3

因此 25-14 当前应继续把 `Status(raw)` 作为可审计原始证据保存，而把具体报警分类、保护触发后的卸载行为和恢复条件继续列为待供应商/实机验证事项。

## 11. 未完成项

- SO-101 实际 STS3215 型号与固件确认；
- C046 准确固件下 Status bit 定义的官方证据；
- 地址65实机读回基线；
- 保护触发前后 Status/Torque/Current/Temperature/Voltage 联合记录；
- 单轴保护与多轴 Sync Write 隔离验证；
- 报警清除和恢复行为验证。

因此 25-14 继续保持“进行中”。
