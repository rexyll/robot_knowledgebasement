# Stäubli ROS 2—控制状态反馈、模式语义与故障恢复一致性审计

- **审计编号：** SERVO-857
- **章节节点：** §9.3.274
- **日期：** 2026-11-10
- **审查基线：** `ICube-Robotics/staubli_driver_ros2@bd658e2d266e315d2ee35f985fb352ea88306b79`
- **目标分支：** `rexyll/robot_knowledgebasement:main`
- **审计性质：** 固定提交静态源码、现有测试与接口文档核对；不修改上游代码。

## 1. 审计目标与范围

本节点追踪机器人状态从 VAL3 控制任务采集、字段填充、二进制编码，到 C++ 解码、RobotDriver 有效性/新鲜度检查、ros2_control 状态接口导出的完整路径；同时审查故障复位后控制模式、状态序号和新命令的恢复关系。

重点字段：`bInMotion`、`bInError`、`bMotionPossible`、`nControlMode`、`nSequenceDelay`、`nSafetyStatus`、状态帧 sequence number、ROS 2 `supervision/*` state interfaces。

核对文件包括：

- VAL3：`updateState.pgx`、`controlTask.pgx`、`RobotState.dtx`、`encodeRobotStateMsg.pgx`。
- C++：`types.hpp`、`messages.hpp/.cpp`、`real_time_socket_subscriber.hpp/.cpp`、`robot_driver.cpp`、`staubli_hardware_interface.cpp/.hpp`。
- 测试：`test_message_serialization.cpp`、`test_robot_driver.cpp`。
- 文档：驱动 quickstart overview 中的 supervision state interface 说明。

## 2. 正向核对：协议位与 ROS 接口映射

1. VAL3 `encodeRobotStateMsg` 的状态位顺序为：bit 0 DrivePowered、bit 1 BrakeReleased、bit 2 MotionPossible、bit 3 InMotion、bit 4 InError、bit 5 EStopped。
2. C++ `RobotStateMessage::serialize/deserialize` 使用的 `StatusFlag` 位掩码与上述 bit 0–5 对应；字段顺序也与 VAL3 固定payload布局相符。
3. C++ `StaubliHardwareInterface::update_state()` 将 operation mode、operation mode status、safety status、sequence delay、brakes released、motion possible、in motion、in error、estop pressed、wait for ack 逐项复制到 `supervision_gpio_copy_`；`export_state_interfaces()` 导出的接口名称与这些字段对应。
4. joint position 与 velocity 缺失时 `update_state()` 返回失败；joint torque缺失时被置零。位置/速度由驱动侧从度制转换为弧度制。以上仅为代码映射核对，不证明机器人端传感器值的准确度或实时性。

## 3. 主要发现

### SF1｜状态字段的生成语义比接口名称更窄

`updateState.pgx` 明确将 `bInMotion = !isSettled()`；该字段因此是 VAL3 `isSettled()` 判据的反值，不是由本工程独立计算的实际轴速度/静止判据。代码没有在该字段旁定义速度阈值、连续采样次数、静止确认时间或停止响应上限。

`bMotionPossible` 当前仅按 `bDrivePowered and (!bEStopped)` 生成；被注释掉的另一表达式曾额外检查 `nRobotStatus == 0`，但当前没有启用。另有 `bBrakeReleased = bDrivePowered`，并非独立制动器状态回读。该逻辑与“motion possible”接口名称可能让上层消费者期待的完整安全许可语义并不等价。安全状态与制动语义的更早发现见 SERVO-852，本条在此记录其对状态一致性审查的影响，不把它误报为本轮新发现。

**影响：** 上层只能把这些接口看作 VAL3 当前软件状态摘要；不能据此证明所有安全互锁均满足、制动器已物理释放或机器人已经静止。必须查验控制器/机器人型号对应的真实状态源与安全功能定义。

### SF2｜状态帧在本轮命令处理之前发布，反馈与控制决策存在周期错位

`controlTask.pgx` 的主循环先调用 `updateState()`，再写入 sequence number、sequence delay、`bInError=l_bError` 与 `nControlMode=l_nCmdMode`，随后编码并发送 RobotState。发送完成后才读取新命令、检查命令/序号延迟、选择控制模式、执行运动命令及处理错误。

因此，该状态帧中的控制模式和内部错误标志代表本轮命令处理前的内部变量快照，而不是本轮命令已经被接受或执行后的确认。命令处理阶段新产生的错误，不能出现在本轮已经发送的帧中；若错误分支又在同轮清除 `l_bError`，下一帧也可能看不到该瞬态值。此项与 SERVO-856 的错误传播时序发现相互印证，本节点进一步确认 `nControlMode` 也受到相同的发布时序影响。

**影响：** ROS 侧可能把上一周期的 control_state 当成当前命令执行状态；`in_error=false` 不代表刚刚处理的命令未触发错误，也不代表故障事件从未发生。

### SF3｜无有效命令时可报告 INVALID 控制模式，但错误标志为 false

