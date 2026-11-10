# 2026-11-10 Stäubli ROS 2 硬件错误恢复实现映射与最小接口契约

> 节点：§9.3.282 / SERVO-865  
> 类型：固定上游源码静态映射、缺口分析与实现建议；不是代码修复或运行测试。  
> Stäubli 固定基线：`ICube-Robotics/staubli_driver_ros2@bd658e2d266e315d2ee35f985fb352ea88306b79`  
> ros2_control 参考：Jazzy `ros-controls/ros2_control@c6ef5a24e0cd21463edb99bded552a96f914b716`

## 1. 范围与结论

本轮逐项检查以下固定提交文件：

- `staubli_robot_driver/include/staubli_robot_driver/robot_driver.hpp`
- `staubli_robot_driver/src/robot_driver.cpp`
- `staubli_robot_driver/include/staubli_robot_driver/staubli_hardware_interface.hpp`
- `staubli_robot_driver/src/staubli_hardware_interface.cpp`
- `staubli_robot_driver/src/communication/udp_socket_impl.hpp`
- `staubli_robot_driver/include/staubli_robot_driver/real_time_socket_interface.hpp`
- `staubli_robot_driver/src/real_time_socket_interface.cpp`
- `staubli_robot_driver/src/real_time_socket_subscriber.cpp`
- `staubli_robot_driver/test/unit_tests/test_robot_driver.cpp`
- `staubli_robot_driver/test/unit_tests/test_staubli_hardware_interface.cpp`

结论：当前代码已有连接、断开、STOP尝试、状态新鲜度、生命周期回调和 mode-switch 基础，但还没有完整的错误恢复状态机。最优先的静态缺口是 UDP `would_block` 时数据包已丢弃却返回成功；其余关键缺口包括接收序号异常未拒绝、STOP 使用可能过期的状态构造、错误回调未清理会话、错误后命令缓存和硬件状态快照没有统一失效门禁，以及错误处理/读写/生命周期并发契约缺失。

本报告不把静态代码观察等同于运行时已复现的故障。没有修改上游源码，没有执行构建或测试。

## 2. 状态机与现有源码映射

| 设计状态/责任 | 现有实现位置 | 当前行为 | 差异/建议 |
|---|---|---|---|
| RUNNING | HardwareInterface::read/write；RobotDriver::is_connected/read_robot_state | 检查 socket/interface ready；read校验状态类型和年龄 | 增加显式运行态/故障锁存状态，不能仅以 socket connected 判定可运行 |
| ERROR_DETECTED | HardwareInterface::read/write返回ERROR | 断连、读状态失败、update_state失败、命令发送失败等返回ERROR | 统一记录首发故障类别、时间、触发路径；立即使状态快照和命令许可失效 |
| STOP_REQUESTED | HardwareInterface::on_error；write中的错误分支；on_shutdown | 调用 RobotDriver::send_stop_all_command | STOP请求应有统一入口和结果记录；不能在多个路径中无协调地重复发送 |
| STOP_SEND_ACCEPTED_LOCAL | RobotDriver::send_stop_all_command → RealTimeSocketInterface::send_message → Socket::send | 逐层返回bool；但 UDP would_block 特殊分支错误地返回true | 首先修正发送结果语义：would_block必须返回失败/明确未知，且计数；不把本地成功描述为远端确认 |
| STOP_CONTROLLER_ACKNOWLEDGED | 无 | 当前代码没有独立 STOP ACK/命令关联机制 | 当前状态应标记 unsupported；若未来增加，需协议回执、命令关联、来源和新鲜度校验 |
| INTERFACES_REVOKED | ros2_control ResourceManager（框架） | read/write ERROR进入硬件错误传播，框架撤销接口 | 集成测试要通过真实 ResourceManager 验证，驱动层不能假设控制器仍可调用硬件 STOP |
| UNCONFIGURED / FINALIZED | HardwareInterface::on_error | connected分支尝试STOP但忽略结果并返回SUCCESS；不connected返回ERROR | 将 STOP 结果与生命周期返回值解耦；清理资源后再返回明确生命周期结果 |
| RECONNECTING | RobotDriver::connect/disconnect | connect发现 socket connected 时先 disconnect；disconnect重置接口、停止接收线程、关闭socket、reset_data | 增加明确连接代次；disconnect清理结果逐资源记录；对半连接和部分失败进行可重复清理 |
| SESSION_VALIDATING | RobotDriver::connect/read_robot_state | 等待状态帧、检查消息类型/年龄和协议版本；没有控制器 boot/session ID | 增加新连接后的序号基线/首帧门禁；拒绝旧代次回调；补足来源校验 |
| INACTIVE / ACTIVE | HardwareInterface::on_activate、perform_command_mode_switch | activate设置当前模式STOP；perform依据prepare缓存切换模式 | 增加故障锁存和显式授权门禁，错误未清除、会话未验证时禁止切换到运动模式 |

