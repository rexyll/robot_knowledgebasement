# Stäubli ROS 2—ros2_control硬件错误传播、Controller Manager与生命周期状态转换契约审计

- 审计节点：§9.3.280 / SERVO-863
- 日期：2026-11-10
- Stäubli驱动固定上游：`ICube-Robotics/staubli_driver_ros2@bd658e2d266e315d2ee35f985fb352ea88306b79`
- ROS 2 Control参考基线：`ros-controls/ros2_control@c6ef5a24e0cd21463edb99bded552a96f914b716`（Jazzy分支快照；hardware_interface包版本4.50.0）
- 驱动README目标发行版：ROS 2 Jazzy / Ubuntu 24.04；驱动声明仅支持CS9，旧控制器不支持。
- 审计性质：固定提交静态源码、ROS 2 Control Jazzy静态源码、官方生命周期文档和现有测试源码交叉核对；未运行构建、单测或运行时注入。

## 1. 执行摘要

本轮把SERVO-862发现的read失败、write失败和状态缓存失效问题，向外追踪到ROS 2 Control的HardwareComponent、ResourceManager和ControllerManager错误处理路径。

确认以下端到端行为：

1. Stäubli HardwareInterface的read()/write()返回ERROR后，ROS 2 Control的HardwareComponent会触发error()并调用插件on_error()；随后ResourceManager将故障硬件组件的接口从available列表移除。
2. Stäubli on_error()在RobotDriver仍被判定为connected时尝试发送STOP，但忽略send_stop_all_command()的布尔返回值，仍返回CallbackReturn::SUCCESS。Jazzy HardwareComponent因此把组件置为UNCONFIGURED，而不是FINALIZED。
3. 如果RobotDriver已经不connected，Stäubli on_error()返回CallbackReturn::ERROR；Jazzy HardwareComponent把组件置为FINALIZED。此状态不能通过普通configure/activate生命周期服务恢复，通常需要卸载并重新加载插件。
4. on_error()没有调用disconnect()，也没有调用on_cleanup()；成功进入UNCONFIGURED后，RobotDriver的socket和接收线程仍可能保持连接。下一次on_configure()调用connect()时，RobotDriver会检测既有socket并先断开再重连。
5. ResourceManager在组件error后移除接口；ControllerManager随后仍尝试对故障组件执行command mode switch。由于接口已不可用、组件已不在ACTIVE/INACTIVE状态，该切换路径会被拒绝。ros2_control上游Issue #3620记录了这一Jazzy故障处理顺序问题；本轮固定Jazzy源码快照也确认存在相同调用顺序。

因此，不能把ControllerManager的后续mode-switch调用视为故障后的第二次STOP保障。停止请求必须在插件自己的故障处理路径中被妥善处理，但UDP本地发送成功仍不等于CS9接受、执行或物理静止确认。

本轮仅完成静态审计。未执行ROS 2 Control构建、ControllerManager运行时故障注入、CS9、VAL3、SIL/HIL、FAT/SAT或实机测试。

## 2. 固定源码与参考范围

### 2.1 Stäubli驱动源码

重点核对：

- `staubli_robot_driver/src/staubli_hardware_interface.cpp`
- `staubli_robot_driver/include/staubli_robot_driver/staubli_hardware_interface.hpp`
- `staubli_robot_driver/src/robot_driver.cpp`
- `staubli_robot_driver/test/unit_tests/test_staubli_hardware_interface.cpp`
- `staubli_robot_driver/package.xml`
- 仓库README中的ROS 2发行版与控制器支持声明。

### 2.2 ROS 2 Control源码

固定参考：

- `hardware_interface/src/hardware_component.cpp`
- `hardware_interface/src/resource_manager.cpp`
- `controller_manager/src/controller_manager.cpp`
- `hardware_interface/package.xml`
- `controller_manager/test/test_controller_manager_hardware_error_handling.cpp`

Jazzy分支快照SHA：`c6ef5a24e0cd21463edb99bded552a96f914b716`。该快照中的hardware_interface package.xml版本为4.50.0。Stäubli驱动package.xml仅依赖hardware_interface，没有固定其精确版本；实际部署必须记录安装的ros2_control/hardware_interface/controller_manager二进制包版本，不能只记录ROS发行版名称。

## 3. ROS 2 Control生命周期状态转换契约

Jazzy固定源码中的关键转换如下：

