# Stäubli SocketV2 源码级资源所有权、close-site 追踪与真实依赖 DAG 提取

- 节点：§9.3.301 / SERVO-884
- 审查日期：2026-11-10
- 上游仓库：`ICube-Robotics/staubli_driver_ros2`
- 固定上游提交：`bd658e2d266e315d2ee35f985fb352ea88306b79`
- 方法：固定 commit recursive Git tree + 逐文件源码静态读取；行号按该提交原始文件从 1 开始计数
- 本仓库：`rexyll/robot_knowledgebasement`，仅新增审计文档并同步 TaskPlan/索引

## 1. 结论摘要

本轮首次将 SERVO-882/883 的设计候选资源图映射到固定上游真实源码。确认该提交实现的是 legacy `Socket` 接口 + `UDPSocket` PIMPL + Boost.Asio UDP socket/async receive worker + `RealTimeSocketSubscriber` 回调 + `RobotDriver` 双通道共享所有权 + ros2_control HardwareInterface/plugin。源码中没有 SocketV2、QuarantineManager、ResidualResourceHandle、PluginLease 或独立 cleanup journal 的实现。

最重要的源码事实：

1. `RobotDriver` 创建两个 `shared_ptr<Socket>`（control/diagnostics）；各自的 interface/subscriber 再持有同一 socket 的 `shared_ptr`。这是真实 shared ownership，不等于唯一 logical cleanup authority。
2. `UDPSocket` 以 `unique_ptr<UDPSocketImpl>` 持有实现；Impl成员拥有 Asio `io_service_`、UDP socket、endpoint、receive buffer、`std::thread` 和 callback。
3. async receive handler 以裸 `this` 捕获并访问 Impl 成员；安全性依赖 Impl 存活至 worker/handler 不再访问它。当前 stop 路径先 `io_service_.stop()` 再 `join()`，之后 disconnect 才 `socket_.close()`。
4. Subscriber注册的 callback 以裸 `this` 捕获 Subscriber；Subscriber析构调用 `socket_->stop_receive_thread()`。这提供了一个隐式停止屏障，但源码没有 callback admission gate、active callback计数、独立 lease 或可观测 drain report。
5. `RobotDriver::disconnect()` 先 reset control interface、diagnostics subscriber，再 stop/disconnect两个socket；但仅在 `is_connected()` 为真时进入socket disconnect分支。UDP disconnect即使close抛异常仍把 `is_connected_` 设为false，Impl析构又只在该标志为true时调用disconnect，存在“关闭失败后不再显式重试”的残留风险。
6. `UDPSocketImpl::disconnect()` 的 `stop_receive_thread()` 失败会令 `all_ok=false`，但仍继续 close；`stop_receive_thread()` 当前仅在 `receiving_==true` 时join，未检查joinable/self-join，也没有timeout。
7. `UDPSocketImpl::connect()` 在open之后若后续步骤抛异常，会尝试close；但catch内部的close若再次抛异常，没有第二层保护。
8. CMake将 `udp_socket.cpp` 编入主库，但不编译 `tcp_socket.cpp`；SocketFactory对TCP明确抛出not implemented。树中未找到 `tcp_socket_impl.hpp`，TCP wrapper引用它的实现文件不在该固定树内，因此TCP不纳入真实运行资源DAG。

**审计等级：** 以上为静态源码事实或由明确的C++成员/调用顺序推导出的强推断；没有运行时证据。不得据此声称发生了fd泄漏、UAF、死锁或实机故障。

## 2. 范围、来源与证据规则

### 2.1 固定树与读取文件

本轮读取固定 commit 的 recursive tree，并逐文件读取以下核心文件：