VAL3 的控制模式约定为 0=Invalid/Error、1=STOP/Idle、2=Joint Position、3=Joint Velocity。主循环在 `l_bError` 为 false、但 `robot_command_msg.robotCommand.bIsValid` 为 false 时，仍将 `l_nCmdMode` 设为 0。此路径本身不必设置 `l_bError=true`。由于状态发布在命令处理之前，后续状态帧可以呈现 `control_state=INVALID` 与 `error_state=false` 同时成立。

C++ `write()` 在非 STOP 控制模式下会把 `error_state=true` 或 `control_state=INVALID` 视为错误并尝试发送 STOP；但没有显式定义“无命令空闲态”究竟应当表示 STOP 还是 INVALID，也没有通过单独 validity 位区分“没有活动命令”和“控制器内部错误”。

**影响：** 上层难以仅凭 `in_error` 与 `control_state` 组合区分正常空闲、通信恢复中的暂态与真正控制错误；状态枚举契约需要统一。

### SF4｜内部错误复位后存在隐式 STOP 重新武装顺序

VAL3 错误处理分支将 `l_nCmdMode` 设为 0、使旧命令无效、清零控制序号/延迟并重置 socket。循环尾部随后执行 `l_nPreviousCmdMode = l_nCmdMode`，因此复位后的先前模式会变为 0。

若恢复后第一个有效命令直接请求模式 2 或 3，模式转换守卫会命中：
`previous != current && current != STOP && previous != STOP`。
在 `previous=0` 的情况下，直接进入位置/速度模式会被拒绝并触发错误路径。若先收到 STOP（模式 1），转换守卫允许该 STOP，循环尾把 previous mode 更新为 1，下一次位置/速度命令才可能通过该模式转换检查。

**结论边界：** 这是依据固定提交控制流得出的静态状态机推导，不是已在 CS9 上复现的行为。代码没有把“复位后必须先发送 STOP，再重新请求运动”定义成独立、可观测的恢复握手，也没有检查该 STOP 是否获得控制器接受/停止确认。建议将其明确设计为恢复协议，而不是依赖调用方猜测内部模式规则。

### SF5｜C++ 写命令路径没有完整核对请求模式与反馈模式的一致性

`StaubliHardwareInterface::write()` 在非 STOP 模式下只拒绝 `state_msg_.error_state` 或 `state_msg_.control_state == INVALID`；代码没有显式比较当前 `current_control_mode_` 与最近状态帧的 `control_state`，也没有独立的“请求已接受/正在执行/已停止”状态字段。

由于 VAL3 状态帧在处理本轮命令之前发送，模式反馈天然可能落后一轮；而驱动又没有 command ACK 或模式接受回执与本次命令序号关联。故 `write()` 返回成功只能说明本地发送路径接受了该消息，不能证明控制器已经接受相同模式，更不能证明机器人已经进入该模式或开始运动。命令确认链缺口已在 SERVO-792 记录，本节点把它与模式反馈的周期错位关联起来。

### SF6｜重复序号的数据报仍可能刷新状态新鲜度

`RealTimeSocketSubscriber::update_message()` 对每一份成功反序列化的数据报都更新本地 `reception_timestamp`。`read_message()` 虽会在序号相同的情况下把 `status.new_message=false`，但仍返回成功；`RobotDriver::read_robot_state()` 检查消息类型和时间年龄，却没有检查 `status.new_message`，随后仍将缓存状态复制给调用方并更新 `last_valid_sequence_id_`。

因此，如果发送端持续重发相同 sequence number 的有效数据报，时间戳会随接收更新，状态可能持续通过 staleness 检查，尽管序号没有前进。这与 SERVO-851 的重复序号/新鲜度发现相同；此处强调它会直接污染“状态反馈持续更新”和“恢复后收到新状态”的判定。

### SF7｜状态过期后没有显式向状态接口发布 invalid 标志

`RobotDriver::read_robot_state()` 在状态超时或读取失败时返回 false；硬件接口 `read()` 随即返回 `ERROR`，不会调用 `update_state()` 清除或标记上一份 supervision/joint state。硬件接口没有额外导出 `state_valid`、状态接收时间戳或会话代次字段。

所以在 read 错误返回后，接口内存仍保留最后一次成功更新的数值；其是否被上层继续读取取决于 ros2_control 生命周期和消费者行为，不能把缓存值当成当前机器人状态。仅凭现有导出接口无法区分“数值保持不变的真实静止”与“通信中断导致的旧值保持”。

## 4. 现有测试覆盖评估

- `test_message_serialization.cpp` 的 RobotState 测试覆盖基本字段、状态位和有效字段位的 C++ 序列化/反序列化往返；没有覆盖 VAL3 实际编码器生成的跨语言 golden frame、非法枚举、状态位组合不变量或长度/版本畸形帧。
- `test_robot_driver.cpp` 包含 Connection、Disconnection、ReadRobotState 测试。mock 以约 4 ms 周期发送递增序号状态；ReadRobotState 测试覆盖停止 mock 后状态超时、重新启动 mock 后恢复读取。
- 该 mock 恢复测试没有执行 RobotDriver 的真实 disconnect/reconnect，也没有模拟 VAL3 的错误复位、`l_nPreviousCmdMode=0` 后 STOP 重新武装、直接运动模式重入、重复序号重传或故障状态发布时序。
- 在固定提交的测试目录检索范围内，未发现对 `StaubliHardwareInterface::update_state()`、supervision 状态接口与 VAL3 `controlTask` 跨语言状态机的集成测试。此次仅检查测试源码，未实际运行测试。