| 入口 | 插件回调结果 | HardwareComponent结果 |
|---|---|---|
| configure | SUCCESS | INACTIVE |
| configure | FAILURE | 保持UNCONFIGURED |
| configure | ERROR | 调用error()；当前状态为UNCONFIGURED时error()不再调用on_error，仍保持UNCONFIGURED |
| activate | SUCCESS | ACTIVE |
| activate | FAILURE | 保持INACTIVE |
| activate | ERROR | 调用error()；on_error结果决定UNCONFIGURED或FINALIZED |
| deactivate | SUCCESS | INACTIVE |
| cleanup | SUCCESS | UNCONFIGURED |
| read/write返回ERROR | 触发error()和on_error() | SUCCESS→UNCONFIGURED；FAILURE/ERROR→FINALIZED |
| shutdown | SUCCESS | FINALIZED |

需要特别区分两条路径：

- **on_configure()失败：** HardwareComponent::configure()从UNCONFIGURED调用on_configure()。如果返回ERROR，随后调用error()；但error()对UNKNOWN和UNCONFIGURED状态不调用on_error()，所以该路径保持UNCONFIGURED，可再次尝试configure。
- **ACTIVE/INACTIVE状态下read()/write()失败：** HardwareComponent::read()/write()检测到ERROR并调用error()。该时点组件已处于ACTIVE/INACTIVE，因而会真正执行插件on_error()，其返回值决定进入UNCONFIGURED还是FINALIZED。

官方Jazzy文档说明read()/write()返回ERROR会触发on_error()；on_error成功后硬件回到UNCONFIGURED，若error处理回调失败则进入FINALIZED，通常需要重新加载插件。实际状态转换以固定Jazzy源码为准。官方文档未替具体插件定义STOP命令是否成功或物理停止是否完成。

## 4. 主要发现

### F1｜read/write ERROR会触发硬件组件生命周期错误处理，而非普通周期性错误返回（高）

Stäubli read()在以下情况返回hardware_interface::return_type::ERROR：

- RobotDriver不存在或未连接；
- read_robot_state()失败；
- update_state()失败。

write()在以下情况返回ERROR：

- RobotDriver不存在或未连接；
- 活动控制模式下缓存状态显示error或INVALID；
- 控制模式不支持；
- 关节命令包含NaN；
- send_robot_command()失败。

在Jazzy HardwareComponent::read()/write()中，底层trigger_read/trigger_write返回ERROR会直接触发error()。ResourceManager收到非OK结果后还会记录故障硬件名称、再次调用component.error()（此时若已UNCONFIGURED/FINALIZED则不会再次执行on_error），并移除该硬件组件的可用接口。

**影响：** read/write的ERROR不只是本周期报告一次数据失败；它会触发硬件组件生命周期变化、接口撤销和相关控制器停用。当前驱动没有把短暂数据缺失、状态过期、网络中断、命令发送失败和不可恢复硬件故障分成不同恢复等级。

### F2｜断线时on_error返回ERROR，会使组件进入FINALIZED（高）

Stäubli on_error()逻辑为：

- 若robot_driver_存在且is_connected()为true：调用send_stop_all_command()，然后返回CallbackReturn::SUCCESS；
- 若driver未连接：记录错误并返回CallbackReturn::ERROR。

Jazzy HardwareComponent::error()将on_error的SUCCESS映射到UNCONFIGURED，将FAILURE/ERROR映射到FINALIZED。

因此，若read/write失败的原因是控制连接已经断开，on_error()会走未连接分支并返回ERROR，硬件组件进入FINALIZED。该状态不是普通的“等待重新连接”；普通set_hardware_component_state服务不能将FINALIZED组件重新配置。恢复通常需要卸载并重新加载硬件插件/Controller Manager进程，具体运维路径需要目标部署验证。

**边界：** 这是固定源码与Jazzy生命周期实现的静态调用链推导，尚未通过目标ROS 2运行时复现。

### F3｜连接仍存在时，STOP发送失败不会阻止on_error报告SUCCESS（高）

on_error()调用send_stop_all_command()时没有检查其返回值。即使该函数返回false，on_error()仍返回CallbackReturn::SUCCESS，Jazzy生命周期因而将硬件组件置为UNCONFIGURED。

进一步注意：

- send_stop_all_command()的true仅代表本地发送函数报告成功，不是CS9的独立接收/接受/执行回执；
- 前序SERVO-860已确认固定上游UDP would_block分支存在“丢弃数据报但send仍返回true”的静态缺口；
- 本轮没有在CS9上验证STOP命令是否被接受，也没有测量物理停止时间。