| 文件 | Blob SHA | 读取范围/用途 |
|---|---|---|
| `include/staubli_robot_driver/communication/socket.hpp` | `230af198337e5d047b29b2bbf6354a698fb3a390` | Socket纯虚API、SocketFactory |
| `include/staubli_robot_driver/communication/udp_socket.hpp` | `31eb5e2e9218e17160fc10dfbd72d77be4b3b0e5` | UDPSocket PIMPL与析构声明 |
| `include/staubli_robot_driver/communication/tcp_socket.hpp` | `55790bb891cb5a4e7c3faefda9ba5d25a7f76909` | TCP wrapper接口 |
| `src/communication/udp_socket.cpp` | `c74fe82be22b378273e29b6aba10f9aaccf1f2d8` | façade构造/析构/转发 |
| `src/communication/udp_socket_impl.hpp` | `1309a8f2d59e8295869e178af82a66868bb911ff` | Asio socket、线程、回调、open/close/join |
| `src/communication/socket_factory.cpp` | `dbbc85d6f036e8d1fc035336022a499830f58686` | UDP/TCP factory分支 |
| `src/real_time_socket_subscriber.cpp` | `e2cd8fc50b2b13d9e31b2c024e90f9da76107622` | Subscriber启动、裸this callback、析构stop |
| `src/real_time_socket_interface.cpp` | `eda0a830cfe0118e07bc3423ad0f455bd50d610c` | 双向接口及发送buffer |
| `include/staubli_robot_driver/robot_driver.hpp` | `62c87a6741aa082db4599bb2c048aec0fcd7a464` | shared_ptr成员及声明顺序 |
| `src/robot_driver.cpp` | `ede48a314856a455df9d8434f354aaf9fbc47bff` | 双socket构造、connect、disconnect、析构 |
| `include/staubli_robot_driver/staubli_hardware_interface.hpp` | `a84d0c63b15db168ea453a15571ab1494b8f9e99` | SystemInterface与RobotDriver成员 |
| `src/staubli_hardware_interface.cpp` | `4ae2b8c8d91857e5e32558bfcd16e2c391b9c3d0` | lifecycle、析构、driver disconnect |
| `staubli_hardware_interface.xml` | `eb946e450ef8546b13e1be50836918236fc47966` | pluginlib class registration |
| `CMakeLists.txt` | `b21608627b53d66f9910d9a836b053cd7d7fd6bf` | 编译源文件、测试和plugin导出 |

此外读取 recursive tree，检查 `tcp_socket_impl.hpp` 路径；固定树没有该文件，GitHub contents路径读取亦返回404。这里的404仅证明该路径在指定commit不可读取，不推断其他分支或外部依赖内容。

### 2.2 证据等级

- **CONFIRMED**：直接由固定commit源码、构建清单或plugin XML明确显示。
- **INFERRED**：由C++对象成员、shared_ptr/unique_ptr关系、析构顺序或调用顺序直接推导，但没有运行时验证。
- **UNKNOWN**：源码没有提供足够证据，或依赖库内部行为未纳入本次审查。
- **NOT_FOUND**：在固定commit的tree和读取范围内没有找到相应实现/符号；不是对其他版本作断言。

## 3. Resource ownership inventory

