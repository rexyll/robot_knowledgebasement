# 18-SO-Follower最小健康反馈读取闭环核验

> 状态：进行中
> 目的：在不把现有 LeRobot SO-Follower 误写成已具备健康闭环的前提下，核实 STS3215 可读取的最小健康寄存器集合，并定义动作发送后的最小可审计反馈闭环。

## 1. 证据范围

本轮核对当前 LeRobot SO-Follower 源码、LeRobot 硬件接口文档以及 rustypot STS3215 官方控制表。仍属于公开源码/文档静态核验，没有运行 LeRobot、没有连接 SO-101，也没有做实机寄存器读取、抓包或故障注入。LeRobot 当前 SO-Follower 的常规 `get_observation()` 读取 `Present_Position`，而 `send_action()` 使用 `Goal_Position` Sync Write。citeturn562215search6

## 2. 当前 SO-Follower 实际观测覆盖范围

当前 `get_observation()` 的电机读取路径是：

`bus.sync_read("Present_Position", num_retry=...)`

随后将结果映射为各电机的 `.pos` 观测；没有在该常规路径中同时读取 Torque Enable、Status、Present Current、Present Temperature 或 Present Voltage。citeturn562215search6

因此当前默认观测可以回答“轴的位置读回是多少”，但不能单独回答：

- 该轴当前是否仍处于 Torque Enable；
- 该轴是否存在 STS3215 硬件状态报警；
- 当前电流是否异常；
- 当前温度/电压是否处于允许范围；
- 该轴是否已经进入保护/卸载状态。

这不是说这些信息不可读取，而是说当前 SO-Follower 默认 observation 没有把它们纳入闭环。

## 3. STS3215 可用于健康闭环的最小寄存器集合

rustypot 当前 STS3215 定义显示：

| 寄存器 | 地址 | 权限 | 本项目用途 |
|---|---:|---|---|
| `Torque_Enable` | 40 | R/W | 判断扭矩使能状态 |
| `Present_Position` | 56 | R | 动作位置反馈 |
| `Present_Speed` | 58 | R | 可选运动状态/响应分析 |
| `Present_Load` | 60 | R | 可选负载趋势 |
| `Present_Voltage` | 62 | R | 电源健康 |
| `Present_Temperature` | 63 | R | 热健康 |
| `Status` | 65 | R | 舵机硬件状态/报警信息 |
| `Moving` | 66 | R | 是否仍处于运动状态 |
| `Present_Current` | 69 | R | 电流健康/异常趋势 |

这些地址和访问属性来自 rustypot STS3215 控制表。citeturn562215search3turn562215search8

需要特别保持地址65 `Status` 与协议状态包中的 error field 区分：二者不是同一个字段，也不能用其中一个替代另一个。

## 4. “最小健康反馈”不等于一次读取全部寄存器

工程上不宜默认每个控制周期都把所有健康寄存器与位置一起读取。原因包括串行总线事务耗时、控制周期抖动以及健康变量并不需要与位置具有相同采样频率。

建议首先定义两级读取：

### A. 快速动作反馈

每个控制周期保持：

`Present_Position`

用于建立：

`OBS(t) → COMMAND(t) → POSITION(t+1)`

并计算目标位置与实际位置误差。

### B. 健康反馈

以经实机测量验证后的较低频率读取：

`Torque_Enable + Status + Present_Current + Present_Temperature + Present_Voltage`

`Moving` 可作为辅助字段。

rustypot 支持按寄存器名称执行 `sync_read_register`，也提供带 error field 的 `sync_read_register_with_error`，因此底层能力足以构建比当前 SO-Follower 更细的反馈采集路径。citeturn562215search5

但“底层 API 能读取”不等于“当前 LeRobot SO-Follower 已实现该健康闭环”。

## 5. 推荐的最小状态判据

建议每个轴至少维护以下逻辑状态：