**影响：** 生命周期状态从ACTIVE变成UNCONFIGURED，不能作为机器人已停止的证据；STOP失败也不会通过on_error返回值反映为FINALIZED。不得把该软件路径当作安全功能或物理停止确认。

### F4｜成功错误处理后，on_error不释放RobotDriver连接资源（中/高）

Stäubli on_error()没有调用RobotDriver::disconnect()，也没有清除硬件层state_msg_、关节状态缓存或命令缓存。Jazzy HardwareComponent::error()执行on_error并直接设置生命周期状态，不会自动调用插件on_cleanup()或on_shutdown()。

因此，on_error返回SUCCESS后：

- 硬件组件进入UNCONFIGURED；
- HardwareComponent不再执行正常ACTIVE/INACTIVE读写周期；
- RobotDriver的control/diagnostics socket及接收线程可能仍然连接并运行；
- 已导出的接口由ResourceManager从available列表移除；
- 之后重新configure时，RobotDriver::connect()会检测既有连接并先disconnect，再建立新连接。

这意味着错误恢复依赖显式生命周期重配置；错误回调本身没有形成“STOP尝试—断开—缓存失效—新会话建立—首帧确认”的完整事务。该项与SERVO-858、SERVO-862已有的缓存和恢复问题相关，本轮新增的是其在Jazzy HardwareComponent生命周期中的具体资源状态后果。

### F5｜ControllerManager在硬件已error并移除接口后，仍尝试对故障组件执行mode switch（中/高，框架交互）

固定Jazzy源码路径：

1. ResourceManager::read()/write()在组件返回ERROR后调用component.error()；
2. ResourceManager将故障组件的command interfaces从available列表移除；
3. ControllerManager::read()/write()取得failed_hardware_names，查找使用这些硬件的控制器；
4. ControllerManager调用perform_hardware_command_mode_change()，尝试prepare_command_mode_switch()/perform_command_mode_switch()；
5. ResourceManager的prepare路径检查接口available状态；perform路径还要求组件处于INACTIVE或ACTIVE；
6. 但此时故障组件已经UNCONFIGURED或FINALIZED，且接口已被移除，故障组件的mode switch无法按普通路径完成。

ros2_control上游Issue #3620记录了这一Jazzy错误处理顺序，并说明read/write错误路径可能产生“Not available”及mode-switch失败日志。固定Jazzy源码快照也能看到相同的ResourceManager移除接口与ControllerManager后续调用顺序。

**归属边界：** 这是ros2_control框架交互问题，不应错误归因成Stäubli驱动的单独缺陷；本轮未修改ros2_control上游，也未判断该上游Issue是否会在未来版本修复。

**工程含义：** 不应依赖ControllerManager在硬件已经进入错误状态后，再通过普通mode switch向故障组件补发STOP。故障停止请求的实现与独立安全停止链必须在更早的故障处理边界中设计并验证。

### F6｜现有Stäubli测试没有覆盖HardwareComponent/ResourceManager/ControllerManager的真实错误传播链（高）

现有LifecycleTransitions测试：

- 直接调用on_init、on_configure、on_activate；
- 执行一次成功read；
- 写入命令接口并执行一次write；
- 最后停止mock robot。

它没有让read/write返回ERROR，也没有验证on_error回调、UNCONFIGURED/FINALIZED状态、接口available状态变化、ControllerManager控制器停用、mode-switch失败或重新configure/activate。

ConfigurationShouldFailWithoutRobot测试直接调用on_configure并检查回调返回ERROR，不经过HardwareComponent生命周期包装，因此不能证明configure失败后的最终生命周期状态。

ros2_control Jazzy仓库本身有test_controller_manager_hardware_error_handling测试文件，覆盖通用硬件错误后的控制器处理；但这不能替代Stäubli插件特有的on_error STOP结果、断线分支、socket清理和重连行为测试。

## 5. Stäubli与Jazzy错误处理交互矩阵