| ID | 资源 | 创建/持有位置 | 使用者/引用关系 | 关闭/释放位置 | 证据与备注 |
|---|---|---|---|---|---|
| R01 | control UDP facade | `RobotDriver::RobotDriver`创建；`control_socket_` | `control_interface_`共享持有同一Socket | `RobotDriver::disconnect`；最后shared_ptr销毁 | CONFIRMED：RobotDriver cpp 26-39；header 150-162 |
| R02 | diagnostics UDP facade | 同上，`diagnostics_socket_` | `diagnostics_subscriber_`共享持有 | 同上 | CONFIRMED：同上 |
| R03 | UDPSocketImpl | `UDPSocket`构造时`make_unique` | UDPSocket独占；实现所有Asio资源 | `UDPSocket`成员unique_ptr析构；Impl析构97-101 | CONFIRMED：udp_socket.cpp 26-28；Impl header 41-44, 88-101 |
| R04 | Asio io_service | Impl成员 | receive worker调用run；start调用reset/stop | Impl对象析构 | CONFIRMED：Impl 72-74, 293-301, 313 |
| R05 | Asio UDP socket/native handle | Impl成员`socket_(io_service_)` | connect/open/bind/resolve/send/async receive | connect失败catch 155-157；disconnect 178-185；Asio成员析构 | CONFIRMED：Impl 72-76, 119-160, 167-190；native fd细节由Boost.Asio封装，UNKNOWN |
| R06 | local/remote/sender endpoints | Impl成员 | bind/local_endpoint/resolve/async_receive_from | 随Impl析构 | CONFIRMED：Impl 75-76, 126-150, 351-359 |
| R07 | receive buffer | Impl成员vector，构造时resize(1024) | Asio async_receive_from与用户callback共享引用 | Impl析构 | CONFIRMED：Impl 78-80, 88-95, 288-290, 351-359 |
| R08 | receive worker thread | Impl成员`std::thread` | 执行io_service_.run | stop_receive_thread 313-316 join；若仍joinable时Impl析构行为需遵守std::thread规则 | CONFIRMED：Impl 81-83, 296-302, 307-317 |
| R09 | socket receive callback | Impl成员`std::function` | handler调用；Subscriber注册lambda | 下一次start覆盖或Impl析构释放 | CONFIRMED：Impl 83, 272-278, 341-347 |
| R10 | async receive handler | `start_receive`中Asio async_receive_from lambda | 捕获裸`this`并调用handle_data_received | Asio完成/取消/销毁行为取决于io_service/socket生命周期 | CONFIRMED捕获形式：Impl 351-359；handler最终排空语义UNKNOWN |
| R11 | Subscriber对象 | `make_shared<RealTimeSocketSubscriber>`或基类子对象 | 保存shared_ptr<Socket>；注册回调 | Subscriber析构调用stop_receive_thread | CONFIRMED：subscriber cpp 29-38, 64-76, 79-83 |
| R12 | Subscriber callback target | lambda捕获裸`this` | UDP handler调用update_message；更新message_buffer_ | Subscriber析构先stop线程，期望阻断后续回调 | CONFIRMED捕获：subscriber cpp 64-70；drain屏障强度仍需运行时验证 |
| R13 | Subscriber message buffer | RealtimeThreadSafeBox<MessageType>成员 | async callback set；读线程try_get | Subscriber成员析构 | CONFIRMED：subscriber header private成员；cpp 87-102, 106-149 |
| R14 | RealTimeSocketInterface outgoing buffer | `data_out_`成员，构造时resize | send_message序列化并调用Socket::send | interface对象析构 | CONFIRMED：interface cpp 29-36, 44-60 |
| R15 | RobotDriver interface/subscriber owners | `control_interface_`、`diagnostics_subscriber_` shared_ptr成员 | 分别共享持有control/diagnostics Socket | disconnect显式reset；否则RobotDriver成员析构 | CONFIRMED：RobotDriver header 155-162；cpp 251-259 |
| R16 | HardwareInterface RobotDriver | `on_init` make_shared | lifecycle callbacks/read/write调用 | on_cleanup/on_shutdown/析构尝试disconnect；成员随后析构 | CONFIRMED：hardware cpp 43-47, 132-174, 190-231；header 80-83 |
| R17 | plugin class image/loader lease | pluginlib XML注册SystemInterface类 | pluginlib加载类；源码没有显式lease类型 | loader/ROS plugin管理器外部负责 | plugin注册CONFIRMED；lease、卸载屏障NOT_FOUND/UNKNOWN |
| R18 | remote controller session | 由远端控制器协议/VAL3管理 | UDP控制/诊断通信 | 本地disconnect不证明远端session已关闭 | UNKNOWN：本次C++源码未发现独立session close/ack |

**所有权语义提醒：** R01/R02由RobotDriver与interface/subscriber形成shared ownership图；真正的停止线程动作当前由Subscriber析构触发，socket native handle关闭由Socket::disconnect/Impl析构路径执行。源码没有声明一个显式且唯一的logical cleanup authority对象。

