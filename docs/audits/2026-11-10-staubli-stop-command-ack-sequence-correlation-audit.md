# Stäubli ROS 2—STOP命令接收确认与状态反馈关联协议审计

- **审计编号：** SERVO-859
- **章节节点：** §9.3.276
- **日期：** 2026-11-10
- **审查基线：** `ICube-Robotics/staubli_driver_ros2@bd658e2d266e315d2ee35f985fb352ea88306b79`
- **目标分支：** `rexyll/robot_knowledgebasement:main`
- **审计性质：** 固定提交静态源码、VAL3协议流程与单元测试源码审查；不发送机器人命令、不执行CS9或实机测试。

## 1. 审计目标与范围

核对STOP从ROS 2调用到VAL3接收、执行，再到RobotState返回的协议链路，重点确认：
1. 发送端的成功返回代表哪一层保证；
2. 命令序号是否为独立、单调、可关联的command ID；
3. VAL3是否对命令序号执行去重、乱序拒绝、会话隔离或ACK；
4. RobotState是否回显已接收/接受/执行的STOP命令标识；
5. 现有协议与测试能否证明STOP已送达、被接受或机器人已静止。

核对文件：
- C++：`robot_driver.cpp/.hpp`、`real_time_socket_interface.cpp/.hpp`、`real_time_socket_subscriber.cpp/.hpp`、`communication/protocol.cpp/.hpp`、`communication/messages.cpp/.hpp`。
- VAL3：`controlTask.pgx`、`Comm/computeSequenceDelay.pgx`、`Comm/getNextSequenceNumber.pgx`、`Serialization/decodeRobotCommandMsg.pgx`、`Serialization/encodeRobotStateMsg.pgx`、`Serialization/decodeHeader.pgx`、`Serialization/encodeHeader.pgx`。
- 测试：`test_rt_socket_interface.cpp`、`test_robot_driver.cpp`、`test_message_serialization.cpp`。

## 2. 协议链路事实

### 2.1 本地发送成功的定义

`RealTimeSocketInterface::send_message()` 依次检查本地socket连接、序列化命令、调用 `socket_->send(data_out_)`；只有这三步返回成功才返回true。该函数不等待远端回应，不读取控制器接收队列，不等待状态帧，也不检查机器人运动状态。

`RobotDriver::send_stop_all_command()` 构造STOP命令，把 `header.sequence_number` 设为最近一次有效RobotState的序号，然后调用上述send_message。返回true只代表本地发送函数成功，不代表CS9收到或接受STOP。

### 2.2 当前协议没有独立STOP ACK或命令结果消息

协议头仅含magic number、protocol version、message type、sequence number和payload size。消息类型定义为RobotState、RobotCommand和DiagnosticData。RobotState payload含控制状态、SafetyStatus、operation mode、status flags、joint state等；没有last_received_command_id、last_accepted_command_id、last_completed_command_id、stop_ack或command_result字段。

因此当前RobotState即使回报 `control_state=STOP` 或 `in_motion=false`，也无法将该状态唯一归因到某一条STOP命令；它可能由初始状态、控制器本地操作、上一条STOP或其他状态转换产生。

### 2.3 序号语义是状态帧回显，不是独立命令编号

VAL3每轮通过 `getNextSequenceNumber()` 递增RobotState序号，范围0..65535并回绕。ROS 2读取有效RobotState后保存 `last_valid_sequence_id_`；普通命令和STOP命令都将该最近状态序号写入RobotCommand header。

VAL3 `controlTask` 以当前状态发送序号和收到命令中的序号调用 `computeSequenceDelay()`，计算两者差值（含uint16回绕修正），用于估算ping-pong控制周期延迟。该字段表达命令所依据的最近状态帧年龄/往返节拍，不是每条RobotCommand独立递增的命令ID，也不是控制器ACK。

### 2.4 VAL3不基于命令序号执行ACK/去重/会话检查

