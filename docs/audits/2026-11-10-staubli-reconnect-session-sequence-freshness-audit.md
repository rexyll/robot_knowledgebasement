# Stäubli ROS 2—断线恢复、会话重同步与命令/状态序号新鲜度审计

- 审计节点：§9.3.268 / SERVO-851
- 日期：2026-11-10
- 固定上游：`ICube-Robotics/staubli_driver_ros2@bd658e2d266e315d2ee35f985fb352ea88306b79`
- 审查方式：固定提交静态源码与现有测试代码审查；未执行动态测试。
- 范围：C++ RobotDriver、RealTimeSocketSubscriber/Interface、UDP socket、StaubliHardwareInterface；VAL3 controlTask、computeSequenceDelay、getNextSequenceNumber、decodeRobotCommandMsg；相关RobotDriver与socket subscriber单元测试。

## 1. 主要结论

### 1.1 ROS状态帧的“新消息”标志没有成为RobotDriver状态有效性门禁

1. `RealTimeSocketSubscriber::update_message()`对每一份成功反序列化的数据报都会设置本地`reception_timestamp=now()`并覆盖latest-value message buffer；没有先根据序号判重、拒绝旧序号或验证会话标识。
2. `read_message()`在序号与上次读取相同的情况下，将`status.new_message=false`，但仍返回true，并继续计算接收时间；`RobotDriver::read_robot_state()`只检查`read_message`返回值、消息类型和staleness timeout，没有检查`status.new_message`。
3. 因而，重复发送相同序号但每次都能成功反序列化的数据报，会持续刷新本地接收时间；上层状态读取可能继续把该序号的旧状态视为未过期。该路径是静态代码推断，尚未通过重复数据报注入复现。
4. 这并不证明机器人一定会继续运动：VAL3侧还有基于状态序号与命令序号差值的延迟门禁；但ROS侧“新鲜状态”判断不能独立证明收到的是推进中的新状态帧。

### 1.2 较小序号被直接按uint16回绕处理，缺少乱序/重放窗口

1. Subscriber仅区分大于、等于、小于上次读取序号三种情况；小于时一律按uint16回绕计算丢包数，没有判断这是合法回绕还是网络乱序、旧包重放或控制器重启后序号回退。
2. `MAX_FRAME_SEQUENCE_NUMBER=65535`，VAL3 `getNextSequenceNumber`在65535后回到0；ROS端把任何较小序号都解释为wrap-around。没有最大前向窗口、重放拒绝、boot/session epoch或重启标记。
3. 例如上次读取序号为40000，随后收到较小序号20000，当前算法会按回绕计算丢包，而不是将其判为可疑回退。是否被更上层拒绝取决于后续逻辑；RobotDriver仅记录/忽略丢包数，不以该状态拒绝帧。
4. 16-bit序号只适合短窗口内的顺序/丢包统计，不能单独充当连接身份或重放保护。

### 1.3 断开清理了部分RobotDriver状态，但新连接没有会话级连续性验证

1. `RobotDriver::disconnect()`先销毁control interface和diagnostics subscriber，再停止接收线程/断开socket，最后调用`reset_data()`。该函数将`last_valid_sequence_id_`和两个消息对象的sequence/message_type清零或置INVALID。
2. 新建`RealTimeSocketSubscriber`会重新初始化`last_read_sequence_number_=0`、`first_read_=true`；所以正常完整disconnect/reconnect路径会重置ROS端序号基线，而不是跨会话保留旧序号。
3. 但重置基线后第一份可反序列化报文被当作first read，不要求序号相对上次会话连续，也没有controller boot ID、session nonce、epoch或挑战应答；旧数据报若在新socket接收路径上到达，无法仅靠first_read机制识别其所属会话。
4. UDP socket的`is_connected_`只表示本地socket已打开并完成本地connect配置；UDP没有面向远端的连接握手。远端掉电/断网不会自然令该本地标志变false，因此`RobotDriver::is_connected()`不能识别所有远端失联场景。
5. connect阶段等待有效状态帧并检查协议版本，但该检查不是跨会话认证；诊断通道读取仍为TODO。源码未见重连session/epoch核验或重新授权控制权的挑战应答流程。
6. `RobotDriver::connect()`仅在本地socket仍标记connected时先调用disconnect；若底层socket状态和interface对象状态不一致，异常分支/析构顺序仍需测试覆盖。

### 1.4 VAL3侧序号差计算有回绕修正，但不是重放保护

1. VAL3状态序号每个4ms控制周期递增，超过65535回到0；controlTask启动时将本地状态序号初始化为0。
2. `computeSequenceDelay`计算`nLastSequenceSent - nLastSequenceReceived`；仅当差值小于-60000时加65536作为uint16回绕修正。其他负值保留为负数，并由controlTask触发错误/STOP。
3. 该算法用于估算ROS命令相对当前状态序号的滞后，不包含会话ID、命令唯一ID、重放窗口或新鲜命令挑战应答。旧会话命令如果在重启后序号差刚好落入可接受区间，静态代码不能证明其一定被拒绝。
4. `decodeRobotCommandMsg`检查消息类型并解码字段，但未发现它独立拒绝重复/回退序号；序号差检查发生在controlTask后续路径中。VAL3在无新命令时的旧命令staleness逻辑仍是TODO（SERVO-850）。

### 1.5 ROS发送命令序号绑定最新RobotState序号，而非独立命令计数器