## 4. close-site / teardown traceability matrix

| Site | 源码位置 | 操作 | 前置条件/顺序 | 错误与幂等性 | 风险/证据 |
|---|---|---|---|---|---|
| C01 | udp_socket_impl.hpp:97-101 | Impl析构中若is_connected则disconnect | 依赖flag反映资源状态 | 不检查socket_.is_open；flag false时跳过显式disconnect | CONFIRMED；close失败后flag仍可能false，析构不再显式重试 |
| C02 | udp_socket_impl.hpp:119-121 | socket_.open(UDPv4) | connect阶段 | 异常进入catch | CONFIRMED |
| C03 | udp_socket_impl.hpp:153-160 | connect失败时若is_open则socket_.close；flag=false | 捕获open/options/parse/bind/resolve异常 | close本身若抛异常，没有嵌套catch | CONFIRMED；错误路径异常安全不完整 |
| C04 | udp_socket_impl.hpp:167-190 | disconnect：必要时stop worker，再socket_.close | 仅在is_connected为true时close | stop结果合入all_ok但仍继续close；close异常记all_ok=false；无论close成功与否都store(false) | CONFIRMED；关闭失败后状态flag与真实open状态可能分离 |
| C05 | udp_socket_impl.hpp:307-317 | io_service_.stop(); receive_thread_.join(); receiving_=false | receiving_为true | 无超时、无joinable/self-join检查；若false直接返回true | CONFIRMED；不能仅凭return true证明所有handler/callback已安全排空 |
| C06 | real_time_socket_subscriber.cpp:79-83 | Subscriber析构stop_receive_thread | socket_应有效 | 忽略stop返回值；无显式callback lease/count | CONFIRMED；析构清理失败不可见 |
| C07 | robot_driver.cpp:251-259 | reset control interface与diagnostics subscriber | 在socket disconnect之前 | reset会触发Subscriber析构stop | CONFIRMED；正确依赖顺序但结果未传播 |
| C08 | robot_driver.cpp:261-285 | 对仍is_connected的socket stop receive then disconnect | 以is_connected作门禁 | stop失败只warning，仍继续disconnect；flag false时跳过disconnect | CONFIRMED；残留资源可能被状态flag隐藏 |
| C09 | robot_driver.cpp:41-43 | RobotDriver空析构 | 依赖成员逆序析构 | 无显式disconnect/report | CONFIRMED；成员逆序析构推断：subscriber/interface先于socket owner释放 |
| C10 | staubli_hardware_interface.cpp:43-47 | HardwareInterface析构调用driver.disconnect | robot_driver_非空 | 忽略disconnect返回值 | CONFIRMED |
| C11 | staubli_hardware_interface.cpp:190-231 | on_cleanup/on_shutdown/on_error | lifecycle状态/driver连接状态 | cleanup忽略disconnect结果；shutdown仅connected时STOP+disconnect；on_error只发STOP不disconnect | CONFIRMED；与ROS资源回收顺序未做运行时验证 |
| C12 | udp_socket_impl.hpp:324-359 | receive callback与重挂async receive | handler持有裸this | callback异常未见catch；若异常越过io_service worker入口，行为需运行时确认 | CONFIRMED调用路径；异常传播结果UNKNOWN |

### 4.1 直接native close调用情况

在本轮读取的固定提交Socket/UDP/driver源码中，没有直接调用POSIX `::close`、`shutdown`、Windows `closesocket` 或直接保存整数fd的代码。native handle封装在Boost.Asio `boost::asio::ip::udp::socket` 内；因此：
- **CONFIRMED：** 应用层显式close-site为Asio `socket_.close()`（Impl 156、179行）。
- **UNKNOWN：** Boost.Asio该版本/平台的内部native handle释放实现、错误状态与系统调用细节，本轮未拉取依赖源码，不能将SERVO-883的POSIX/Linux规则直接当作该实现已验证事实。
- **NOT_FOUND：** 应用源码中没有独立remote-session shutdown/ack，也没有直接plugin unload API。

