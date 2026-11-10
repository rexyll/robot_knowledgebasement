# Stäubli SocketV2 source-to-test coverage gap、teardown failure-path matrix 与最小验证切片

- 节点：§9.3.302 / SERVO-885
- 审查日期：2026-11-10
- 固定上游：`ICube-Robotics/staubli_driver_ros2@bd658e2d266e315d2ee35f985fb352ea88306b79`
- 前序输入：SERVO-884源码级资源所有权/close-site/DAG审计
- 方法：读取固定commit recursive tree、CMake测试注册、socket/RT interface/RobotDriver/HardwareInterface/mock server测试源码；按源码行号建立测试覆盖与失败路径映射
- 执行边界：静态审查；未运行测试、未修改上游

## 1. 结论摘要

固定提交已有一组实际UDP loopback测试，覆盖Socket工厂、connect/disconnect、send/receive、单次/连续接收、callback、多消息、reconnect、double connect/disconnect、double start/stop；RT subscriber/interface有正常收发与消息状态测试；RobotDriver有连接、断开、状态读取和staleness测试；HardwareInterface有构造、初始化、plugin加载、接口导出和一次正常lifecycle读写测试。

但当前测试主要证明**正常路径功能行为**，没有覆盖SERVO-884识别出的关键teardown失败语义：

1. 没有FakeSocket/可注入SocketFactory/close失败注入接口；现有测试直接构造真实UDP实现。
2. 没有验证Asio close抛异常后底层socket状态、`is_connected_`状态、析构重试及owner残留。
3. 没有并发callback期间销毁Subscriber/UDPSocket的确定性屏障测试，也没有active callback drain/late callback测试。
4. 没有stop/join失败、self-join、joinable异常、线程永久阻塞或callback抛异常测试。
5. RobotDriver的disconnect happy path有覆盖，但stop失败、control/diagnostics部分成功、close失败、重复disconnect后底层资源状态均未注入。
6. HardwareInterface有plugin加载和正常configure/activate/read/write，但没有显式on_cleanup/on_shutdown/on_error断开路径矩阵、plugin unload与worker/callback残留交错测试。
7. 测试中存在固定端口和sleep驱动同步，适合基本集成验证，不足以作为资源生命周期竞态的确定性测试。

因此SERVO-885的结论是：现有测试不是“无测试”，而是**happy-path和轻量loopback覆盖存在；清理失败、资源残留和并发销毁覆盖缺口明显**。

## 2. 测试注册与源文件清单

固定commit的 `staubli_robot_driver/CMakeLists.txt`（blob `b21608627b53d66f9910d9a836b053cd7d7fd6bf`）：

- C++17：25–27行。
- 主库源文件包含 `socket_factory.cpp`、`udp_socket.cpp`、subscriber/interface、RobotDriver、MockRobotServer：53–68行。
- 硬件接口独立共享库：82–93行。
- BUILD_TESTING与ament_cmake_gtest：129–153行。
- 注册的测试目标：serialization、`test_sockets`、`test_rt_socket_interface`、`test_robot_driver`、`test_mock_robot_server`、`test_staubli_hardware_interface`：155–182行。
- 没有独立TSan/ASan/UBSan target、故障注入target或native socket close adapter target。

| 测试目标/源码 | 主要覆盖 | 不覆盖的关键语义 |
|---|---|---|
| `test_sockets.cpp` | UDP loopback；connect/disconnect；callback receive；多消息；reconnect；receive_once；disconnected send；double connect/disconnect；double start/stop | close失败/系统调用错误、底层open状态复核、异步handler drain、并发销毁、callback异常、线程join异常 |
| `test_rt_socket_interface.cpp` | Subscriber初始化、收包、sequence/lost/stale状态；Interface初始化、双向发送接收 | Subscriber销毁与回调并发、buffer残留、异常callback、stop结果传播 |
| `test_robot_driver.cpp` | 双通道loopback mock、connect/disconnect、state read/staleness | partial channel cleanup、stop/close失败、析构残留、并发disconnect、远端session确认 |
| `test_staubli_hardware_interface.cpp` | 构造/init、configure、plugin load/init、interface export、正常activate/read/write | on_cleanup/on_shutdown/on_error失败矩阵、plugin unload与callback/worker交错、清理结果验证 |
| `test_mock_robot_server.cpp` | mock server构造/init/disconnect/not-ready及未初始化API拒绝 | 驱动transport failure injection；mock server析构/partial init故障清理 |
| `test_primitives_serialization.cpp`、`test_message_serialization.cpp` | 编码/解码正确性 | socket生命周期无关，不覆盖teardown |