- `COMM_OK`：本周期读取事务成功并获得该轴数据；
- `POSITION_OBSERVED`：获得 `Present_Position`；
- `TORQUE_STATE_OBSERVED`：获得 `Torque_Enable`；
- `SERVO_STATUS_OBSERVED`：获得地址65 `Status`；
- `HEALTH_OK`：电流/温度/电压均通过已验证阈值；
- `FEEDBACK_CONFIRMED`：只有动作关联条件全部满足后才能进入；
- `FAULT_LATCHED`：任一安全条件失败并需要人工/明确恢复流程。

其中阈值不能凭经验直接写入生产配置，必须结合目标 STS3215 具体型号、固件、供电和实机基线测量确定。

## 6. 动作关联闭环

建议把动作确认设计为带时间戳的证据链：

`command_seq=N`

→ 记录六轴 `Goal_Position`

→ 下一周期读取六轴 `Present_Position`

→ 同时/按规定频率取得 `Status`、`Torque_Enable` 和健康数据

→ 按实机验证的响应时间窗口计算位置误差

→ 满足全部轴判据后才允许标记 `FEEDBACK_CONFIRMED`。

如果只有位置发生变化，但某轴 `Status` 报警、Torque Enable 异常或通信缺失，则不能仅凭位置变化标记整组动作确认。

同样，如果 Sync Write 本地调用成功但下一周期某轴没有有效反馈，也不能自动把该轴标记为执行成功。

## 7. error field 与 Status 的双通道记录

rustypot 支持带状态 error field 的读取 API；其 STS3215 定义同时提供地址65 `Status`。因此后续日志建议至少保存：

- 时间戳；
- command sequence；
- motor ID；
- Goal Position；
- Present Position；
- Torque Enable；
- Status 地址65；
- 协议状态包 error field（如果该调用路径返回）；
- retry 次数；
- 最终通信结果；
- 当前状态机状态。

这样才能在故障复盘时区分“没有收到包”“收到包但带报警”“寄存器状态异常”“位置没有按预期响应”等不同原因。

## 8. 与当前 SO-Follower 的边界

当前源码并没有实现上述完整健康反馈闭环：

1. `get_observation()` 默认只读取 `Present_Position`；
2. `send_action()` 直接 `sync_write("Goal_Position", ...)`；
3. 没有默认 post-action 健康读取；
4. `send_action()` 返回实际发送 action，而不是逐轴健康确认；
5. 因此当前代码不能声称已经实现 `FEEDBACK_CONFIRMED` 状态。

这些结论与 LeRobot 当前 SO-Follower 源码及其通用机器人 API 定义一致。citeturn562215search6turn562215search9

## 9. 后续实机验收

必须在目标 SO-101 实机上验证：

- 六轴位置同步读的实际耗时；
- 健康寄存器读取对控制周期的额外负担；
- 地址65 Status 的正常基线和故障值；
- Torque Enable 在正常、断连、保护和恢复场景下的真实表现；
- Present Current/Temperature/Voltage 的正常范围和异常响应；
- 位置误差阈值与响应时间窗口；
- 单轴健康异常时是否立即阻止下一控制帧；
- 健康读取失败时是否进入故障锁存，而不是继续控制。

## 10. 当前结论

可以确认：**STS3215 底层已经提供足够的寄存器反馈能力来构建最小健康闭环，但当前 LeRobot SO-Follower 默认 observation 只读取 `Present_Position`，因此现状仍是“位置反馈闭环”，不是完整的“健康/故障反馈闭环”。** citeturn562215search3turn562215search5turn562215search6

本项目后续应把“位置观测”“健康观测”“动作确认”三个层级分开定义，并在实机测量后确定采样频率、阈值和故障锁存策略。

## 11. 未完成项

- 目标 SO-101 实际安装型号、控制板和固件确认；
- 六轴健康寄存器实机读回；
- 正常基线与阈值测量；
- 动作反馈延迟和总线负载测量；
- 故障状态下的保护/卸载行为验证；
- 健康异常后停止发送与人工恢复实测。

因此 25-14 继续保持“进行中”。
