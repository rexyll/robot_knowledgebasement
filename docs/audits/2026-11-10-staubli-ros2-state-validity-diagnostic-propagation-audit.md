# Stäubli ROS 2—状态有效性与通信安全诊断接口端到端审计

- 审计节点：§9.3.279 / SERVO-862
- 日期：2026-11-10
- 固定上游：`ICube-Robotics/staubli_driver_ros2@bd658e2d266e315d2ee35f985fb352ea88306b79`
- 范围：RobotDriver状态读取/失效路径、StaubliHardwareInterface::read/update_state/write、prepare/perform command mode switch、导出的joint/supervision/GPIO state interfaces、诊断订阅/连接就绪判断、现有RobotDriver与HardwareInterface测试。
- 方法：固定提交源码及测试源码静态审查；未运行构建、单测或ROS运行时注入。

## 1. 执行摘要

本轮确认状态有效性在RobotDriver、ros2_control HardwareInterface、导出StateInterface与命令模式准入之间没有端到端失效闭环。RobotDriver遇到无数据/过期数据/无效消息时返回false，但保留current_robot_state_中上一次消息的有效message_type；HardwareInterface::read()收到false仅返回ERROR，不清除state_msg_或已导出的关节/supervision缓存；perform_command_mode_switch()只依据缓存的error_state与motion_possible准入位置模式，不检查最近一次成功读取时间、状态序号前进或会话状态。update_state()还会在验证所有必需字段前逐段写入状态缓存，缺少原子提交。

此外，连接阶段诊断就绪仍被硬编码为true，read_diagnostic_data()未被调用；SupervisionGpio导出接口没有state_valid/state_age/source/authentication/error_reason等独立有效性字段。现有测试有RobotDriver staleness检测，但没有验证HardwareInterface在stale/read error后是否清除导出缓存、拒绝模式切换或阻止继续写入命令。

## 2. 主要发现

### F1—RobotDriver读取失败不会使当前状态对象失效（高）

`RobotDriver::read_robot_state()`在control interface未ready、read_message失败、message type无效或time_since_received超过timeout时直接返回false。只有成功路径才将`state= current_robot_state_`并更新last_valid_sequence_id_。失败路径没有把`current_robot_state_.header.message_type`置为INVALID，也没有清除/标记当前快照的validity。reset_data()确实会将状态与诊断message_type置INVALID，但read失败不会调用reset_data()。

`is_state_msg_valid()`只比较current_robot_state_.header.message_type是否为ROBOT_STATE，不检查状态时间戳、序号新鲜度、来源、认证或session epoch。注意：read_robot_state的staleness判断仍会返回false，因此调用方能获知本次读取失败；风险在于对象内部有效标志和其它缓存没有同步失效。

### F2—HardwareInterface::read返回ERROR，但不失效已导出状态缓存（高）

`StaubliHardwareInterface::read()`在未连接、RobotDriver读取失败或update_state失败时返回hardware_interface::return_type::ERROR；这些分支均未清除`state_msg_`、`hw_joint_positions_`、`hw_joint_velocities_`、efforts、GPIO或`supervision_gpio_copy_`。ROS 2 StateInterface仍然指向这些内存地址。由此，读周期失败后导出的状态内存仍保留上一份成功数据，状态消费者必须正确处理read错误，不能仅凭接口数值认定其仍新鲜。

该结论不等于controller_manager一定会继续执行控制器；其具体调度响应取决于ros2_control版本、硬件组件错误策略和上层配置，需运行时验证。源码没有提供每个StateInterface自带的valid标志。

### F3—位置模式准入检查缓存安全位，不检查新鲜度/序号/通信会话（高）

`perform_command_mode_switch()`在切换到JOINT_POSITION时只检查`state_msg_.error_state`和`state_msg_.motion_possible`，并在通过后更新current_control_mode_。它没有确认：
- state_msg_是否来自最近一次成功read；
- 最近一次状态的本地接收年龄是否仍小于timeout；
- sequence number是否相对上一次有效状态前进；
- 连接/接收线程是否在本次read之后断开或重启；
- 来源端点、协议字段、认证和session是否有效。

因此，若此前存在一份error_state=false、motion_possible=true的成功快照，随后read失败/状态过期，而模式切换调用仍然到达该函数，源码门禁本身可能基于旧快照准入。此为控制流条件推导，实际生命周期/控制器管理器调度是否形成可利用时序需SIL/HIL验证。

### F4—write路径没有独立状态新鲜度门禁（高）