## 3. Source-to-test traceability

| 生命周期/行为 | 实现源码证据 | 现有测试证据 | 覆盖判断 |
|---|---|---|---|
| Socket创建与初始状态 | `socket_factory.cpp`；`udp_socket_impl.hpp`构造 | `test_sockets.cpp:89–94` | PARTIAL：创建及初始connected=false |
| connect/disconnect正常路径 | `udp_socket_impl.hpp:119–190` | `test_sockets.cpp:96–111`；RobotDriver disconnect test | COVERED happy path |
| 重复connect/disconnect | 同上 | `test_sockets.cpp:316–337` | PARTIAL：只验证返回值，不核实native handle/错误状态 |
| start/stop重复调用 | `udp_socket_impl.hpp:293–317` | `test_sockets.cpp:340–369` | PARTIAL：只验证正常调用和幂等返回 |
| callback收包 | `udp_socket_impl.hpp:324–359` | `test_sockets.cpp:129–177` | COVERED happy path |
| 多消息循环收包 | 同上 | `test_sockets.cpp:179–224` | COVERED基本吞吐路径 |
| receive callback stop后不再执行 | Subscriber/Impl析构及stop路径 | 现有测试stop后未断言late callback为零 | GAP |
| Subscriber callback裸this销毁安全 | `real_time_socket_subscriber.cpp:64–83` | `test_rt_socket_interface.cpp:48–70` fixture reset，但无并发销毁/同步断言 | GAP |
| Impl async handler裸this销毁安全 | `udp_socket_impl.hpp:351–359` | 没有销毁与handler执行交错测试 | GAP |
| callback异常隔离 | callback调用路径 | 无throwing callback测试 | GAP |
| close失败后的状态与重试 | `udp_socket_impl.hpp:178–185`、97–101 | 无故障注入 | GAP |
| connect部分失败回滚 | `udp_socket_impl.hpp:119–160` | 无open/options/bind/resolve阶段注入 | GAP |
| stop失败后仍close的行为 | `udp_socket_impl.hpp:167–190` | 无stop失败模拟 | GAP |
| worker join/self-join/timeout | `udp_socket_impl.hpp:307–317` | 无自线程stop、join失败、永久阻塞测试 | GAP |
| RobotDriver双socket部分清理 | `robot_driver.cpp:251–285` | `test_robot_driver.cpp` disconnect happy path | PARTIAL |
| HardwareInterface cleanup/shutdown/error | `staubli_hardware_interface.cpp:190–231` | 测试只覆盖LifecycleTransitions正常流程 | GAP |
| plugin unload生命周期 | plugin XML/CMake export | PluginLoading/PluginLoadingAndInitialization只验证可加载 | PARTIAL |
| mock server partial initialization cleanup | `mock_robot_server.cpp:45–139,147–176` | Init/Disconnect基础测试 | PARTIAL |

## 4. 现有测试的具体限制

### 4.1 Socket tests

`test_sockets.cpp`：

- Fixture用`SocketFactory::create`创建真实socket：42–70行；loopback连接：72–78行。
- 固定使用127.0.0.1与固定端口12345/12346：80–86行。
- ReceiveCallback以promise/future等待数据，最多5秒：129–177行。
- ReceiveMultipleMessages通过50条消息与sleep轮询：179–224行。
- ReconnectAfterDisconnect验证重连后能发收：226–279行。
- DoubleConnect验证第二次connect与两次disconnect均返回成功：316–337行。
- DoubleStartReceiveThread验证第二次start失败、第二次stop成功：340–369行。

**局限：** 这些case没有替换transport实现、注入close错误、验证OS句柄是否真正关闭或模拟callback仍在执行时触发stop/destructor。测试中promise只确认回调曾执行，不是回调已完全排空的证据。

### 4.2 RT subscriber/interface tests

`test_rt_socket_interface.cpp`：

- Fixture创建两个真实UDP socket并connect：39–62行。
- TearDown调用stop_receive_thread与disconnect：64–70行。
- Subscriber fixture reset subscriber：72–83行。
- ReceiveMessage/LostPackageDetection验证消息接收、sequence、lost count和staleness：97行以后。
- BidirectionalCommunication验证interface双向收发：250行以后。

**局限：** fixture的析构顺序有助于正常清理，但没有人为阻塞callback并在另一个线程reset subscriber；也没有证明reset返回后没有迟到的回调访问Subscriber成员。

### 4.3 RobotDriver tests

