# 2026-11-10 Stäubli RobotDriver / Subscriber fixture 生命周期与集成测试映射

> 节点：§9.3.288 / SERVO-871。固定上游静态审查与测试夹具设计，不是上游补丁，也不是测试执行报告。  
> Stäubli 基线：`ICube-Robotics/staubli_driver_ros2@bd658e2d266e315d2ee35f985fb352ea88306b79`  
> ros2_control 参考：`ros-controls/ros2_control@c6ef5a24e0cd21463edb99bded552a96f914b716`

## 1. 本轮范围与结论

本轮将 SERVO-870 的 FS-01至FS-22 映射到固定上游实际调用点，并设计分层 fixture 生命周期。核对的生产文件：

- `staubli_robot_driver/include/staubli_robot_driver/communication/socket.hpp`
- `staubli_robot_driver/include/staubli_robot_driver/robot_driver.hpp`
- `staubli_robot_driver/src/robot_driver.cpp`
- `staubli_robot_driver/include/staubli_robot_driver/real_time_socket_subscriber.hpp`
- `staubli_robot_driver/src/real_time_socket_subscriber.cpp`
- `staubli_robot_driver/include/staubli_robot_driver/real_time_socket_interface.hpp`
- `staubli_robot_driver/src/real_time_socket_interface.cpp`
- `staubli_robot_driver/test/unit_tests/test_robot_driver.cpp`
- `staubli_robot_driver/test/unit_tests/communication/test_rt_socket_interface.cpp`

关键结论：

1. 现有最小注入 seam 是 RobotDriver 增加一个显式构造重载，接收 control 与 diagnostics 两个 `std::shared_ptr<Socket>`；保留默认构造和 SocketFactory 行为不变。
2. Subscriber 构造时立即检查 socket connected/receiving 并调用 start_receive_thread；构造失败抛 `std::runtime_error`。因此 fake 必须在 subscriber 构造前 connect 成功，且 fixture 需要明确管理构造异常和回滚。
3. Subscriber 的 callback 捕获裸 `this` 并调用 update_message；析构函数直接调用 `socket_->stop_receive_thread()`。Fake 的 stop 屏障因此直接关系到 subscriber 对象生命周期：stop 返回前不得再进入该 subscriber callback。
4. RobotDriver::disconnect 先 reset control interface 与 diagnostics subscriber，再检查 socket receiving 并 disconnect；subscriber 基类析构会 stop receive。之后 RobotDriver 仍会检查 is_receiving 并可能再次 stop，故 Fake stop 必须幂等。
5. RobotDriver 当前析构函数为空；不能把显式 disconnect 的行为与析构行为混为一谈。成员销毁会触发 subscriber/interface 基类析构，但不等价于完整 RobotDriver::disconnect，尤其不保证显式 socket disconnect。
6. RobotDriver::connect 同步等待有效 state 消息，并在循环中 sleep 500 ms；Fake 手动 dispatch 可以在测试控制线程投递 state/diagnostics 数据，但不能在 connect 同一线程内等待之后再投递。
7. 当前 subscriber 每次 update_message 使用 `rclcpp::Clock().now()`，read_message 再次使用同类 Clock 计算时间差；ManualClock 需要 seam 改造，不能仅通过 FakeSocket 控制接收数据时间。
8. 现有单测使用硬编码 UDP loopback 端口、sleep 和独立 mock server thread；应保留为 adapter/integration 覆盖，不把 FakeSocket 测试替换成“真实 UDP 已覆盖”。

## 2. 实际生产调用链

### 2.1 RobotDriver 构造与 socket 所有权

固定基线的默认构造在 `robot_driver.cpp` 中创建两个独立 UDP socket：

- `control_socket_`：提供 RobotState 接收和 RobotCommand 发送。
- `diagnostics_socket_`：提供 DiagnosticData 接收。

头文件中 RobotDriver 持有两个 shared_ptr Socket、一个 `RealTimeSocketInterface<RobotStateMessage, RobotCommandMessage>` 和一个 `RealTimeSocketSubscriber<DiagnosticDataMessage>`。