## 5. 固定源码的真实依赖 DAG

### 5.1 节点

| DAG节点 | 实际对象 | 状态 |
|---|---|---|
| D0 | RobotDriver | CONFIRMED |
| D1 | control/diagnostics Socket shared owners | CONFIRMED |
| D2 | UDPSocket façade | CONFIRMED |
| D3 | unique_ptr<UDPSocketImpl> | CONFIRMED |
| D4 | Asio io_service + UDP socket + endpoints | CONFIRMED |
| D5 | receive buffer + std::function callback | CONFIRMED |
| D6 | receive worker std::thread | CONFIRMED |
| D7 | async_receive_from handler（裸this） | CONFIRMED |
| D8 | RealTimeSocketInterface / Subscriber | CONFIRMED |
| D9 | Subscriber lambda callback（裸this） | CONFIRMED |
| D10 | RealtimeThreadSafeBox message buffer | CONFIRMED |
| D11 | StaubliHardwareInterface / pluginlib SystemInterface | CONFIRMED |
| D12 | plugin loader/code image lease | UNKNOWN；没有应用级显式对象 |
| D13 | remote controller session | UNKNOWN；未发现独立session teardown |

### 5.2 有向引用/生命周期边

以下箭头表示“持有、访问或必须先完成的生命周期依赖”，不是所有权等价关系：

- D0 → D1：RobotDriver成员持有两个shared_ptr Socket。
- D8 → D1：interface/subscriber构造时复制shared_ptr Socket。
- D1 → D2：SocketFactory创建UDPSocket façade（静态类型为Socket）。
- D2 → D3：UDPSocket独占Impl（unique_ptr）。
- D3 → D4：Impl直接拥有Asio service/socket/endpoints。
- D3 → D5：Impl拥有buffer与callback function。
- D3 → D6：Impl拥有receive thread对象。
- D6 → D7：worker执行io_service_.run，处理异步handler。
- D7 → D3：handler捕获裸this，反向依赖Impl存活（关键生命周期边）。
- D5 → D9：callback function保存Subscriber lambda。
- D9 → D8：lambda捕获Subscriber裸this（关键生命周期边）。
- D9 → D10：回调调用update_message写入message buffer。
- D8 teardown → D6：Subscriber析构请求stop_receive_thread并join worker。
- D0 disconnect → D8 teardown → D1 disconnect：RobotDriver先reset接口/subscriber，再停止/断开socket。
- D11 → D0：HardwareInterface持有RobotDriver shared_ptr。
- D12 ⇢ D11：plugin loader必须保证类代码在对象析构期间仍可用；本源码没有显式lease边实现。
- D13 ⇢ D1/D4：本地UDP socket与远端控制器会话可能相关，但协议没有显示可验证的关闭确认。

### 5.3 可从源码确认的 teardown 顺序

正常显式路径为：

1. RobotDriver reset control interface；
2. RealTimeSocketSubscriber基类析构请求停止对应Socket receive thread；
3. RobotDriver reset diagnostics subscriber，停止第二条receive thread；
4. 对connected control socket调用stop（如仍receiving）并disconnect；
5. 对connected diagnostics socket执行相同流程；
6. reset RobotDriver缓存数据。

HardwareInterface的on_cleanup/destructor会调用RobotDriver::disconnect；on_shutdown仅在driver报告connected时尝试STOP并disconnect；on_error不释放transport。

这不是SERVO-882的理想化候选顺序：源码中没有单独的admission-close、active-callback counter、async operation drain journal、protocol session shutdown、plugin lease或quarantine owner步骤。

### 5.4 DAG风险边