`test_robot_driver.cpp`：

- fixture构造两条server UDP socket并启动模拟机器人线程：31–150行。
- TearDown先driver disconnect/reset，再释放interface并stop/disconnect server sockets：152–178行。
- ConnectionTest、DisconnectionTest、ReadRobotStateTest验证基本连接、断开和staleness：约250–400行。

**局限：** 使用真实UDP loopback和mock线程；没有fake socket让control关闭成功而diagnostics关闭失败，也没有让stop/close返回失败，无法覆盖partial teardown和残留状态。

### 4.4 HardwareInterface tests

`test_staubli_hardware_interface.cpp`：

- 构造、init与无效HardwareInfo：18–56行。
- configure成功/失败：58–97行。
- pluginlib加载与初始化：99–124行。
- interface export：126–204行。
- LifecycleTransitions执行init/configure/activate/read/write：206行以后。

**局限：** 生命周期测试没有显式调用on_cleanup/on_shutdown/on_error，也没有检查cleanup结果、socket状态、worker线程状态或plugin实例销毁后回调残留。

### 4.5 MockRobotServer tests

`test_mock_robot_server.cpp`覆盖Construction、Initialization、Disconnect、IsReady和未初始化发送/读取拒绝；但未对第二通道连接失败、第一通道已连接后第二通道初始化失败、析构时close失败等情形进行注入。

## 5. Teardown failure-path matrix

| ID | 故障注入点 | 预期安全性质 | 现有覆盖 | 建议测试 |
|---|---|---|---|---|
| F01 | socket.open失败 | 状态保持未连接；无遗留native handle | NONE | FakeNativeSocket open失败 |
| F02 | set_option/bind/resolve失败 | 回滚close；close失败被保留并可观测 | NONE | 每阶段注入异常，检查rollback journal |
| F03 | async receive启动后立即stop | handler不会在owner释放后访问Impl | PARTIAL | barrier阻塞handler后stop |
| F04 | callback正在执行时销毁Subscriber | 不释放Subscriber直到callback lease归零 | NONE | gate + latch确定性并发测试 |
| F05 | callback抛异常 | worker不发生未处理异常终止；错误可报告 | NONE | throwing callback |
| F06 | stop_receive_thread从worker自身调用 | 不self-join；明确拒绝/转交stop | NONE | callback中调用stop |
| F07 | join等待超时/worker卡住 | 不释放仍被访问资源；超时进入residual | NONE | 可控worker阻塞与deadline |
| F08 | socket.close抛异常 | 不把资源误标记为closed；保留owner并允许reconcile | NONE | FakeSocket close失败，检查is_open/connected分离 |
| F09 | stop失败但close成功 | 汇总两个独立结果；不丢失thread residual | NONE | stop false + close success |
| F10 | control close成功、diagnostics close失败 | 部分清理状态逐通道保留；后续只重试残留通道 | NONE | 两通道不同故障脚本 |
| F11 | RobotDriver重复disconnect | 幂等且不掩盖close unknown | PARTIAL | 第一次close fail、第二次retry |
| F12 | Hardware on_cleanup/on_shutdown/on_error | lifecycle返回值与资源终态一致 | NONE | lifecycle callback matrix |
| F13 | plugin实例释放时callback仍活跃 | plugin代码/对象不提前卸载 | NONE | unload与callback latch竞态 |
| F14 | mock server第二通道初始化失败 | 第一通道回滚，接口不残留 | NONE | 第二socket connect失败 |
| F15 | native handle立即复用/重复close | 不关闭已复用的其他handle | NONE | 平台级fd/socket reuse测试 |
| F16 | 远端控制器未确认session关闭 | 状态标记REMOTE_SESSION_UNKNOWN，不冒充关闭成功 | NONE | 协议仿真超时/无ACK |

## 6. 最小可验证实现切片排序

建议严格按切片推进，每个切片先添加可失败的测试，再实现最小代码，不进行一次性全栈重写。

### Slice A — 可注入Transport与状态快照（P0）

目标：建立可测的Socket边界，不改协议行为。

- 引入内部`ISocketTransport`/NativeSocketOps seam，或等价可替换依赖。
- Fake transport可配置open/bind/receive/stop/close返回值和抛出异常。
- 将`connected_、native_is_open、worker_joinable、pending_handlers、callback_inflight`分离成可审计状态快照。
- 测试F01、F02、F08、F09、F11。

完成门槛：close失败后不能仅靠connected flag判断资源已关闭；每个失败步骤与owner身份可观测。