| 故障输入 | Stäubli回调结果 | Jazzy生命周期预期 | 当前静态结论 |
|---|---|---|---|
| on_configure连接失败，初始为UNCONFIGURED | on_configure返回ERROR | error()跳过on_error，保持UNCONFIGURED | 可再次尝试configure；需验证重试 |
| ACTIVE状态read超时，socket仍connected，STOP发送函数返回true | on_error返回SUCCESS | UNCONFIGURED | 本地发送不等于远端停止 |
| ACTIVE状态read超时，socket仍connected，STOP发送函数返回false | on_error仍返回SUCCESS | UNCONFIGURED | 发送失败未反映到生命周期结果 |
| ACTIVE状态read/write失败，driver已断线 | on_error返回ERROR | FINALIZED | 普通生命周期恢复不可用 |
| write命令发送失败，但is_connected仍为true | on_error返回SUCCESS | UNCONFIGURED | 接口撤销，需重配置 |
| read/write错误后ControllerManager停用控制器 | 框架后续mode switch | 失败组件已UNCONFIGURED/FINALIZED且接口不可用 | 普通mode switch不能作为故障STOP补偿 |
| UNCONFIGURED后重新configure | connect发现既有socket时先disconnect | 成功则INACTIVE | 需验证旧状态/命令缓存与新会话隔离 |
| cleanup成功 | on_cleanup调用disconnect | UNCONFIGURED | cleanup与on_error不是同一条调用路径 |

## 6. 整改与工程建议

### P0｜定义可恢复错误与不可恢复错误的生命周期策略

- 明确哪些故障允许回到UNCONFIGURED并人工重配置，哪些故障必须进入FINALIZED并要求重新加载插件。
- 将通信暂时中断、状态超时、协议畸形、控制器故障和驱动内部异常分级；不要让所有瞬态错误都隐式走同一个生命周期分支。
- 在部署操作手册中明确FINALIZED后的插件卸载/重新加载流程、数据归档和安全确认。

### P0｜让STOP结果可观测，但不把UDP STOP当作安全功能

- 检查send_stop_all_command()返回值，并在日志/诊断中记录STOP发送尝试、失败原因和后续确认状态。
- 将“本地发送成功”“控制器收到”“控制器接受”“机器人停止确认”定义为不同状态。
- 安全停止仍必须依赖适用的控制器安全功能、急停/安全PLC和经验证的安全回路；不能由普通UDP/VAL3/ROS软件STOP替代。

### P0｜为on_error建立明确的资源清理和状态失效契约

- 对进入UNCONFIGURED的路径，定义socket、接收线程、缓存、命令模式、GPIO输出缓存和session如何处置。
- 不得让旧session的状态或命令缓存跨重连复用。
- 在重新激活前，要求新连接、有效首帧、状态完整性、新会话序号和安全许可均通过验证。

### P1｜将ControllerManager错误处理作为独立集成验证对象

- 记录目标Jazzy二进制版本及上游补丁版本；
- 对照Issue #3620验证read/write故障后接口撤销、控制器停用和mode-switch日志；
- 不要把故障后mode-switch失败日志误判为Stäubli on_error STOP发送失败；
- 不要依赖该mode-switch路径向已经UNCONFIGURED/FINALIZED的组件发送停止命令。

### P1｜建立插件级集成测试

建议在Stäubli插件测试中使用Mock Robot与真实ResourceManager/ControllerManager封装，覆盖本报告LC-01至LC-15。只直接调用插件回调的单元测试不足以验证生命周期契约。

### P1｜固定软件兼容基线

Stäubli README指向ROS 2 Jazzy，但package.xml没有固定hardware_interface精确版本。部署基线必须保存ROS发行版、ros2_control、hardware_interface、controller_manager、pluginlib、rclcpp及驱动源码commit，且在版本升级后重跑生命周期故障测试。

## 7. 验收矩阵