建议只增加：
`RobotDriver(std::shared_ptr<Socket> control_socket, std::shared_ptr<Socket> diagnostics_socket)`
并在构造时拒绝 null、同一对象被误用作两个 channel（若产品允许共享需另行证明），同时初始化 logger、timeout、data。默认构造仍调用 SocketFactory 创建两个 UDP 实例。构造注入必须是 test seam，不暴露任何上游网络行为变更。

### 2.2 connect 路径及失败分支

`RobotDriver::connect(config, timeout)` 的实际阶段顺序：

1. 记录 connect 开始时间，保存 NetworkConfig，检查 robot_ip 非空。
2. 若已有 socket connected，调用 disconnect 清理旧会话。
3. control socket connect。
4. 创建 control RealTimeSocketInterface；其父类 Subscriber 构造立即 start_receive_thread。
5. diagnostics socket connect。
6. 创建 diagnostics RealTimeSocketSubscriber；立即 start_receive_thread。
7. 检查两个接口 is_ready。
8. 循环调用 read_robot_state 等待第一条有效 state；每轮 sleep 500 ms。diagnostics readiness 当前被硬编码为 true，代码中有 TODO 尚未真正读取诊断消息。
9. 检查 protocol version 与兼容性字段。

这意味着注入测试必须为 connect 循环提供异步控制路径：在 connect 所在线程等待时，由测试 driver 线程调用 control_fake.deliver(serialized_state)；不要在同一个线程同步调用 connect 后再 deliver，否则 connect 可能直到 timeout 才返回。diagnostics 消息当前不是 connect 成功的必要条件，不能误写成已验证 diagnostics 首包门禁。

### 2.3 disconnect 与析构链

`RobotDriver::disconnect()`：

1. reset control_interface_；RealTimeSocketInterface 派生析构为空，随后 Subscriber 基类析构调用 stop_receive_thread。
2. reset diagnostics_subscriber_；Subscriber 析构调用 stop_receive_thread。
3. 若 control socket 仍 connected，且 is_receiving() 为 true，则再次 stop；之后 disconnect。
4. diagnostics socket 同样处理。
5. reset_data，返回两个 disconnect bool 的逻辑 AND。

因此测试必须断言 stop 至少可能被调用两次且行为幂等，不能将 stop 调用次数固定为恰好一次。Subscriber 析构中的 stop 返回值被忽略；RobotDriver 随后的 stop 结果才会被记录为 warning。若 Fake stop 返回 false 但仍完成 callback 清理，可验证 teardown 不泄漏，但不能声称真实 socket stop 的失败语义已被证明。

`RobotDriver::~RobotDriver()` 当前为空。成员销毁顺序由声明顺序逆序决定：diagnostics subscriber、control interface、diagnostics socket、control socket 等依次析构。Subscriber 析构会 stop，但 RobotDriver 析构本身没有调用显式 disconnect，也不应被测试期望为必然调用两次 disconnect。需要独立用例记录此差异。

### 2.4 Subscriber callback 与 message buffer

Subscriber 构造函数调用 init_communication：

- 检查 socket 非空、connected、未 receiving。
- 调用 start_receive_thread，callback 捕获 `[this]`。
- callback 调用 update_message(data, bytes_transferred)。
- update_message deserialize；成功时写入 reception_timestamp，再更新 RealtimeThreadSafeBox；失败只记录错误。
- read_message 从 box 读取最新消息，计算 time_since_received，更新序号丢包状态。
- Subscriber 析构直接 stop_receive_thread。

Fake deliver 可驱动这条真实 Subscriber callback 路径，因此这类测试比纯 Fake FS 测试更有价值；但它仍不验证 UDP socket、Asio io_context、真实后台线程调度或内核数据报。

## 3. Fixture 分层和所有权规则

### F0 — FakeSocket contract fixture

目的：只测试 FS-01至FS-22。fixture 拥有 FakeSocket 和事件快照；不创建 ROS node、真实 UDP 或 RobotDriver。每个测试独立实例，避免 FIFO 脚本跨测试残留。

### F1 — SubscriberHarness fixture

资源顺序（创建顺序）：