- **E-RACE-01（CONFIRMED结构 / 运行时影响UNKNOWN）：** D7→D3裸this；必须证明Impl销毁前handler不再运行。
- **E-RACE-02（CONFIRMED结构 / 运行时影响UNKNOWN）：** D9→D8裸this；Subscriber析构stop/join是隐式屏障，缺少显式active callback计数与失败报告。
- **E-STATE-03（CONFIRMED）：** C04 close异常后仍将is_connected置false，C01析构可能跳过disconnect；状态位不再足以证明native socket已关闭。
- **E-STATE-04（CONFIRMED）：** RobotDriver仅以is_connected决定是否调用disconnect；若flag与Asio socket真实open状态分离，显式清理分支被跳过。
- **E-JOIN-05（CONFIRMED）：** join没有joinable/self-thread检查和超时；实际调用上下文是否可能self-stop，源码未证明，标记UNKNOWN。
- **E-EXC-06（CONFIRMED）：** user callback调用未包catch；异常对worker的影响未执行验证。
- **E-SESSION-07（NOT_FOUND）：** 本地socket close不能证明远端session已结束；源码无session close/ack状态。
- **E-PLUGIN-08（UNKNOWN）：** pluginlib注册可见，但没有显式PluginLease/卸载前资源屏障实现。

## 6. 未发现或未能确认的资源

| 项目 | 结论 | 说明 |
|---|---|---|
| SocketV2 / SocketFactoryV2 | NOT_FOUND | 固定树未发现v2实现 |
| QuarantineManager / RetryScheduler | NOT_FOUND | 仅前序知识库设计概念 |
| ResidualResourceHandle / CleanupReport / cleanup journal | NOT_FOUND | 未实现 |
| 显式 callback admission gate / active callback counter | NOT_FOUND | 当前只有 receiving_布尔值 |
| 显式 async operation count / drain barrier | NOT_FOUND | 未发现 |
| 显式 plugin lease / code-image reference counter | NOT_FOUND | plugin XML仅注册类 |
| 直接OS fd/socket整数owner | NOT_FOUND | 由Boost.Asio封装 |
| 直接POSIX close/shutdown调用 | NOT_FOUND | 显式应用close为Asio socket_.close |
| TCP socket implementation | NOT_FOUND | tree未找到tcp_socket_impl.hpp；CMake未编译tcp_socket.cpp；factory拒绝TCP |
| remote controller session close/ACK | NOT_FOUND | 未见协议级确认 |
| native Boost.Asio内部close细节 | UNKNOWN | 依赖源码/目标平台不在本轮范围 |

## 7. SERVO-884 验收矩阵

以下均为静态审计交付项；运行时验收仍需独立执行。

| ID | 验收项 | 状态 |
|---|---|---|
| SRC-OWN-01 | 固定commit tree与blob身份记录 | STATIC_REVIEWED |
| SRC-OWN-02 | Socket/UDPSocket/Impl owner链 | STATIC_REVIEWED |
| SRC-OWN-03 | control/diagnostics shared ownership关系 | STATIC_REVIEWED |
| SRC-OWN-04 | Subscriber裸this callback生命周期边 | STATIC_REVIEWED |
| SRC-OWN-05 | Asio handler裸this生命周期边 | STATIC_REVIEWED |
| CLOSE-TRACE-01 | open/close/disconnect/destructor sites定位 | STATIC_REVIEWED |
| CLOSE-TRACE-02 | stop/join/callback teardown sites定位 | STATIC_REVIEWED |
| CLOSE-TRACE-03 | HardwareInterface lifecycle teardown映射 | STATIC_REVIEWED |
| DAG-REAL-01 | 源码引用DAG节点/边提取 | STATIC_REVIEWED |
| DAG-REAL-02 | unknown/not-found边界与证据等级 | STATIC_REVIEWED |
| DAG-REAL-03 | cycle detection/运行时barrier验证 | NOT_RUN |
| RUN-01 | C++编译、CMake、gtest | NOT_RUN |
| RUN-02 | UDP loopback/close失败/partial connect故障注入 | NOT_RUN |
| RUN-03 | handler/callback drain与UAF压力验证 | NOT_RUN |
| RUN-04 | join self-call、thread residual、异常callback注入 | NOT_RUN |
| RUN-05 | fd/socket leak、double-close、句柄复用检测 | NOT_RUN |
| RUN-06 | ASan/UBSan/TSan | NOT_RUN |
| RUN-07 | ROS 2 Control lifecycle/plugin load-unload | NOT_RUN |
| RUN-08 | Boost.Asio目标版本与Linux/macOS/Windows native行为核验 | NOT_RUN |
| RUN-09 | VAL3/CS9、SIL/HIL、FAT/SAT、实机 | NOT_RUN |