## 3. 源码级关键发现

### 3.1 P0：UDP would_block 被当作发送成功

位置：`staubli_robot_driver/src/communication/udp_socket_impl.hpp` 的 `UDPSocketImpl::send()`。

当前实现调用 Asio `send_to(..., MSG_DONTWAIT, err)`。遇到 `boost::asio::error::would_block` 时日志明确说数据包 dropped，但该分支没有返回 false，函数末尾仍返回 true。上层 `RealTimeSocketInterface::send_message()` 因此也可能返回 true；`RobotDriver::send_stop_all_command()` 继而返回 true。

影响：
- UDP发送缓冲区繁忙时，运动命令可能未发送但上层误认为成功。
- STOP数据报可能已丢弃但上层误认为发送成功。
- 任何以该 bool 作为“发送成功”证据的日志、状态机和测试都不可靠。

建议最小契约：
- `would_block` 必须返回明确失败（或引入显式枚举区分 NOT_SENT / LOCAL_ACCEPTED / UNKNOWN）；不能返回 true。
- 统计丢弃计数并提供有界、非阻塞的故障上报。
- STOP 的发送失败应进入 STOP_UNCONFIRMED；本地发送成功也只代表本地发送层接受，不代表控制器收到或执行。
- 为 UDP send 添加注入测试，覆盖 would_block、其他错误和正常发送。

### 3.2 P1：序号重复/回退没有作为状态拒绝条件

位置：`real_time_socket_subscriber.cpp::read_message()` 与 `RobotDriver::read_robot_state()`。

Subscriber计算 lost_packages，并在重复序号时将 `status.new_message=false`；但仍返回 true。RobotDriver读取后没有检查 `status.new_message`，只检查 message type 和 time_since_received。因此重复帧可被当成一次成功读取，且同一帧在 staleness timeout 内可能被多次使用。序号回退路径仅按 wrap-around 计算丢包数，不会拒绝乱序帧。

建议：
- 区分“缓存中有可读消息”和“本周期收到新的、符合序号策略的消息”。
- 只有有效新帧才能刷新有效状态时间与状态代次。
- 序号回退仅在定义好的模数回绕窗口内接受；否则拒绝并记录。
- 新连接重置 subscriber 的序号基线/first_read 状态，避免旧会话序号影响新会话。
- 测试重复、乱序、合法回绕、远端重启序号归零和旧帧延迟到达。

### 3.3 P1：UDP数据源身份校验尚未实现

位置：`udp_socket_impl.hpp::handle_data_received()`。

代码注释明确标注 sender endpoint 校验仍是 TODO。接收回调在没有核对发送方地址/端口的情况下直接处理数据。

建议：
- 对来源 IP/端口与当前配置端点进行校验，不匹配则丢弃。
- 将来源校验与协议 magic/version/type/长度/字段范围校验合并为帧接纳门禁。
- 仅在完整校验通过后更新状态缓存、时间戳和序号。
- 在隔离测试网络注入非预期来源数据报，验证不刷新状态有效性。

### 3.4 P1：on_error 不清理 RobotDriver 会话

位置：`StaubliHardwareInterface::on_error()` 与 `RobotDriver::disconnect()`。

on_error在 driver connected 时调用 STOP 后直接返回 SUCCESS；没有调用 disconnect。相较之下，on_cleanup会disconnect，析构函数也尝试disconnect。RobotDriver::disconnect当前会重置 control interface/diagnostics subscriber（subscriber析构停止接收线程），再关闭两个socket并 reset_data。

