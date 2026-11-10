# Stäubli ROS 2—状态有效性、STOP确认与跨层生命周期故障恢复验收设计审计

- **审计编号：** SERVO-858
- **章节节点：** §9.3.275
- **日期：** 2026-11-10
- **审查基线：** `ICube-Robotics/staubli_driver_ros2@bd658e2d266e315d2ee35f985fb352ea88306b79`
- **目标分支：** `rexyll/robot_knowledgebasement:main`
- **审计性质：** 固定提交静态源码、测试源码与ROS 2官方生命周期契约核对；本报告定义验收设计，不执行故障注入或实机动作。

## 1. 目标与审查范围

本节点把SERVO-856/857的状态、STOP和恢复发现转化为跨层验收设计，重点回答：

1. read/write返回ERROR后，ros2_control生命周期状态是否与实际网络/硬件资源状态一致？
2. STOP是仅完成本地UDP发送，还是获得控制器接收/执行/停止确认？
3. cleanup、shutdown、on_error及activate是否处理状态失效、停止和资源关闭？
4. mode switch是否使用足够新鲜的状态作为运动准入依据？
5. 现有mock与单元测试是否真正覆盖运动命令、STOP回执及错误恢复？

核对文件：

- C++ `staubli_hardware_interface.cpp/.hpp`、`robot_driver.cpp/.hpp`、`real_time_socket_interface.hpp`、`mock_robot_server.cpp`。
- 测试 `test_staubli_hardware_interface.cpp/.hpp`、`test_robot_driver.cpp`。
- 驱动文档 `quickstart/overview.rst`、`quickstart/bringup.rst`。
- ROS 2 Humble官方硬件组件生命周期/错误处理文档：
  https://control.ros.org/humble/doc/ros2_control/hardware_interface/doc/hardware_components_userdoc.html

## 2. 核对出的实现事实

### 2.1 STOP调用链的真实保证范围

`RobotDriver::send_stop_all_command()` 构造STOP及清零IO的命令，给命令填入最近有效状态序号，然后调用 `control_interface_->send_message()`。该函数返回值最多表示本地消息序列化/套接字发送函数报告成功；当前协议消息类型只有RobotState、RobotCommand和DiagnosticData，没有独立的STOP ACK/command-result消息，也没有等待状态帧确认对应STOP序号的闭环。

因此必须区分：
- STOP命令对象已构造；
- 本地发送接口报告成功；
- 控制器收到命令；
- 控制器接受并切换到STOP；
- 机械臂停止运动；
- 停止状态持续满足规定的静止判据。

当前代码中的bool发送结果不等价于后面五项。RobotState可能提供控制模式、in_motion等反馈，但当前实现未将该反馈与STOP命令做唯一关联，也没有稳定时间/静止阈值的验收规则。

### 2.2 各生命周期回调的停止/资源动作并不对称

- `on_activate()` 只把本地 `current_control_mode_` 设为STOP，未在回调内同步发送STOP，也未等待控制器STOP反馈。
- `on_cleanup()` 只调用 `robot_driver_->disconnect()`，不先发送STOP，也忽略disconnect返回值。
- `on_shutdown()` 仅当缓存的 `state_msg_.control_state != STOP` 时发送STOP；不检查该缓存的新鲜度或 `state_msg_.in_motion`，且忽略STOP发送与disconnect返回值，最后无条件返回CallbackReturn::SUCCESS。
- `on_error()` 在driver已连接时调用STOP但忽略返回值，随后返回CallbackReturn::SUCCESS；没有disconnect、reset_data或显式状态失效动作。driver未连接时返回CallbackReturn::ERROR。
- `write()` 的错误状态分支及NaN分支也会尝试发送STOP，但忽略STOP发送结果后返回return_type::ERROR。
- `read()` 因连接失败、状态读取失败或字段不完整而返回ERROR；只有成功路径才调用update_state，因此失败不会主动清零/失效上一次的joint与supervision缓存。

### 2.3 ROS 2生命周期契约与插件资源状态存在错配风险

Humble官方文档规定：硬件组件的 `read()` 或 `write()` 返回 `hardware_interface::return_type::ERROR` 后会调用 `on_error(previous_state)`；若 `on_error` 返回CallbackReturn::SUCCESS，组件转至UNCONFIGURED；若返回ERROR或FAILURE，则进入FINALIZED。文档对UNCONFIGURED的定义是硬件已初始化但通信未启动。