`write()`检查robot_driver_连接状态；非STOP模式下检查缓存`state_msg_.error_state`与`state_msg_.control_state == INVALID`，但不检查状态年龄、sequence推进、last read result或session有效性。write随后从缓存的current_control_mode_构造命令并发送。因而在前一周期read失败而调用序列仍进入write的情况下，write自身不会基于read失败标志或状态年龄拒绝非STOP命令；它依赖缓存状态和上层对read ERROR的处理。

本项只确认write自身缺少独立门禁，不推断所有controller_manager配置都会在read ERROR后继续调用write。必须用目标ROS 2发行版和实际controller_manager配置做时序实验。

### F5—update_state非原子更新，失败会留下混合时间快照（高）

`update_state()`先检查has_joint_positions并立即写入关节位置，再检查has_joint_velocities并写入关节速度。如果速度字段缺失，函数此时返回false；但本周期位置已更新，速度/effort/GPIO/supervision仍可能来自上一个成功周期。read()返回ERROR不会回滚前面写入的关节位置。数字/模拟GPIO valid flag缺失时则不更新对应缓存，继续保留旧值。

整改应先完整验证所有必需字段、有限数值、范围与有效标志，再将一份完整RobotState快照原子提交到缓存；任何失败都应使整个快照invalid，而不是部分写入。

### F6—supervision状态接口缺少独立数据有效性和通信诊断字段（中/高）

导出的SupervisionGpio字段包括operation_mode、operation_mode_status、safety_status、control_sequence_delay、brakes_released、motion_possible、in_motion、in_error、estop_pressed、wait_for_ack。没有state_valid、state_age、last_successful_sequence、source_endpoint、authentication/session状态、protocol_error、rejected_packet_count、diagnostic_valid或diagnostic_age。

这使消费方只能看到状态值，不能从同一接口确认该值是否来自当前有效快照。现有SafetyStatus/estop/brakes语义压缩问题已在SERVO-852等节点记录，本轮不重复作为新发现。

### F7—诊断链路未参与连接就绪与运行期有效性闭环（高）

`RobotDriver::connect()`建立diagnostics subscriber并检查subscriber本地is_ready()，但等待首帧循环将`diag_interface_ready = true`硬编码，且read_diagnostic_data调用仍为TODO注释。连接成功并不证明控制器诊断帧已经到达。read_diagnostic_data()本身有message type与staleness检查，但未被连接握手或HardwareInterface::read()使用。连接时日志打印current_diagnostic_data_默认固件版本字段，且CS9型号/VAL3兼容检查被注释/TODO（前序SERVO-852已记录）。

### F8—现有测试没有覆盖硬件层状态失效传播和模式拒绝（中/高）

RobotDriver测试包含停止mock发送后等待超过staleness timeout，再确认read_robot_state返回false，随后恢复发送再成功读取。这只验证RobotDriver API的返回值，不验证current_robot_state_内部有效标志失效或HardwareInterface导出状态被清除。

HardwareInterface测试覆盖接口导出、生命周期与一次成功read/write；LifecycleTransitions没有在读取成功后停止mock、制造stale状态，再检查state interfaces invalidation、位置模式切换拒绝和write阻断。测试也没有验证update_state在缺少velocity字段时不得部分提交。

## 3. 端到端状态机缺口

当前可观察的路径：
1. UDP subscriber收到/反序列化数据，缓存最新消息并记录本地接收时间。
2. RobotDriver::read_robot_state读取消息，检查message_type及staleness；失败则返回false，但不统一失效内部快照。
3. HardwareInterface::read调用RobotDriver；失败返回ERROR，但不清除state_msg_与已导出的state interface缓存。
4. update_state逐字段更新；缺少必需字段时可能在中途返回false，留下部分更新。
5. perform_command_mode_switch/write使用state_msg_缓存安全位；没有独立freshness/valid/session门禁。
6. ROS导出supervision字段不含有效性、年龄、来源、认证和异常计数；诊断数据未进入read/connect readiness闭环。

建议实现统一的状态快照契约：每帧携带单调接收时间、严格前进序号、会话epoch、来源与认证结果、协议校验结果、required-fields/finite/range校验结果；仅在所有检查通过时原子更新snapshot。read失败立即置invalid；位置/速度模式准入与每次非STOP write均需检查snapshot valid与age。无效时明确进入STOP/故障处理流程，但不得把软件STOP当作安全认证或物理静止证明。

## 4. 整改优先级