## 8. 整改优先级与后续工作

### P0：必须先冻结的生命周期安全契约

1. 用资源状态快照而非`is_connected_`单一布尔值驱动disconnect；至少区分 facade state、Asio socket is_open、worker joinable、pending handler/callback状态。
2. 关闭路径不得在close失败后把状态标记成“已关闭”；保留close outcome unknown与真实owner，提供显式retry/reconcile。
3. Subscriber与Impl的裸this捕获需要显式callback lease/admission barrier，或证明当前stop+join在目标Asio版本下足以形成安全屏障。
4. stop必须检查thread.joinable与self-join；定义从callback/worker线程调用stop时的行为，不能无界等待。
5. callback异常必须在线程入口隔离并记录，避免异常越过worker边界。
6. disconnect即使connected flag为false也应检查底层资源快照，避免flag失真导致跳过真实close。

### P1：所有权与集成契约

1. 明确RobotDriver是两个transport的logical cleanup authority；interface/subscriber仅持有Socket shared reference并拥有各自receive lease，而不是让析构副作用隐式决定全局生命周期。
2. 分开记录control/diagnostics清理结果，stop失败、close失败和缓存reset不得互相覆盖。
3. HardwareInterface的on_cleanup/on_shutdown/on_error应有统一且可审计的transport teardown policy；on_error目前只发送STOP，不释放transport。
4. plugin unload前需由ROS/plugin管理层证明hardware interface析构完成且没有回调/worker继续执行；当前源码无显式lease机制。

### P2：依赖与平台核验

1. 固定Boost版本与Asio源码版本，读取Asio socket close/cancel/io_context handler dispatch实现。
2. 明确Linux/macOS/Windows目标平台与错误语义，不把POSIX close(2)直接等同于Boost.Asio socket.close()异常语义。
3. TCP wrapper的缺失实现和构建清单不一致应单独清理；本轮不补写上游代码。
4. 对remote controller session增加协议层明确的close/timeout/epoch语义；本地UDP close不是远端确认。

## 9. 限制与未执行项

- 本轮是固定提交源码静态读取，不是动态执行或安全证明。
- 未运行编译、CMake、gtest、UDP loopback、native close失败注入、fd/socket复用、泄漏/双重关闭检查、线程竞态测试、ASan/UBSan/TSan。
- 未运行ROS 2 Control生命周期、plugin加载/卸载、VAL3/CS9、SIL/HIL、FAT/SAT或实机。
- 未审计Boost.Asio依赖源码内部实现，native handle关闭细节标记UNKNOWN。
- 未修改上游 `ICube-Robotics/staubli_driver_ros2`，未创建/应用/合并PR。
- `TODO-EXT-001`仍未授权。
- 本轮只在知识库仓库main分支增加审计报告与计划索引记录。

## 10. 下一节点

**§9.3.302 / SERVO-885：SocketV2 source-to-test coverage gap analysis、lifecycle teardown failure-path matrix 与最小可验证实现切片排序。**

下一轮应把SRC-OWN/CLOSE-TRACE/DAG-REAL发现映射到现有gtest源码和CMake测试目标，识别哪些路径已有测试、哪些仅测试了表面API、哪些需要FakeSocket/loopback/native fault injection；先冻结最小实现切片与验收证据，再考虑任何上游修改。