1. 确保 rclcpp 初始化（由测试套件级环境统一负责，不在每个 fixture 任意 shutdown）。
2. 创建 FakeSocket shared_ptr。
3. 在构造 Subscriber 前脚本化 connect 成功。
4. 创建 Subscriber；构造会调用 start_receive_thread。
5. 测试调用 FakeSocket::deliver，进入真实 Subscriber::update_message。
6. TearDown 首先 reset Subscriber；其析构触发 FakeSocket::stop 屏障。
7. 再断言 Fake 已停止、active callback=0、callback 清空，最后释放 Fake。

严禁先销毁 Fake 再销毁 Subscriber。不得在 subscriber reset 前手动销毁其唯一 socket 所有者；shared_ptr 只保证对象存活，不自动保证 callback 捕获的裸 this 安全，真正的安全边界是 Subscriber 析构中的 stop 屏障。

### F2 — RobotDriverInjectedFixture

资源创建顺序：

1. ROS 初始化与测试时钟环境。
2. 创建两个独立 FakeSocket：control 与 diagnostics。
3. 配置各自 connect 脚本成功。
4. 构造注入双 socket 的 RobotDriver。
5. 调用 connect(config, timeout)；另一个测试线程等待 control Fake callback 已注册后投递序列化 RobotState 消息。
6. connect 返回后进行 send/read/disconnect 断言。
7. TearDown 先停止测试侧投递线程并 join，再显式调用 driver.disconnect（若 driver 仍存在），再 reset driver，最后检查两个 Fake 均 active=0、STOPPED、callback empty。
8. 释放 Fake。

禁止在 driver.disconnect/reset 期间继续调用 deliver；若测试目标是 stop/deliver 竞态，需单独 fixture 控制 gate 和顺序，且所有 worker 都必须 join。

### F3 — Real UDP loopback fixture

保留现有真实 SocketFactory UDP 双端通信测试，专门覆盖真实 adapter 的 bind/connect/send/receive 和系统端口行为。将硬编码端口替换为动态端口或集中分配器是后续独立改造，不属于 Fake seam 首轮范围。所有 worker thread/future 必须在 TearDown 前确定完成；现有 future timeout 分支需特别审查：std::async(std::launch::async) future 析构可能阻塞直到任务完成，不能把 wait_for timeout 等同于后台任务已取消。

### F4 — ROS 2 Control integration fixture

RobotDriver 注入测试只验证驱动层。ResourceManager/ControllerManager 的 hardware lifecycle、interface export/revocation、controller switch、ERROR propagation 需独立使用真实 plugin/ROS 2 Control fixture；不得用 FakeSocket 替代整个 hardware component 并声称覆盖 ros2_control。

## 4. FS-01至FS-22 对生产调用点的映射