### Slice B — Callback admission与drain barrier（P0）

- callback入口先获取lease；关闭时先关闭admission，再等待active count归零。
- Subscriber与Impl不得以裸this生命周期假设代替明确屏障。
- drain必须有deadline和失败报告；未排空对象进入residual owner，而不是析构释放。
- 测试F03、F04、F05、F13。

完成门槛：并发销毁压力下无late callback、UAF；超时路径保留资源而非释放。

### Slice C — Worker stop/join contract（P0）

- stop语义区分request_stop、worker_exit、join_complete。
- 检查joinable与self-join；定义从worker线程发起stop的策略。
- timeout后不detach并释放owner；记录THREAD_RESIDUAL。
- 测试F06、F07及重复stop。

完成门槛：任何线程状态都不会在join未完成时销毁其访问的Impl成员。

### Slice D — Socket close transaction与per-channel reconcile（P0）

- close操作状态与结果分离：CLOSE_PENDING/CLOSED/CLOSE_OUTCOME_UNKNOWN。
- control/diagnostics独立记录stop、callback drain、native close、remote session状态。
- 失败时保留资源owner，后续reconcile只处理残留，不重复已确认完成的副作用。
- 测试F08–F11、F15、F16。

完成门槛：部分成功可恢复；未知状态不被映射成成功；重复调用不丢失残留。

### Slice E — ROS lifecycle/plugin integration（P1）

- 为on_cleanup/on_shutdown/on_error建立统一teardown入口与错误策略。
- plugin unload前证明HardwareInterface、Subscriber、worker和callback均已终止。
- 测试F12、F13，并补齐plugin实例反复load/unload循环。

完成门槛：lifecycle result与transport resource terminal state一致，卸载后没有代码映像或回调引用残留。

### Slice F — native/platform validation（P1）

- 固定Boost.Asio版本和目标OS版本。
- 增加Linux fd、Windows SOCKET、macOS socket错误注入/复用验证。
- 执行ASan/UBSan/TSan及loopback stress。
- 测试F15，补充跨平台close语义矩阵。

完成门槛：native handle关闭与复用语义由实际目标平台证据支持，而非仅由POSIX/Windows文档推演。

## 7. 验收状态

| ID | 项目 | 状态 |
|---|---|---|
| TEST-MAP-01 | 固定commit测试目标/CMake映射 | STATIC_REVIEWED |
| TEST-MAP-02 | Socket loopback现有case映射 | STATIC_REVIEWED |
| TEST-MAP-03 | RT subscriber/interface case映射 | STATIC_REVIEWED |
| TEST-MAP-04 | RobotDriver case映射 | STATIC_REVIEWED |
| TEST-MAP-05 | HardwareInterface/plugin case映射 | STATIC_REVIEWED |
| FAIL-MATRIX-01 | teardown故障注入点定义F01–F16 | SPECIFIED |
| SLICE-ORDER-01 | A–F最小实现切片排序 | SPECIFIED |
| RUN-01 | 编译、CMake、gtest运行 | NOT_RUN |
| RUN-02 | Fake transport与close failure injection | NOT_RUN |
| RUN-03 | callback drain/UAF并发测试 | NOT_RUN |
| RUN-04 | worker self-join/timeout/callback exception测试 | NOT_RUN |
| RUN-05 | 双通道partial teardown/reconcile测试 | NOT_RUN |
| RUN-06 | ROS lifecycle/plugin unload测试 | NOT_RUN |
| RUN-07 | ASan/UBSan/TSan/native handle reuse | NOT_RUN |
| RUN-08 | VAL3/CS9、SIL/HIL、FAT/SAT、实机 | NOT_RUN |

## 8. 限制与授权边界

- 以上为固定上游提交的测试源码静态审查，不表示任何测试已经通过。
- 未执行CMake、编译、gtest、loopback运行、故障注入、压力测试或sanitizer。
- 未修改上游 `ICube-Robotics/staubli_driver_ros2`，未创建/应用/合并PR。
- `TODO-EXT-001`仍未授权；本轮只提交知识库中的审计报告和计划记录。
- SERVO-884中§9.3.281–§9.3.294历史TaskPlan同步缺口继续保留，不伪造补录。

## 9. 下一节点

**§9.3.303 / SERVO-886：Fake transport seam、socket lifecycle state snapshot与failure-injection contract详细设计（不落上游实现）。**

下一轮应把Slice A细化成接口契约、状态机、FakeTransport行为表、错误注入脚本和单元测试断言；仍不修改上游，直到用户明确授权。