| 优先级 | 整改项 | 验收条件 |
|---|---|---|
| P0 | 统一状态快照validity与失效传播 | 任意read失败、stale、协议/来源/认证失败立即使snapshot invalid；所有导出状态具有可观察有效性 |
| P0 | 模式切换及write新鲜度门禁 | 仅使用当前session内、序号前进、年龄合格且完整验证的快照准入；write每周期重新检查 |
| P0 | update_state原子提交 | 缺失字段、NaN/Inf、越界或invalid flag不得部分修改任意导出状态 |
| P1 | ROS状态/诊断接口扩展 | 暴露valid、age、sequence、session、source/auth status、错误原因与计数 |
| P1 | 诊断帧连接握手与运行期监控 | 连接就绪要求真实有效诊断帧或明确降级配置；诊断stale/缺失可观测并传播 |
| P1 | 生命周期恢复与缓存重置 | activate/deactivate/cleanup/reconnect统一重置快照、命令缓存与状态有效性 |
| P1 | 端到端测试 | mock、ROS integration、SIL/HIL覆盖stale、disconnect、malformed、partial fields、mode switch/write拒绝 |

## 5. 验收矩阵

| ID | 场景 | 预期结果 | 状态 |
|---|---|---|---|
| SV-01 | 首帧正常状态 | 所有必需字段一次性提交，valid=true | 未执行 |
| SV-02 | 状态超过staleness timeout | snapshot invalid，所有接口可观察失效 | 未执行 |
| SV-03 | subscriber无新帧/read失败 | 缓存不再被标为有效，非STOP命令被阻断 | 未执行 |
| SV-04 | UDP断线后仍有旧state_msg_ | 模式切换拒绝，write不得继续运动命令 | 未执行 |
| SV-05 | 序号重复/倒退/旧session帧 | 不刷新freshness，不提交状态 | 未执行 |
| SV-06 | 错误来源/认证失败/畸形协议帧 | 状态invalid，原因和拒绝计数可见 | 未执行 |
| SV-07 | has_joint_positions=true、has_joint_velocities=false | 不得只更新位置；整帧拒绝并失效 | 未执行 |
| SV-08 | has_joint_velocities=true、positions=false | 不提交任何状态字段 | 未执行 |
| SV-09 | 必需字段包含NaN/Inf/越界值 | 整帧拒绝，无部分缓存更新 | 未执行 |
| SV-10 | read返回ERROR后执行position mode switch | 明确拒绝，不能用旧motion_possible准入 | 未执行 |
| SV-11 | read成功后状态变stale、随后调用write | 非STOP write拒绝并触发经定义的故障流程 | 未执行 |
| SV-12 | GPIO valid flag缺失 | 明确invalid/unknown，不静默保留旧值而不标注 | 未执行 |
| SV-13 | 诊断端口无帧但control状态正常 | 连接结果按明确required/optional策略处理，不硬编码ready | 未执行 |
| SV-14 | 诊断帧stale/错误/无认证 | diagnostics validity与原因向ROS层传播 | 未执行 |
| SV-15 | cleanup/reconnect/activate | 旧快照、旧session与旧命令不跨生命周期复用 | 未执行 |
| SV-16 | ROS controller_manager read ERROR时序 | 在目标发行版明确记录read/write/controller行为及安全策略 | 未执行 |

## 6. 证据边界

已完成：固定提交中RobotDriver、HardwareInterface、状态接口导出、mode switch/write、诊断连接ready路径及现有测试源码静态审查。

未执行：C++构建/单测、ROS 2运行时、controller_manager错误传播时序、mock stale/断线/部分字段注入、接口缓存观测、模式切换拒绝、write阻断、诊断丢帧、VAL3/CS9、SIL/HIL、FAT/SAT及实机测试。没有对任何安全功能或物理停止能力作认证结论。

未修改上游源码，未提交上游PR，未合并或关闭`TODO-EXT-001`。

## 7. 参考源码路径

- `staubli_robot_driver/src/robot_driver.cpp`
- `staubli_robot_driver/include/staubli_robot_driver/robot_driver.hpp`
- `staubli_robot_driver/src/staubli_hardware_interface.cpp`
- `staubli_robot_driver/include/staubli_robot_driver/staubli_hardware_interface.hpp`
- `staubli_robot_driver/test/unit_tests/test_robot_driver.cpp`
- `staubli_robot_driver/test/unit_tests/test_staubli_hardware_interface.cpp`
- `staubli_robot_driver/src/communication/messages.cpp`
- `staubli_robot_driver/src/communication/real_time_socket_subscriber.cpp`

## 8. 节点状态

SERVO-862固定提交静态审查完成；SV-01至SV-16验收矩阵全部未执行。P0状态快照失效传播、模式准入/写入新鲜度门禁和原子状态提交均未解决。下一节点：§9.3.280 / SERVO-863，审查ROS 2控制器管理器错误处理、生命周期状态转换与驱动read/write故障策略的运行时契约。