本插件的已连接分支在 `on_error()` 返回SUCCESS前只尝试发送STOP，不调用disconnect。因此静态代码显示，组件生命周期可能已经转至UNCONFIGURED，而RobotDriver控制/诊断socket、接收线程和缓存仍保持已连接/运行状态。该状态与官方UNCONFIGURED通信未启动的定义不一致。此项需在目标ROS 2发行版与实际Controller Manager中验证完整回调顺序，但插件自身没有完成资源清理。

另一个边界是driver未连接时 `on_error()` 返回ERROR；按Humble文档会进入FINALIZED，这不是可自动重试的普通重新配置状态。运维流程需要明确区分可恢复错误与不可恢复错误，不能只看到日志便假定组件会回到可用状态。

### 2.4 shutdown可能依据陈旧STOP状态跳过停止请求

`on_shutdown()` 的STOP发送条件只检查最近一次缓存的 `control_state` 是否不等于STOP；没有检查缓存序号/接收时间，也没有确认 `in_motion=false`。因此，当缓存最后记录是STOP但状态已过期，或控制模式回报STOP而机器人仍处于运动/滑行状态时，代码会跳过STOP发送并断开通信。这里是条件性风险，不等同于已证实的CS9现场运动现象。

### 2.5 运动模式切换使用未附带新鲜度判据的状态缓存

`prepare_command_mode_switch()` 检查模式支持情况；`perform_command_mode_switch()` 在提交位置模式前检查 `state_msg_.error_state` 与 `state_msg_.motion_possible`，并对HOLD状态仅记录warning。该函数没有对状态接收时间、状态序号变化或有效会话代次执行检查。因此，模式切换准入逻辑自身无法证明其使用的是当前新鲜状态。

另外，Humble生命周期文档说明ACTIVE阶段运动命令接口可用；插件 `on_activate()` 仅设置软件模式为STOP，真正的STOP报文依赖后续write周期，而非activate回调内完成的握手。

## 3. 现有硬件接口测试覆盖边界

上游存在 `test_staubli_hardware_interface.cpp`，本轮更正“完全没有HardwareInterface测试”的表述。其覆盖包括Construction、Initialization、Configuration、PluginLoading、InterfaceExport与LifecycleTransitions。

但LifecycleTransitions当前实际执行顺序为：
1. 启动mock并configure；
2. activate，插件将 `current_control_mode_` 设为STOP；
3. read一次并检查关节状态；
4. 修改position command interface数值；
5. 直接调用write，没有调用 `prepare_command_mode_switch()` 与 `perform_command_mode_switch()`。

因此该测试中的write仍使用STOP模式；修改位置命令并未使其进入JOINT_POSITION发送分支。测试只断言write返回OK，没有读取mock端收到的RobotCommand并检查类型/序号/值，也没有检查控制器反馈或停止状态。

测试fixture循环发送RobotState与DiagnosticData；虽然MockRobotServer提供 `get_last_received_command()` 接口，当前该测试没有调用它来确认收到的命令。测试文件未覆盖on_error、on_shutdown、cleanup失败、STOP发送失败、状态缓存失效或错误后的重新配置。RobotDriver测试覆盖mock连接/断开和状态staleness/重启，但不是HardwareInterface跨生命周期STOP恢复测试。

## 4. 主要审计发现

### LF1｜on_error成功返回与底层通信资源生命周期不一致

插件已连接时 `on_error()` 只尝试STOP，然后返回SUCCESS；未关闭socket/接收线程，也未重置缓存。依Humble生命周期契约，SUCCESS会使组件转入UNCONFIGURED，而该状态定义为通信未启动。

**风险：** 生命周期管理器看到的是已恢复到UNCONFIGURED，但底层驱动可能仍连接且接收线程持续运行；错误恢复与重新configure之间缺少确定的资源收敛点。

### LF2｜STOP发送失败可能被包装成生命周期成功

`on_error()`、`on_shutdown()` 以及 `write()` 内的应急STOP分支没有检查 `send_stop_all_command()` 返回值。on_shutdown还忽略disconnect返回值，并始终返回SUCCESS。

**风险：** 组件回调返回成功并不能代表STOP数据报发送成功、控制器接受命令或机器人静止；失败可能只留在底层日志/返回值而没有推动生命周期进入失败分支。

### LF3｜cleanup/shutdown缺少可证明的“先停止、再断开”顺序

`on_cleanup()` 直接disconnect；`on_shutdown()` 按可能陈旧的 `control_state` 决定是否发STOP，随后立即disconnect，没有等待新状态帧、STOP模式回读、`in_motion=false`或静止持续时间。