| Fake 用例 | 对应生产路径 | 应新增的调用方/集成断言 | 覆盖边界 |
|---|---|---|---|
| FS-01 | RobotDriver::connect 两个 channel 调用 connect overload | control 与 diagnostics 的 endpoint/port 参数各自准确；不串用配置 | RobotDriver 注入 fixture |
| FS-02 | RobotDriver connect 的 control socket connect 失败分支 | connect 返回 false；不创建 control interface；diagnostics 不应连接 | RobotDriver |
| FS-03 | Socket 脚本耗尽 | 调用方在 false 时失败关闭，不继续假设已连接 | Fake + RobotDriver |
| FS-04 | RealTimeSocketInterface::send_message -> Socket::send | 序列化后的 payload 被发送一次；send false 传播为 send_message false | Interface + Fake |
| FS-05 | send 默认失败 | 未配置脚本不允许假成功；上层 command API 返回 false | Fake + RobotDriver |
| FS-06 | Socket::receive_once | 固定 Socket 抽象的 blocking receive_once 调用方需单独确认；当前 Subscriber 主路径使用异步 callback，不经过此方法 | Fake only，除非找到调用点 |
| FS-07 | receive_once 失败 | 不将失败伪装为有效消息 | Fake only |
| FS-08 | Subscriber init_communication 的 disconnected guard | Subscriber 构造抛异常；不遗留 callback/receiving | SubscriberHarness |
| FS-09 | Subscriber 已 receiving guard | 第二个 Subscriber 对同一 socket 构造失败；原 Subscriber 仍有效 | SubscriberHarness |
| FS-10 | callback -> update_message | deliver 有效序列化消息后，read_message 取得相同字段与 sequence | SubscriberHarness |
| FS-11 | Subscriber destructor -> stop | reset Subscriber 后 stop 屏障完成且幂等 | SubscriberHarness |
| FS-12 | stop 后迟到的数据投递 | stop 线性化后 deliver 被拒绝；不得访问已销毁 Subscriber | SubscriberHarness |
| FS-13 | callback 执行期间析构/stop | gate 阻塞 callback，另线程 reset subscriber；reset 不能先于 callback 完成 | SubscriberHarness concurrency |
| FS-14 | update_message callback 异常路径 | 生产 update_message 目前无预期抛异常契约；Fake callback 异常用例不等同于 Subscriber 代码异常测试 | Fake only + optional injected callback |
| FS-15 | RobotDriver::disconnect reset Subscriber 再断开 socket | 两个 channel callback 都退出后 disconnect；不发生 use-after-free | RobotDriverInjectedFixture |
| FS-16 | reconnect 后重新创建 interface/subscriber | 新一轮 callback 更新新实例；旧 callback 不再访问旧对象 | RobotDriver lifecycle |
| FS-17 | control/diagnostics 分离 | control state 投递只更新 state；diagnostics 投递只更新 diagnostics buffer | RobotDriverInjectedFixture |
| FS-18 | 事件日志并发快照 | Fake 内部数据竞争由 TSan 验证；调用方状态快照由相应线程安全机制验证 | Fake + TSan |
| FS-19 | stop/deliver 竞态 | Subscriber reset 与 deliver 的两种顺序均安全 | SubscriberHarness concurrency |
| FS-20 | callback self-stop | 生产 Subscriber callback 不直接调用 stop；Fake 规则只保护 helper，不能伪称生产路径测试 | Fake only |
| FS-21 | events() 快照 | 事件快照修改不影响 Fake；调用方不得依赖测试内部事件引用 | Fake only |
| FS-22 | bytes_transferred 越界 | Fake 拒绝非法长度；另外需对 Message::deserialize 的短帧/超长帧做真实 callback 路径测试 | Fake + SubscriberHarness |

注意：FS-06/07 对应 Socket::receive_once 接口，但在已核对的 Subscriber 主路径中未见使用。若无其他调用点，保留为 Fake 接口覆盖，不将其标成 RobotDriver/Subscriber 覆盖。

## 5. 建议新增的生产调用方测试集

以下是建议的独立测试，不应挤入 FS-01至FS-22 的 Fake-only 计数：

### SD-01 Subscriber 构造前置条件
- Arrange：Fake 未连接 / 已连接且 receiving / 已连接且 stopped 三种状态。
- Act：分别构造 Subscriber。
- Assert：未连接与已 receiving 时构造抛 runtime_error；成功构造时恰好注册 callback 并 is_ready=true；失败路径没有遗留 callback。

### SD-02 有效帧到消息缓冲
- Arrange：Fake connected + Subscriber ready；构造有效 RobotStateMessage 并序列化。
- Act：deliver 完整 buffer 与精确长度；read_message。
- Assert：消息字段、序号匹配；status.new_message=true；无丢包。时间戳断言需使用可控时钟 seam 或宽容的真实时钟断言，不能把系统调度延迟误认为协议错误。

### SD-03 非法/截断帧
- Arrange：构造小于协议最小长度、长度不匹配、损坏字段的 payload。
- Act：deliver 后 read_message。
- Assert：deserialize 失败，旧的有效消息不得被覆盖；没有伪造有效状态。捕获日志/错误计数作为失败证据；当前实现仅打印日志，可能需要 test logger seam 才能稳定断言。