## 5. 验收矩阵

| ID | 验收项 | 本轮状态 | 证据边界 |
| --- | --- | --- | --- |
| SF1 | VAL3 bit flags → C++ RobotState字段映射 | 静态核对完成 | 源码逐项对应，未执行VAL3实测 |
| SF2 | C++字段 → supervision state interfaces映射 | 静态核对完成 | 字段赋值/导出名称匹配，未运行ros2_control |
| SF3 | bInMotion / bMotionPossible / brakes_released语义 | 静态缺口已确认 | 需要控制器API与型号安全信号定义确认 |
| SF4 | bInError / control_state发布时序 | 静态缺口已确认 | 周期级实测未执行 |
| SF5 | 错误复位后的STOP重新武装顺序 | 静态推导完成 | 尚未在隔离控制器/CS9复现 |
| SF6 | 请求模式与反馈模式/命令接受闭环 | 静态缺口已确认 | 无ACK/接受状态；动态控制器行为未验证 |
| SF7 | 重复/乱序/回绕状态序号与新鲜度 | 静态缺口已确认 | 重复帧、序号回退和故障注入未执行 |
| SF8 | stale read后的ROS状态失效语义 | 静态缺口已确认 | ros2_control消费者行为未实测 |
| SF9 | VAL3↔C++跨语言黄金帧与状态真值表 | 未执行 | 需要共同协议向量/VAL3导出帧 |
| SF10 | 故障后直接位置/速度重入与STOP重武装测试 | 未执行 | 需要mock/VAL3控制流测试 |
| SF11 | STOP响应、静止回读、状态时序与安全链 | 未执行 | 需要CS9/机器人及安全工程证据 |
| SF12 | SIL/HIL/FAT/SAT/实机验收 | 未执行 | 无测试记录或现场证据 |

## 6. 整改建议

1. **建立明确状态模型。** 将物理安全状态、控制器运行错误、命令模式、命令接受状态、机器人运动状态分开定义；区分“无活动命令/STOP/INVALID/通信未就绪”，避免用同一枚举表达空闲和故障。
2. **调整状态快照时序。** 对本轮命令接收、模式判定、错误处理和停止动作形成一致的状态快照；故障事件使用锁存计数/事件序号或独立诊断事件，不得依赖短暂布尔值跨周期可见。
3. **定义恢复握手。** 明确故障复位后是否要求STOP预备命令、控制器接受回执、状态确认、用户/安全重启授权和重新进入运动模式；把握手步骤与超时、失败转移和日志一起实现。
4. **补齐新鲜度与会话约束。** 不把重复序号的重发当作新状态；建立乱序/重放窗口、回绕边界与session epoch；恢复后要求至少一帧属于新会话且满足严格新鲜度条件。
5. **导出状态有效性。** 为状态接口提供valid/stale与接收时间/序号信息；read失败时显式使缓存失效或保证上层生命周期不会消费旧值，并在文档中规定缓存语义。
6. **建立跨语言和状态机测试。** 以VAL3实际编码布局建立golden frame；覆盖各安全状态、状态位组合、无命令空闲、STOP、位置/速度模式切换、错误复位、重复帧、丢包、回绕、重新连接及STOP回读。
7. **安全状态单独验收。** `motion_possible`、`brakes_released`、`in_motion` 不得未经控制器/安全链定义就作为安全许可或静止证明；由安全负责人依据对应机器人型号与控制器安全功能确认。

## 7. 本轮验证边界与结论

本轮只完成固定上游提交的静态源码、现有测试源码和接口文档核对。未执行 C++ 构建/单元测试、VAL3 Studio 导入/编译/下载、VAL3逐周期监测、ROS topic/state-interface运行观测、UDP重复/乱序帧注入、恢复状态机自动化测试、CS9停止/静止回读、SIL/HIL、FAT/SAT或实机验收。

**结论：** 字段位映射和ROS supervision接口导出在静态代码层面基本一致；但反馈语义、发布时序、空闲/错误模式区分、恢复后STOP重新武装、新鲜度判定及状态失效传播存在需要整改或补证的缺口。本轮不构成驱动功能通过、控制器安全验证通过或工程验收通过。未修改上游仓库，未执行或应用 PR，`TODO-EXT-001` 未授权合并。

## 8. 下一节点

**§9.3.275 / SERVO-858：** 状态有效性、停止确认与跨层生命周期故障恢复验收设计。重点把本轮发现转换成状态真值表、时序图、自动化测试用例和CS9现场验收步骤。