**风险：** 失去通信通道前没有可审计的停止确认条件。此审计不主张仅用软件STOP替代安全额定急停或防护系统。

### LF4｜运动模式准入使用无时间戳状态缓存

`perform_command_mode_switch()` 的位置模式准入判断读取 `state_msg_.error_state/motion_possible`，但未检查最后状态是否新鲜、序号是否前进或当前通信会话是否连续。

**风险：** 状态接口缓存仍为“可运动”时，控制模式切换不具备独立的新鲜度证明。应先确认状态有效性，再允许运动命令接口切换。

### LF5｜read失败后旧状态值继续留在接口缓存

`read()` 返回ERROR时不会调用清缓存/失效函数；supervision与joint state内存保持最后一次成功的数值。当前无明确 `state_valid`、`state_stale` 或状态接收年龄接口。

**风险：** 消费者无法只凭导出的状态值区分有效静止状态与通信故障后的旧缓存。ros2_control生命周期可能限制接口消费，但插件自身没有提供失效语义。

### LF6｜现有LifecycleTransitions测试未验证其注释/意图中的位置命令路径

测试激活后 `current_control_mode_` 固定为STOP，没有调用command mode switch；写入position命令后调用write实际仍走STOP分支。mock发送线程没有检查所收命令，测试未验证命令类型和值，也未验证STOP回执。

**风险：** 测试通过只说明该路径返回OK，不能据此证明position command被发送、控制器接收、机器人执行或停止成功。

## 5. 建议的跨层状态模型与停止确认契约

推荐把状态分成独立维度，不要继续用一个布尔量或一个CommandType兼任所有语义：

| 维度 | 建议状态/证据 | 禁止的推断 |
| --- | --- | --- |
| ROS硬件生命周期 | UNCONFIGURED / INACTIVE / ACTIVE / FINALIZED | ACTIVE不等于机器人已安全可动 |
| 通信会话 | DISCONNECTED / CONNECTING / CONNECTED / STALE / SESSION_INVALID | socket connected不等于远端状态新鲜 |
| 状态有效性 | VALID / STALE / INVALID，附接收时间、序号、session epoch | 缓存数值不等于当前状态 |
| 控制器命令状态 | NOT_SENT / SENT / ACCEPTED / REJECTED / UNKNOWN | 本地send成功不等于控制器接受 |
| 运动状态 | MOVING / STOPPING / STANDSTILL_CONFIRMED / UNKNOWN | control_state=STOP不等于机械臂静止 |
| 安全状态 | 控制器安全状态与独立安全回路反馈 | motion_possible不替代安全回路 |

STOP确认应形成可测量的验收条件：
1. 记录触发原因、当前会话代次、命令序号、发送时间及发送结果。
2. 要求控制器侧提供可关联的命令接收/拒绝反馈，或定义可证明的替代确认机制。
3. 在规定超时内接收新鲜状态；确认控制状态/STOP状态符合协议定义。
4. 通过独立于“control_state==STOP”的运动反馈检查静止，并满足规定的连续稳定时间/阈值。
5. 任一步失败均进入STOP_UNKNOWN/FAULT_LATCHED；不得把回调SUCCESS、UDP send true或单帧in_motion=false当作停止成功。
6. 软件STOP与安全额定E-stop、SS1/SS2、防护门和驱动安全链分开验收。

## 6. 建议验收矩阵

下表是后续测试设计，不代表已执行：