### SD-04 sequence 与 wrap-around
- Arrange：发送基准 sequence，再发送跳号、重复、回绕序列。
- Act：逐帧 deliver，逐次 read_message。
- Assert：lost_packages、new_message、sequence 按当前算法精确断言。注意现有算法只在新 sequence 大于/小于 last sequence 时做简单比较；需确认 MAX_FRAME_SEQUENCE_NUMBER 边界与 16-bit 半空间规则，测试不应预先假设算法正确。

### SD-05 send serialization 与故障传播
- Arrange：创建 RealTimeSocketInterface；设置 send true/false；准备合法消息。
- Act：send_message。
- Assert：序列化字节与 message contract 匹配；false 传播；未连接或 serialize 失败时不调用 Socket::send。

### SD-06 双通道隔离
- Arrange：注入两个独立 FakeSocket，分别创建 control interface 与 diagnostics subscriber。
- Act：投递不同 message type 的数据。
- Assert：各自缓冲独立、事件独立、断开一个 channel 不会误清另一个 channel；RobotDriver 对应 getter/read API 结果正确。

### SD-07 connect rollback
- Arrange：control connect 成功；diagnostics connect 失败，或 Subscriber start 失败。
- Act：调用 RobotDriver::connect。
- Assert：返回 false；已创建 interface/subscriber 被销毁并 stop；control socket 被断开；没有活跃 callback；失败原因可从事件序列还原。

### SD-08 disconnect ordering
- Arrange：两个 callback 分别阻塞在 gate。
- Act：调用 RobotDriver::disconnect。
- Assert：接口/subscriber reset 引起 stop 屏障；两个 callback 均退出后才发生 socket disconnect；reset_data 在收尾阶段执行。检查事件 happens-before，不以两个 Fake 的本地 sequence 号比较跨实例顺序。

### SD-09 RobotDriver destructor 与 explicit disconnect 对照
- Arrange：分别创建已连接 driver，走 explicit disconnect 与仅销毁 driver 两条路径。
- Act：调用 disconnect / reset driver。
- Assert：显式 disconnect 应调用 socket disconnect；仅析构路径按当前实现只能保证成员析构顺序及 Subscriber stop，不能预期 RobotDriver::~RobotDriver 主动执行 disconnect。此测试用于锁定当前行为，不代表推荐长期保留空析构。

### SD-10 connect 首帧投递与 timeout
- Arrange：启动 connect future；等待 control callback 注册；按时或超时后 deliver 有效/无效帧。
- Act：让 connect 的等待循环运行。
- Assert：有效 state 在 timeout 前到达时 connect 可成功；无效/未到达时失败并 rollback。由于 connect 内部使用 500 ms sleep 和 Clock::now，需引入可控时钟/等待策略 seam 才能得到快速、确定性单测。

## 6. 最小生产 seam 设计建议

第一阶段建议仅对 Stäubli 上游形成待授权补丁设计，不在本轮直接修改上游：

1. RobotDriver 增加双 Socket 注入构造；默认构造委托到 SocketFactory。
2. RealTimeSocketSubscriber 保持 socket 抽象不变；新增可选 clock provider（返回与 rclcpp::Time 类型/clock type 一致的 now 值），生产默认仍用 rclcpp::Clock().now()。
3. 将 RobotDriver connect 使用的 start time 与 Subscriber reception/read time 统一到明确的 clock policy；不要混用不同 clock type。
4. 为 connect loop 的等待/休眠引入窄 wait strategy，测试可推进时间而不 sleep 真实 500 ms；不要把 ROS time 与 steady_clock freshness 混为一谈。
5. 暂不改变 Socket 的 bool send 和 callback 签名；若要引入 endpoint/error/generation，须单独版本化接口变更并更新真实 adapter。
6. FakeSocket 只编入 test target；生产库不依赖 gtest helper。

## 7. 生命周期和竞态必须验证的 happens-before