| ID | 场景 | 预期结果 | 状态 |
|---|---|---|---|
| LC-01 | on_configure连接失败，初始UNCONFIGURED | 记录最终状态并确认可重试configure | 未执行 |
| LC-02 | read ERROR且driver仍connected，STOP本地发送成功 | 确认进入UNCONFIGURED、接口撤销和控制器停用 | 未执行 |
| LC-03 | read ERROR且STOP发送函数返回false | 失败原因可见；不得把UNCONFIGURED解释为已停止 | 未执行 |
| LC-04 | read ERROR且driver已断线 | 确认on_error返回ERROR及FINALIZED结果 | 未执行 |
| LC-05 | write ERROR且driver仍connected | 确认on_error和接口撤销路径 | 未执行 |
| LC-06 | write ERROR且driver已断线 | 确认FINALIZED和插件重载恢复程序 | 未执行 |
| LC-07 | on_error SUCCESS后socket/接收线程状态 | 明确记录连接资源是否仍运行 | 未执行 |
| LC-08 | UNCONFIGURED后重新configure | 验证旧socket disconnect与重新连接 | 未执行 |
| LC-09 | 重连后首帧为旧序号/旧session | 拒绝旧会话状态，不允许重新激活运动 | 未执行 |
| LC-10 | read错误后ResourceManager接口可用性 | 确认接口被移除且控制器不再使用 | 未执行 |
| LC-11 | read错误后ControllerManager mode-switch路径 | 记录接口不可用/生命周期门禁行为及日志 | 未执行 |
| LC-12 | write错误后ControllerManager控制器停用 | 确认控制器生命周期与命令接口状态 | 未执行 |
| LC-13 | FINALIZED组件恢复 | 验证卸载/重载插件流程与安全准入 | 未执行 |
| LC-14 | cleanup/shutdown/deactivate与on_error交叉 | 验证STOP、disconnect、缓存清理和重复调用 | 未执行 |
| LC-15 | 目标Jazzy二进制版本与固定源码版本一致性 | 记录包版本、补丁、测试结果和部署哈希 | 未执行 |

## 8. 证据边界

已完成：

- Stäubli固定提交中HardwareInterface生命周期回调、read/write错误返回、RobotDriver connect/disconnect/STOP路径静态审查；
- ros2_control Jazzy固定提交中HardwareComponent::configure/read/write/error、ResourceManager::read/write/mode-switch、ControllerManager::read/write/mode-switch调用顺序静态审查；
- 官方Jazzy生命周期与read/write错误处理文档核对；
- Stäubli现有HardwareInterface测试源码覆盖范围核对；
- ros2_control上游Issue #3620与Jazzy源码调用顺序交叉核对。

未执行：

- C++/ROS 2构建与单测；
- ResourceManager/ControllerManager运行时；
- 真实read/write错误注入；
- STOP发送失败、UDP丢包和断线注入；
- lifecycle service状态转换与插件卸载/重载；
- VAL3编译/部署、CS9仿真或实机停止确认；
- SIL/HIL/FAT/SAT及安全验证。

本轮不构成驱动功能通过、控制器安全验证通过或工程验收通过。未修改Stäubli上游源码，未提交或应用上游PR，未合并`TODO-EXT-001`。

## 9. 参考来源

1. [Stäubli固定提交：staubli_hardware_interface.cpp](https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/src/staubli_hardware_interface.cpp)
2. [Stäubli固定提交：robot_driver.cpp](https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/src/robot_driver.cpp)
3. [Stäubli固定提交：HardwareInterface单元测试](https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/test/unit_tests/test_staubli_hardware_interface.cpp)
4. [ros2_control Jazzy固定提交：hardware_component.cpp](https://github.com/ros-controls/ros2_control/blob/c6ef5a24e0cd21463edb99bded552a96f914b716/hardware_interface/src/hardware_component.cpp)
5. [ros2_control Jazzy固定提交：resource_manager.cpp](https://github.com/ros-controls/ros2_control/blob/c6ef5a24e0cd21463edb99bded552a96f914b716/hardware_interface/src/resource_manager.cpp)
6. [ros2_control Jazzy固定提交：controller_manager.cpp](https://github.com/ros-controls/ros2_control/blob/c6ef5a24e0cd21463edb99bded552a96f914b716/controller_manager/src/controller_manager.cpp)
7. [ROS 2 Control Jazzy：Lifecycle of a Hardware Component](https://control.ros.org/jazzy/doc/ros2_control/hardware_interface/doc/lifecycle_of_a_hardware_component.html)
8. [ROS 2 Control Jazzy：Handling of Errors During read() and write() Calls](https://control.ros.org/jazzy/doc/ros2_control/hardware_interface/doc/handling_errors_during_read_write.html)
9. [ros-controls/ros2_control Issue #3620](https://github.com/ros-controls/ros2_control/issues/3620)

## 10. 节点状态

SERVO-863固定Stäubli提交与ros2_control Jazzy提交静态审查完成；LC-01至LC-15验收矩阵已建立，全部未执行。

P0缺口仍包括：断线时on_error进入FINALIZED的恢复策略、STOP发送结果与生命周期SUCCESS脱钩、on_error成功后连接资源/缓存清理契约、ControllerManager故障mode-switch路径不能向已撤销接口发送停止请求。

**下一节点：§9.3.281 / SERVO-864：Stäubli硬件错误生命周期恢复状态机与故障注入测试设计。**