| ID | 级别 | 测试动作 | 通过判据/必留证据 |
| --- | --- | --- | --- |
| LFA-01 | 单元 | 模拟RobotDriver未连接时read返回ERROR | on_error转移结果与FINALIZED策略符合部署约定；留下生命周期日志 |
| LFA-02 | 单元 | 模拟STOP发送成功/失败/接口为空 | 发送失败不得被记为STOP已发出或恢复成功；返回值进入错误状态 |
| LFA-03 | 单元 | on_error成功处理 | STOP结果被检查；通信资源按明确策略关闭/保持；生命周期状态与socket/线程状态一致 |
| LFA-04 | 单元 | on_cleanup断开失败 | disconnect失败必须传播，不得无条件报告cleanup成功 |
| LFA-05 | 单元 | on_shutdown时缓存为STOP但in_motion=true | 仍须触发规定的停止/确认策略，不能仅凭control_state跳过 |
| LFA-06 | 单元 | 状态过期后请求位置模式切换 | 准入拒绝；日志包含状态年龄、序号与会话信息 |
| LFA-07 | 单元 | read连续失败后读取supervision/joint接口 | state_valid=false或等价失效传播；旧值不可被误认为当前状态 |
| LFA-08 | 集成mock | 正确执行prepare/perform位置模式切换后写入位置命令 | mock端通过get_last_received_command读取并核对JOINT_POSITION、序号和目标值 |
| LFA-09 | 集成mock | STOP命令发送与反馈 | mock接收命令并回送明确状态确认；核对序号关联、超时和重复STOP行为 |
| LFA-10 | 集成mock | read/write错误触发on_error，再configure/activate | 生命周期、socket、线程、缓存与mode状态完整一致，不遗留上次会话命令 |
| LFA-11 | SIL/HIL | 重复序号、乱序、断线、丢包、STOP丢包及恢复 | 状态新鲜度与STOP_UNKNOWN故障路径可靠；保留抓包、日志、状态时间线 |
| LFA-12 | CS9/实机 | 正常运动、软件STOP、各故障条件下停止回读 | 经批准的机器人型号安全程序测量停止响应、停止距离/时间与静止判据 |
| LFA-13 | 安全验收 | 急停、安全停止、防护设备及通信断开组合测试 | 由合格安全人员按风险评估/安全功能规范签署；不以ROS软件状态代替安全功能证据 |
| LFA-14 | FAT/SAT | 生命周期恢复、网络恢复、控制器重启、重复运行回归 | 完整追踪矩阵、版本/配置、环境、原始日志、异常记录与签字报告 |

所有LFA-11至LFA-14须在隔离的仿真/HIL环境或经风险评估批准的机器人测试区内执行；实机测试必须有适用的机械/电气安全措施和现场授权。本审计未触发任何机器人运动或安全装置。

## 7. 实施优先级

**P0｜先阻断不可信状态/停止结果被上层当成成功**
- 检查并传播所有STOP发送结果；区分sent、accepted、stopped。
- 位置模式准入必须要求state valid、state fresh与会话有效。
- read失败立即使状态有效性失效，避免旧值继续冒充当前反馈。
- shutdown/cleanup明确停止与断开顺序，不以可能陈旧的control_state作为唯一跳过STOP条件。

**P1｜使生命周期与资源所有权一致**
- 设计on_error成功/失败两条明确路径：成功时清理或保持资源的规则必须与UNCONFIGURED语义一致；无法确认停止或资源清理失败时不得报告恢复成功。
- cleanup/shutdown必须检查disconnect结果。
- 激活前完成状态同步与安全准入；激活/模式切换过程禁止复用上次会话缓存。
- 对STOP确认超时建立故障锁存和运维恢复策略。

**P2｜完善测试与交付证据**
- 修订LifecycleTransitions：显式调用prepare/perform模式切换，并在mock端读取命令。
- 为on_error、on_cleanup、on_shutdown、STOP send fail、stale state和重连增加单元/集成测试。
- 建立VAL3/CS9命令接收与运动状态回读的关联证据，补齐SIL/HIL/FAT/SAT记录。

## 8. 验收状态与验证边界

- 已完成：固定上游提交的生命周期函数、状态缓存、模式切换、STOP调用路径、mock server能力和现有HardwareInterface测试源码核对；已根据ROS 2 Humble官方文档核对生命周期状态契约。
- 未执行：C++构建/单元测试、ROS 2 Controller Manager生命周期运行、模拟STOP发送失败、socket线程资源检查、mock命令收发集成测试、VAL3/CS9故障注入、停止响应测量、SIL/HIL、FAT/SAT和实机验证。
- 未证明：控制器是否收到/接受某一STOP、机器人是否达到物理静止、on_error后目标部署运行时是否完全按Humble文档转移、任何安全额定功能的有效性。

**结论：** 当前驱动存在STOP发送结果与生命周期成功状态脱钩、on_error后底层通信资源可能仍运行、cleanup/shutdown缺少可验证停止确认、模式切换未检查状态新鲜度、read失败不失效缓存等缺口。现有HardwareInterface测试覆盖了一部分正常生命周期，但其写入验证仍停留在STOP默认模式，不能作为位置命令或STOP闭环验收证据。本报告给出后续测试设计，不是执行结果或安全认证。

未修改上游仓库，未创建/应用PR，`TODO-EXT-001`未授权合并。

## 9. 下一节点

**§9.3.276 / SERVO-859：** STOP命令接收确认与状态反馈关联协议审计。重点追踪命令/状态序号是否可构造可靠关联、mock/VAL3发送与接收方向、STOP ACK替代机制、状态反馈超时及协议扩展兼容性。