固定提交的 `controlTask` 在收到新数据报时调用 `decodeRobotCommandMsg()`；命令有效后，计算sequence delay，并以命令类型/数据执行控制。当前可见控制路径没有：
- 对RobotCommand sequence_number建立last accepted command序号；
- 检查重复命令并返回重复ACK；
- 对乱序/回放命令按命令序列拒绝；
- 将命令序号保存为STOP pending ID；
- 在RobotState中回显命令接受或停止完成标识；
- 连接重建时使用session epoch防止旧会话命令重放。

sequence delay超限可导致错误并转STOP，但这是超时保护路径，不是命令接受回执。

### 2.5 STOP执行反馈是状态快照，不是STOP事务闭环

VAL3在控制循环发布RobotState后才接收并处理本轮命令。收到STOP/进入STOP模式后，执行位置/速度模式停止函数、`stopMove()`和`resetMotion()`；下一周期的RobotState才可能反映新的控制模式或运动状态。当前状态包不包含被处理命令的sequence number/结果码，因此状态只能用于观察机器人状态，不能构成STOP请求与响应的事务关联。

此外，RobotState帧的header sequence是VAL3新生成的状态序号，不是对RobotCommand sequence的echo。C++端读取状态后只更新 `last_valid_sequence_id_`，不与任何待确认STOP ID进行匹配。

## 3. 接收端序号与新鲜度风险

### 3.1 重复/倒退序号仍会刷新本地接收时间

`RealTimeSocketSubscriber::update_message()` 对每个成功反序列化的数据报都设置新的本地 `reception_timestamp` 并写入最新消息缓存，没有先验证sequence number是否前进。

`read_message()` 对相同序号仅设置 `status.new_message=false`，但仍返回true并按该消息的最新reception_timestamp计算age；序号小于上次读取值时按uint16 wrap-around计算lost_packages，不区分真正回绕与乱序/重放。

`RobotDriver::read_robot_state()` 检查消息类型和age，丢包数只作为warning（当前日志被注释），不要求 `status.new_message=true`，因此相同序号的数据报可以刷新状态缓存时间并通过staleness判断。若网络中重复投递/重放旧帧，单靠本地接收时间不能证明状态源持续产生了新状态。

### 3.2 VAL3 command sequence delay也不是严格的重放防护

VAL3 `computeSequenceDelay()` 仅做当前发送序号减命令所带状态序号，并对大幅负数做回绕修正；没有独立的单调性/会话验证。序号差用于延迟阈值判断，不能等同于重复命令拒绝或认证机制。

### 3.3 16位序号回绕缺少会话代次

序号每65536个状态周期回绕至0。协议没有boot/session nonce或连接代次。仅靠16位序号不能区分重连前残留数据报、设备重启后序号重新从0开始、真实回绕和旧帧重放。实际UDP socket/网络设备是否会缓存并重投旧帧需实验确认；静态协议结构本身未提供消歧字段。

## 4. 现有测试覆盖

### 4.1 已有测试覆盖的内容

- `test_rt_socket_interface.cpp`：subscriber初始化、接收状态帧、读取同一缓存消息、等待staleness、丢包计数，以及双向socket接口基本通信。
- `test_robot_driver.cpp`：ConnectionTest、DisconnectionTest、ReadRobotStateTest。
- `test_message_serialization.cpp`：协议消息字段/序列化往返验证。

### 4.2 未覆盖的关键验收点

- 未发现STOP发送后等待远端ACK/接受回执/静止确认的测试。
- 未发现RobotCommand重复序号、乱序、延迟重放、重连旧会话帧测试。
- `ReceiveMessage` 中“再次read同一缓存消息”测试验证 `new_message=false`，不是重复UDP数据报到达后接收时间是否刷新。
- LostPackageDetection测试验证跳号计数，但没有验证乱序包是否拒绝、是否污染最新状态或刷新状态新鲜度。
- 没有序号回绕边界、设备重启后序号重置与session epoch测试。
- MockRobotServer可以通过 `get_last_received_command()` 读取最新命令，但没有完整STOP ACK/command result状态机；mock也不代表CS9的真实协议响应。