建议：
- on_error必须进入统一故障处置路径；STOP尝试结果被单独记录。
- 根据策略显式断开/停止接收并清空旧状态，不允许只改变 lifecycle 状态而保留旧通信会话。
- 清理失败不能静默；记录 socket、subscriber、线程各自结果。
- 注意当前 disconnect 在接口 reset 后由 subscriber 析构停止接收线程，再关闭 socket；重构时必须保留“停止并 join 接收线程后关闭 socket”的生命周期顺序。
- 断开后必须清理硬件接口层 state_msg_、关节状态、GPIO状态、命令缓存和 mode-switch pending 状态，而不仅是 RobotDriver 内部消息头。

### 3.5 P1：STOP由可能过期的 RobotStateMessage 构造

位置：`RobotDriver::send_stop_all_command()`。

该函数以 `current_robot_state_` 调用 `prepare_robot_command_message()`，然后将当前序号写入 STOP 命令。它没有独立检查最近有效状态是否新鲜，也没有验证缓存所属连接代次。状态读取失败后，缓存对象可能仍保留上一次有效内容。

建议：
- STOP构造不得依赖未经 freshness/session 验证的普通运动状态缓存。
- 若协议确实需要状态字段，必须要求缓存来自当前连接代次且未过期；否则 STOP 状态标记未知，并交由独立安全链处理。
- 为 STOP 请求生成本地 event ID，日志关联“请求、序列化、send返回、后续反馈”，但不要把本地 event ID 伪装成控制器 ACK ID。

### 3.6 P1：硬件状态和命令缓存没有统一失效机制

位置：`StaubliHardwareInterface::read()`、`update_state()`、`write()`、`on_activate()`、`perform_command_mode_switch()`。

read在 update_state失败时返回ERROR，但 update_state在缺少 joint positions/velocities 时会提前返回；此前已经写入的其他状态字段可能仍是旧值。write在 NaN 或机器人错误时尝试 STOP 后返回 ERROR，但不统一清除所有 command buffers 或锁存故障。on_activate只把控制模式设为STOP，没有清空所有 pending mode/command状态。

建议：
- 引入状态有效标志、状态时间戳和连接代次。
- 每次 read 只在整帧校验和完整转换成功后原子提交快照；失败时整份快照标记无效，不允许部分字段混用新旧数据。
- 故障锁存时清空或屏蔽运动命令许可；重新配置后以有效新帧重新初始化位置命令。
- prepare/perform mode switch在故障锁存时拒绝运动模式，并确保 pending mode不会跨故障保留。

### 3.7 P1：连接首帧等待与 session 语义不足

位置：`RobotDriver::connect()`。

connect等待控制状态有效消息、检查协议版本；但目前没有远端 boot ID/session nonce。诊断数据读取还被注释掉，`diag_interface_ready`直接设为true。循环会持续到timeout期限结束，而不是在所有ready条件首次成立时立即结束。

建议：
- 将连接就绪分为 socket ready、control first-valid-frame、diagnostics ready（若确实需要）、protocol compatibility 和 session freshness 等独立结果。
- 仅在有效新帧满足序号/新鲜度条件后宣告 session validated。
- 诊断数据当前并未实际验证，连接日志和验收说明不得暗示诊断通道已收到有效诊断首帧。
- 增加连接 deadline 的单调时钟实现和 ready 后及时退出；这属于可维护性改进，优先级低于发送结果与状态有效性门禁。

### 3.8 P1：生命周期/读写/错误回调并发契约未定义

当前 `RobotDriver` 和 `StaubliHardwareInterface` 的连接指针、当前控制模式、状态消息、命令缓存和生命周期回调没有显式统一的并发/锁存契约。UDP subscriber 的消息缓存内部有同步，但这并不自动保护 HardwareInterface 中其他成员，也不保证 on_error 与 read/write 不并发。

建议：
- 明确 ros2_control 执行模型和允许并发调用集合。
- 建立单一故障锁存原子状态；read/write在锁存后拒绝常规控制命令。
- 生命周期资源清理与 read/write 必须通过明确的停止/同步协议协调；避免在实时线程持有大锁、阻塞 join 或执行慢速网络等待。
- 对可并发共享数据选择无锁快照/原子代次或有界锁策略，并用 TSan 与压力测试验证。
- 不要在未证明 ros2_control 调用串行保证前宣称不存在竞态。

## 4. 最小接口契约建议

以下是建议新增的抽象契约，不是对当前上游已有接口的描述。