1. HardwareInterface的`write()`将`cmd_msg.header.sequence_number`设为`robot_driver_->get_current_message_sequence()`，即最近一次被RobotDriver接受的状态帧序号。
2. 若read循环重复使用同一份缓存状态（在staleness timeout内），write会继续发出相同状态序号的命令；VAL3的sequence delay随后反映该命令相对当前控制器状态的滞后。
3. 该设计将状态帧推进、命令节拍和命令新鲜度耦合在一起。它没有独立命令序号、客户端session标识或恢复后首次命令握手；不应把它当成可靠的命令去重/重放机制。
4. 命令模式切换会将位置命令初始化为当前读取关节位置、速度/加速度命令清零；但`on_activate()`只将控制模式设为STOP，未清除全部GPIO命令缓存或执行会话重置协议。

### 1.6 现有测试未覆盖重连会话、重复帧刷新与旧帧重放

1. `test_rt_socket_interface.cpp`覆盖接收一帧、重复读取同一缓存消息时`new_message=false`、等待超时后staleness、序号跳跃丢包计数；未覆盖重复发送相同序号的数据报并观察时间戳刷新，也未覆盖回退序号、乱序、旧帧重放或回绕边界。
2. `test_robot_driver.cpp::ReadRobotStateTest`停止mock状态发送器，等待600ms使状态过期，然后重启mock发送器并确认读取恢复；该测试没有断开/重建RobotDriver连接，因此不验证disconnect/reset/reconnect的会话边界。
3. 该测试fixture的mock发送序号是函数内static计数器，停止再启动mock发送线程不会重置序号；因此它也没有覆盖VAL3重启后序号归零的场景。
4. 现有测试未见网络延迟旧包、远端重启、UDP本地socket仍connected但远端已失联、重复数据报刷新接收时间、恶意/意外发送源等注入。

## 2. SERVO-851验收矩阵

| ID | 验收项 | 状态 |
|---|---|---|
| SS1 | Subscriber接收时间戳刷新与latest-value覆盖 | 固定提交静态审查完成 |
| SS2 | same-sequence消息标志及RobotDriver门禁 | 静态确认new_message=false未被RobotDriver检查 |
| SS3 | duplicate datagram刷新状态新鲜度 | 静态确认可疑路径；未注入复现 |
| SS4 | 低序号/乱序/重放与uint16回绕区分 | 静态确认缺少窗口与会话标识 |
| SS5 | disconnect/reset_data及subscriber重建 | 固定提交静态审查完成 |
| SS6 | UDP本地连接状态与远端存活性 | 静态确认没有远端握手/心跳等价保证 |
| SS7 | reconnect首帧/协议版本/控制权重新取得 | 静态确认有首帧和版本检查；会话认证缺失 |
| SS8 | VAL3状态序号回绕及sequence delay | 固定提交静态审查完成 |
| SS9 | VAL3命令重复/回退/跨会话重放拒绝 | 未发现独立防重放；动态边界未执行 |
| SS10 | ROS命令序号与状态序号耦合 | 固定提交静态审查完成 |
| SS11 | 模式切换和activate命令缓存复位 | 部分静态审查；GPIO缓存清理缺失沿用既有发现 |
| SS12 | 现有单测覆盖范围 | 固定提交测试源码审查完成 |
| SS13 | duplicate/reorder/replay/reboot故障注入 | 未执行 |
| SS14 | CS9/VAL3重启与网络恢复验证 | 未执行 |
| SS15 | SIL/HIL、FAT/SAT、实机安全验收 | 缺少证据，未执行 |

## 3. 整改建议

1. 将接收序号处理改为明确的模16位滑动窗口：分别处理正常前进、合法回绕、重复、乱序、过旧、超前异常；重复/回退帧不得刷新“有效新鲜状态”时间戳。
2. 在`RobotDriver::read_robot_state()`中将`status.new_message`、序号推进结果和消息时间戳作为状态有效性条件；重复缓存可供非控制诊断显示，但不得被视为新的控制反馈。
3. 接收数据报时先验证远端IP/端口，再反序列化并更新状态；意外来源、非法序号和旧会话帧必须丢弃并计数。UDP来源验证不等同于密码学身份认证。
4. 在协议头或握手层增加controller boot ID/session epoch及ROS client session nonce；控制器重启、驱动重连或socket重建时重新协商会话，拒绝旧epoch的状态与命令。
5. 建立独立的命令ID/状态ID关系和ack语义；VAL3必须校验命令所属会话、序号窗口、有效期限及控制权状态，不能只用状态序号差估算滞后。
6. 远端失联检测使用经验证的heartbeat/状态超时；区分本地UDP socket open、收到有效新帧、控制器会话有效、控制权已授权四个状态。
7. 重连恢复默认进入STOP/UNARMED：清理旧命令和GPIO缓存，等待新会话首帧、型号/协议兼容检查、控制器READY与新鲜状态；要求显式重新授权后才允许运动命令。禁止自动重放断线前的最后一个运动命令。
8. 扩展单测：重复序号不同payload、相同帧高频重放、乱序/回退、65534→65535→0→1回绕、控制器重启归零、旧epoch帧、远端IP/端口伪造、断线重连及缓存清理；增加属性测试和模糊测试。
9. 在隔离网络和CS9上验证实际UDP缓冲/延迟/重排、VAL3序号复位时机、重连后首命令策略；随后再执行SIL/HIL与FAT/SAT。

## 4. 验证边界与结论

本轮仅审查固定提交源码与现有测试代码。未运行ROS 2构建/单测，未执行duplicate/reorder/replay注入、UDP抓包、远端控制器重启、socket断线重连、VAL3编译下载、CS9仿真、SIL/HIL、FAT/SAT或实机验证。重复帧导致状态新鲜度被刷新是静态路径推断，尚未动态复现；旧会话帧能否在特定时序下被接受也需隔离故障注入确认。

未修改上游仓库，未应用PR。Stäubli工程级验收仍未通过；`TODO-EXT-001`未授权合并。根00-01与第21章21-02继续进行中。

**下一节点：§9.3.269 / SERVO-852。**