## 5. 主要发现

### ACK1｜本地UDP发送成功被上层当作STOP已发送，但没有远端接收证明

`send_message()` 只确认本地序列化和socket send成功。调用链无远端ACK等待或STOP关联回读。

**风险：** 发送成功可能被误读为控制器已接收/接受；网络丢包、对端线程未处理或协议拒绝均无法由返回值区分。

### ACK2｜RobotCommand sequence number不是command ID，RobotState没有回显命令标识

命令header使用最近一次RobotState序号，VAL3将其用于计算控制循环delay；状态帧自身又生成新的独立序号。两方向序号没有形成request/response事务关联。

**风险：** 多条命令可能引用同一状态序号；无法将后续STOP状态与某条特定STOP请求唯一关联，也无法可靠识别命令被重复执行或被新命令覆盖。

### ACK3｜VAL3没有可见的命令去重、乱序拒绝与会话代次保护

控制任务解码有效命令后按模式执行，未建立独立命令接收窗口、last accepted command ID或session epoch。

**风险：** 协议层缺少抵御旧命令重复/乱序的显式机制；sequence delay阈值不是命令去重机制。

### ACK4｜重复/旧状态数据报可刷新接收时间

subscriber在成功反序列化时无条件刷新本地接收时间；相同序号只标记new_message=false，仍可作为read结果；RobotDriver不强制新序号且丢包数不阻断状态更新。

**风险：** 本地staleness检查可能被重复帧“续命”，不能仅凭本地接收时间证明机器人状态源在持续前进。

### ACK5｜16位状态序号无session epoch，重连/重启的旧帧无法协议级消歧

协议仅有uint16序号，VAL3启动时重置序号，控制错误时也会将其重置；没有设备启动ID或连接会话nonce。

**风险：** 回绕、重启、重连与历史数据报可能具有相同序号；当前协议无法为跨会话命令/状态提供强隔离。

### ACK6｜现有通信测试没有覆盖STOP事务和重复/乱序数据报

当前测试只验证基本收发、缓存读取、丢包计数和staleness时间，不验证重复UDP包时间戳刷新、乱序拒绝、STOP ACK、状态回显关联、session epoch或CS9执行结果。

**风险：** 单元测试通过不等于STOP协议具备远端接收确认和静止确认。

## 6. 建议协议增强

### 6.1 独立命令事务标识

每条RobotCommand分配独立的 `command_id`（建议至少32/64位），与RobotState sequence分离。每次连接/控制器启动引入 `session_id/epoch`，所有命令和回执携带同一会话标识。

### 6.2 明确分级回执

建议定义独立CommandAck/CommandResult消息，至少包含：
- `session_id`；
- `command_id`；
- `received/accepted/rejected/executing/completed/failed`状态；
- 拒绝/失败原因码；
- 控制器时间戳或状态序号；
- 当前控制模式与安全状态快照。

STOP请求应具有单独语义；不得只用普通RobotState中的control_state=STOP推断其已被特定STOP请求接受。

### 6.3 STOP完成需独立静止证据

STOP命令ACK只证明控制器对该命令的协议处理阶段，不证明物理静止。还需要新鲜状态帧、运动反馈（关节速度/驱动状态等）和持续时间/阈值判据，形成 `STOP_ACCEPTED` 与 `STANDSTILL_CONFIRMED` 两个独立结果。安全额定停止和急停必须另按安全功能规范验证。

### 6.4 严格处理状态序号与接收新鲜度

- 只有通过magic/version/type/payload校验且sequence严格前进（按定义回绕）并属于当前session的状态帧，才更新“last fresh state”时间。
- 重复帧不刷新新鲜度；乱序/过期帧丢弃并计数。
- 记录接收时间、源序号、session epoch、重复/乱序/丢包计数。
- 设备重启或控制会话重建时先完成握手，旧session命令一律拒绝。
- 对uint16回绕使用明确的模序比较规则与边界测试，避免简单大小比较误判。