| 契约接口/数据 | 责任 | 最低要求 |
|---|---|---|
| `FaultLatch` | HardwareInterface / RobotDriver | 原子记录首发故障、分类、时间和是否已处置；故障不能被普通 read/write 清除 |
| `SendResult` | Socket → RealTimeSocketInterface → RobotDriver | 至少区分 NOT_SENT、LOCAL_ACCEPTED、UNKNOWN；当前 bool API不足以表达完整语义 |
| `ConnectionGeneration` | RobotDriver / Subscriber | 每次 connect 成功尝试分配新 generation；回调和状态快照携带 generation |
| `StateSnapshot` | Subscriber → RobotDriver → HardwareInterface | 数据、序号、接收时间、generation、validity 一致提交；重复/乱序/过期帧不得刷新有效性 |
| `SessionValidation` | RobotDriver | protocol version、source endpoint、首帧、序号策略、必要字段均通过后才 validated |
| `StopAttemptRecord` | HardwareInterface / RobotDriver | 记录请求、发送结果、是否有协议 ACK（当前 unsupported）、后续运动观测；不表示安全链确认 |
| `CleanupResult` | RobotDriver | 分别报告 subscriber停止、线程join、socket关闭、缓存清空结果；部分失败可定位 |
| `RecoveryAuthorization` | 生命周期管理/运维层 | 明确操作员确认和独立安全许可；未授权不得从 INACTIVE进入ACTIVE |

## 5. 建议实现顺序与优先级

| 顺序 | 优先级 | 最小变更 | 依赖/验收 |
|---|---|---|---|
| 1 | P0 | 修正 UDP would_block 返回成功的错误语义 | UDP socket 单测；send失败注入；确保上层STOP记录失败 |
| 2 | P1 | 状态帧 freshness/sequence/source 统一接纳门禁 | 重复、乱序、回绕、旧来源和旧session帧测试 |
| 3 | P1 | FaultLatch + 整体状态快照失效 | read/write错误后接口状态与命令门禁单测 |
| 4 | P1 | STOP尝试记录与生命周期返回解耦 | STOP准备失败、发送失败、成功本地发送三类测试 |
| 5 | P1 | on_error统一清理与CleanupResult | subscriber线程停止/join、socket关闭、缓存失效测试 |
| 6 | P1 | connect generation 与 SESSION_VALIDATING | 断线重连、旧回调、旧帧、控制器重启测试 |
| 7 | P1 | mode-switch 故障锁存门禁 | prepare/perform与ResourceManager/ControllerManager集成测试 |
| 8 | P2 | 诊断首帧真实验证、连接等待退出与日志结构化 | 连接超时/诊断缺失/协议版本测试 |
| 9 | P2 | 插件 FINALIZED 卸载重载运维流程 | pluginlib/ControllerManager集成测试和运维演练 |

## 6. 单元与集成测试映射

| 测试 ID | 建议测试位置 | 场景 | 通过标准 |
|---|---|---|---|
| SERVO865-UT-01 | communication/test_sockets.cpp 或独立 UDP socket test | send正常 | 本地发送API返回LOCAL_ACCEPTED，计数一致 |
| SERVO865-UT-02 | UDP socket test | 注入 would_block | 明确 NOT_SENT/失败，不得返回成功 |
| SERVO865-UT-03 | UDP socket test | 其他 socket error | 明确失败，错误码可观测 |
| SERVO865-UT-04 | test_rt_socket_interface.cpp | serialize失败 / socket发送失败 | send_message不返回虚假成功 |
| SERVO865-UT-05 | test_robot_driver.cpp | 重复序号/乱序/合法回绕 | 仅符合策略的新帧更新有效快照 |
| SERVO865-UT-06 | test_robot_driver.cpp | 旧来源数据报 | 不更新消息缓存和 freshness |
| SERVO865-UT-07 | test_robot_driver.cpp | disconnect后旧状态读取 | 状态generation失效，旧快照不可用 |
| SERVO865-UT-08 | test_robot_driver.cpp | STOP无新鲜状态/断线/发送失败 | STOP结果分别可观察，不能报告远端确认 |
| SERVO865-UT-09 | test_staubli_hardware_interface.cpp | read缺必需字段 | 整个状态快照失效，无新旧字段混合 |
| SERVO865-UT-10 | test_staubli_hardware_interface.cpp | write错误后继续调用 | 故障锁存门禁拒绝后续运动命令 |
| SERVO865-UT-11 | test_staubli_hardware_interface.cpp | on_error清理资源 | 接收线程停止并join，socket关闭，状态缓存失效 |
| SERVO865-UT-12 | test_staubli_hardware_interface.cpp | 故障期间prepare/perform mode switch | 运动模式被拒绝，pending mode不能跨故障 |
| SERVO865-IT-01 | ResourceManager + SystemInterface integration | read/write ERROR传播 | 接口撤销、生命周期结果和错误原因一致 |
| SERVO865-IT-02 | ControllerManager integration | active controller依赖硬件故障 | 控制器处置可观测，无后续写命令 |
| SERVO865-IT-03 | pluginlib + lifecycle integration | FINALIZED卸载/重载 | 旧实例资源释放，新实例重新初始化且不继承旧状态 |
| SERVO865-IT-04 | network fault proxy / SIL | 断线、丢包、延迟、旧帧 | 故障锁存、会话验证和恢复门禁符合规格 |
| SERVO865-IT-05 | TSan/concurrency test | read/write与生命周期并发 | 无数据竞争、死锁、悬空回调或重复释放 |