- Subscriber 构造：start_receive_thread 成功后才允许对象对外发布。
- Subscriber 析构：stop_receive_thread 关闭 admission；等待所有已 admission callback 退出；之后析构对象成员。
- RobotDriver disconnect：销毁 control interface 与 diagnostics subscriber，确保两个 callback 屏障结束，再 disconnect sockets。
- RobotDriver reconnect：上一轮 Subscriber 已完全销毁、旧 callback 归零后，才能在同一 socket 或新 socket 上 start 新轮次。
- Fixture TearDown：先停止 producer/worker，再 join；然后销毁 driver/subscriber；最后断开/释放 socket。
- 不得在 callback 内销毁所属 Subscriber/RobotDriver；这会形成自等待，需由 API 线程外发起 shutdown。
- callback 使用裸 this 的当前设计要求严格 join-before-destruction；未来如要弱化此约束，需采用共享状态对象/弱引用 token 等独立架构设计，不能仅靠 shared_ptr<Socket> 解决。

## 8. 现有测试基础设施的风险项

1. `test_robot_driver.cpp` 使用固定端口 20021/20022/30021/30022；并行运行或端口占用会产生非确定失败。
2. RobotDriver fixture 的 `start_mock_robot()` 创建线程；TearDown 应无条件 stop/join（即使测试提前断言失败），否则 fixture 生命周期存在泄漏风险。
3. Subscriber tests 使用 sleep_for 100 ms/1 s；需改为条件等待或 deterministic delivery，真实 UDP adapter 测试仍可保留少量系统级超时。
4. `receiveMockCommand` 使用 std::async launch::async；wait_for timeout 不代表任务被取消，future 析构可能阻塞。需显式取消协议或确保任务可退出。
5. RobotDriver connect 每轮 sleep 500 ms，且 diagnostics 首帧检查当前被硬编码为 true；测试应区分当前实现事实与期望行为。
6. RobotDriver::~RobotDriver() 为空；显式 disconnect 与析构清理语义不一致，需作为独立设计决策，不要在测试中隐式假定。
7. Subscriber::update_message 在反序列化成功时用 ROS Clock 写 timestamp；当前没有注入时钟，无法对 freshness 做完全确定性单测。
8. subscriber callback 捕获裸 this；Fake stop barrier 的正确性是避免 use-after-free 的必要条件，但 Fake 测试不能替代真实 UDPSocket/Asio teardown 验证。

## 9. 验收分层与状态

| 层级 | 预期证据 | 当前状态 |
|---|---|---|
| FakeSocket UT | FS-01至FS-22、事件日志、脚本耗尽、stop/deliver 屏障 | NOT_RUN；Fake 未实现 |
| Subscriber + Fake | SD-01至SD-04、析构与 callback 屏障 | NOT_RUN；未实现 seam/fixture |
| Interface + Fake | SD-05 序列化与 send 故障传播 | NOT_RUN |
| RobotDriver + 双 Fake | SD-06至SD-10、connect rollback、双通道、析构对照 | NOT_RUN；注入构造未实现 |
| Real UDP loopback | adapter、Asio、真实 datagram、socket teardown | 现有测试代码存在；本轮未执行，不代表通过 |
| ROS 2 Control integration | ResourceManager/ControllerManager 生命周期与错误传播 | NOT_RUN |
| TSan/ASan | 并发数据竞争与 use-after-free 证据 | NOT_RUN |
| SIL/HIL/VAL3/CS9/FAT/SAT/实机 | 目标控制器与系统级验收 | NOT_RUN |

## 10. 本轮状态与下一节点

- 本轮完成固定上游生产调用链、RobotDriver 双 Socket 所有权、Subscriber callback/析构屏障、disconnect 顺序、现有 fixture 风险与 FS 映射的静态审查。
- 未修改 Stäubli 上游或 ros2_control 上游；未创建/应用 PR；`TODO-EXT-001`仍未授权。
- 未实现注入构造、FakeSocket、ManualClock、wait strategy 或任何新 fixture。
- FS-01至FS-22、SD-01至SD-10 全部 NOT_RUN。
- 未运行 build、gtest、loopback、TSan/ASan、ROS 2 Control 集成、SIL/HIL、VAL3/CS9、FAT/SAT或实机测试；工程级验收未通过。

**下一节点 §9.3.289 / SERVO-872：审查 RobotDriver connect/disconnect 回滚路径的故障注入覆盖，形成双 Socket 状态转换表、部分初始化资源清理矩阵与 SD-07/SD-08/SD-10 的精确事件断言。**