## 7. 建议验收矩阵

| ID | 级别 | 测试动作 | 通过判据/证据 |
| --- | --- | --- | --- |
| ACKT-01 | 单元 | send_message成功/失败模拟 | 结果只表达本地发送状态；不得伪报远端ACK |
| ACKT-02 | 单元 | 重复RobotState UDP帧 | 重复帧不刷新last_fresh_state时间，计数器增加 |
| ACKT-03 | 单元 | 乱序/旧序号状态帧 | 不覆盖当前状态、不刷新新鲜度，记录drop原因 |
| ACKT-04 | 单元 | uint16序号65534、65535、0、1 | 按模序规则连续接受；边界外旧帧拒绝 |
| ACKT-05 | 单元 | 相同command_id重复STOP | 控制器幂等处理并回同一事务结果，不重复触发非幂等副作用 |
| ACKT-06 | 单元 | 不同command_id并发/连续命令 | 按明确队列/拒绝策略处理，回执关联不串单 |
| ACKT-07 | 集成mock | STOP发送后延迟/丢弃ACK | 上层进入ACK_TIMEOUT/STOP_UNKNOWN，不宣称已停止 |
| ACKT-08 | 集成mock | ACK accepted但持续in_motion=true | 仅标记STOP_ACCEPTED，不标记STANDSTILL_CONFIRMED |
| ACKT-09 | 集成mock | 新鲜状态回显对应command_id且速度低于阈值持续T_hold | 记录STANDSTILL_CONFIRMED和原始状态时间线 |
| ACKT-10 | 集成mock | 旧session命令在重连后重放 | 拒绝并记录session mismatch |
| ACKT-11 | SIL/HIL | UDP重复、乱序、丢包、延迟、断链、CS9重启 | 命令回执/状态新鲜度与会话隔离满足时限，留pcap及日志 |
| ACKT-12 | CS9/实机 | STOP在位置运动、错误恢复、网络抖动下执行 | 记录CS9日志、命令ID/ACK、状态反馈、外部测量停止时间/距离 |
| ACKT-13 | FAT/SAT/安全 | 软件STOP与安全停止/急停组合验收 | 风险评估、独立安全功能证据、签字测试记录；ROS ACK不代替安全回路证据 |

ACKT-01至ACKT-13均为建议测试项，本审计未执行。

## 8. 验证边界与结论

- 已完成：固定提交C++发送/接收接口、RobotDriver状态序号、VAL3控制循环/序号延迟计算、VAL3消息编解码、协议结构和现有单元测试源码核对。
- 未执行：C++构建/测试、重复/乱序UDP故障注入、网络抓包、VAL3 Studio编译下载、CS9接收回执实验、停止响应测量、SIL/HIL/FAT/SAT或实机验证。
- 未证明：任何STOP命令在CS9上被实际收到/接受；任何机器人已物理静止；任何协议改进已经实现；任何安全额定功能已验证。

**结论：** 当前协议中的sequence number主要用于RobotState周期编号及RobotCommand对最近状态周期的回显/延迟计算，不是独立command ID；RobotState没有命令接收/接受/完成回执字段；发送函数只证明本地socket发送调用成功。接收端对每个可反序列化状态帧都刷新本地接收时间，重复序号虽标记new_message=false，仍可能使旧帧保持表面新鲜。当前缺少命令事务关联、明确ACK、会话代次和严格重复/乱序状态过滤。所有结论为固定提交静态代码事实与风险推导，不等同于CS9现场行为。

未修改上游仓库、未创建/应用PR；`TODO-EXT-001`未授权合并。

## 9. 下一节点

**§9.3.277 / SERVO-860：** UDP接收缓存、状态序号回绕、重复/乱序/重放数据报与新鲜度判定专项审计；重点追踪socket接收线程、RealtimeThreadSafeBox缓存覆盖语义、VAL3 readData、消息序号模序比较和故障恢复后会话重置。