以上均为建议新增测试，当前没有执行。

## 7. 与现有测试覆盖的差距

固定提交现有 `LifecycleTransitions` 测试直接调用插件的 on_init/on_configure/on_activate/read/write；它不通过 HardwareComponent/ResourceManager/ControllerManager真实错误传播路径，也不注入 read/write ERROR、STOP发送失败、on_error资源清理、接口撤销或 FINALIZED 重载。

现有 `RobotDriver` 单测以 loopback mock server验证连接、断开和通信基础能力；不能证明 UDP would_block、发送丢包、旧来源帧、重复/乱序帧和跨会话旧数据的故障契约。

## 8. 本轮状态与限制

- 已完成：固定提交源码逐项映射；确认 UDP would_block返回true但日志报告packet dropped；识别序号重复/回退未拒绝、来源校验TODO、on_error不disconnect、STOP使用缓存状态、硬件状态快照缺乏整体失效、连接诊断首帧未真实读取、并发契约缺失等问题。
- 未完成：任何代码修复、接口实现、构建、单测、集成测试、TSan、SIL/HIL、CS9/VAL3或实机验证。
- 未修改 Stäubli 上游；未应用/合并任何 PR；`TODO-EXT-001`仍未获授权。
- 不能据此宣称问题已修复或恢复状态机已实现。

## 9. 参考源码链接

所有源码链接固定到同一 Stäubli commit：

- [robot_driver.hpp](https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/include/staubli_robot_driver/robot_driver.hpp)
- [robot_driver.cpp](https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/src/robot_driver.cpp)
- [staubli_hardware_interface.hpp](https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/include/staubli_robot_driver/staubli_hardware_interface.hpp)
- [staubli_hardware_interface.cpp](https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/src/staubli_hardware_interface.cpp)
- [udp_socket_impl.hpp](https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/src/communication/udp_socket_impl.hpp)
- [real_time_socket_interface.cpp](https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/src/real_time_socket_interface.cpp)
- [real_time_socket_subscriber.cpp](https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/src/real_time_socket_subscriber.cpp)
- [test_staubli_hardware_interface.cpp](https://github.com/ICube-Robotics/staubli_driver_ros2/blob/bd658e2d266e315d2ee35f985fb352ea88306b79/staubli_robot_driver/test/unit_tests/test_staubli_hardware_interface.cpp)

## 10. 下一节点

**§9.3.283 / SERVO-866：UDP 发送结果契约与状态帧接纳门禁专项设计。**

优先围绕 P0/P1：
1. 为 UDP send 定义 NOT_SENT / LOCAL_ACCEPTED / UNKNOWN，修复 would_block虚假成功问题的最小补丁规格。
2. 定义发送错误、丢包计数、STOP结果事件和实时线程非阻塞上报契约。
3. 定义数据来源、帧长度/类型/版本、序号单调性/回绕、接收新鲜度和连接代次的状态帧接纳算法。
4. 给出确定性 mock/fault-injection 测试设计与验收日志。
5. 本节点仍只做设计与静态分析，未经授权不修改 Stäubli 上游。
