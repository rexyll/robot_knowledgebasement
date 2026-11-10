# Stäubli SocketV2 固定提交 CMake/源码清单、Private Seam Placement 与 ABI Baseline 可行性审查

- **节点：** §9.3.305 / SERVO-888
- **日期：** 2026-11-10
- **固定上游基线：** `ICube-Robotics/staubli_driver_ros2@bd658e2d266e315d2ee35f985fb352ea88306b79`
- **知识库分支：** `rexyll/robot_knowledgebasement@main`
- **关联：** SERVO-884（源码资源所有权）、SERVO-886（fake seam合同）、SERVO-887（实现策略与ABI/CMake guard）
- **审查性质：** 固定提交文件级静态证据核验与构建可复现性评估；不代表实现或构建验收。

## 1. 执行摘要

本轮通过 GitHub 固定 commit 读取了 package 的 CMake、package manifest、legacy socket public headers、UDP facade/implementation、SocketFactory、plugin XML、README 与 CI workflow。证据足以确认 legacy API 边界、当前两个 shared library target、现有源文件编译归属、install/export规则和 CI 声明的 ROS 发行版；但不足以形成可复现 ABI 二进制基线，也不足以宣称完整 recursive source inventory、真实 CMake target graph 或安装消费验证已完成。

**结论：A1.1 只能进入“候选位置已缩小、准入仍阻塞”的设计状态；不得开始上游实现。** 推荐 private seam 放在 `staubli_robot_driver/src/communication/` 的未安装私有实现层，并由现有 `UDPSocket` façade 的 PIMPL/单一 Core 持有；最终具体文件位置必须先检查固定树完整文件列表、所有 include/call sites、编译单元边界和构建依赖。不能把该目录建议误写成已证明无泄漏。

## 2. 固定提交与证据清单

以下文件均通过 GitHub contents API 指定固定 commit 读取；SHA 为对应文件 blob：

| 路径 | Blob SHA | 本轮观察到的事实 |
|---|---|---|
| `staubli_robot_driver/CMakeLists.txt` | `b21608627b53d66f9910d9a836b053cd7d7fd6bf` | C++17；主库与 hardware interface 两个 SHARED target；源文件清单、install/export、gtest目标 |
| `staubli_robot_driver/package.xml` | `50ad11f1336aab87a9afca6b9751de9fb6766595` | package 0.1.4；ament_cmake；ROS依赖与测试依赖 |
| `.../communication/socket.hpp` | `230af198337e5d047b29b2bbf6354a698fb3a390` | legacy Socket纯虚接口及SocketFactory声明 |
| `.../communication/udp_socket.hpp` | `31eb5e2e9218e17160fc10dfbd72d77be4b3b0e5` | UDPSocket继承Socket，private unique_ptr<UDPSocketImpl>，析构声明out-of-line |
| `.../communication/tcp_socket.hpp` | `55790bb891cb5a4e7c3faefda9ba5d25a7f76909` | TCPSocket public header也位于include树，具有private PIMPL |
| `src/communication/socket_factory.cpp` | `dbbc85d6f036e8d1fc035336022a499830f58686` | UDP转UDPSocketFactory；TCP明确抛出not implemented |
| `src/communication/udp_socket.cpp` | `c74fe82be22b378273e29b6aba10f9aaccf1f2d8` | UDP façade转发到UDPSocketImpl |
| `src/communication/udp_socket_impl.hpp` | `1309a8f2d59e8295869e178af82a66868bb911ff` | Asio实现定义在私有头；直接持有io_service/socket/endpoints/buffer/thread/callback |
| `staubli_hardware_interface.xml` | `eb946e450ef8546b13e1be50836918236fc47966` | plugin library path为staubli_robot_driver_hardware_interface |
| `.github/workflows/ci.yml` | `7073f620d30f10cf595c4211188d349f279ef16e` | Ubuntu Noble容器标签；target ROS 2 distro Jazzy |
| `README.md` | `ce1dd2263e32724b7d3c4e7d66fc0b7ead9762c8` | 项目声明基于Jazzy/Ubuntu 24.04；CS9控制器；文档称项目仍为prototype |

另对固定 commit 元数据核验：提交信息为 Dependabot 将 actions/checkout 从 v6 升级到 v7，提交日期 2026-07-03。该提交SHA本身可读取，但它不是构建产物或依赖锁文件。

## 3. 源码与 CMake target inventory

### 3.1 当前 package target

固定提交的 `staubli_robot_driver/CMakeLists.txt` 定义：

- `${PROJECT_NAME}`，即 `staubli_robot_driver`：SHARED library。源清单包含 protocol.cpp、messages.cpp、socket_factory.cpp、udp_socket.cpp、real_time_socket_subscriber.cpp、real_time_socket_interface.cpp、robot_driver.cpp、mock_robot_server.cpp。
- `${PROJECT_NAME}_hardware_interface`，即 `staubli_robot_driver_hardware_interface`：SHARED library，仅由 staubli_hardware_interface.cpp 构建，并链接主库。
- `test_receive_robot_state`：独立 executable，链接主库，安装到 lib/${PROJECT_NAME}。
- BUILD_TESTING下创建多个 ament gtest目标，测试辅助函数统一链接主库；hardware interface测试另链接hardware interface library。
- plugin XML通过 `pluginlib_export_plugin_description_file(hardware_interface staubli_hardware_interface.xml)` 导出。

### 3.2 Socket相关编译归属

- 主库明确编译 `socket_factory.cpp` 与 `udp_socket.cpp`。
- 主库**未列出** `tcp_socket.cpp`，也没有编译 `tcp_socket_impl.hpp` 对应实现单元。
- CMake源清单未单独列出 `udp_socket_impl.hpp`；它由 `udp_socket.cpp` include，属于当前实现私有头。
- `SocketFactory::create(TCP)` 在固定源码中抛出 `TCP protocol not implemented yet`。
- TCP public header存在于 `include/`，而CMake安装整个 `include/` 目录；因此TCP声明会随头文件树安装，但这不证明TCP实现已进入主库。对外可见声明与实际可用实现之间存在需要显式记录的边界风险。
- 尝试按猜测路径读取 `src/communication/tcp_socket_impl.hpp` 返回404。该路径不能被视为固定树中的文件；本轮不推断是否存在其他命名或位置的TCP实现。

### 3.3 public/private与PIMPL边界

- `socket.hpp` 位于 `include/staubli_robot_driver/communication/`，定义legacy `Socket` 和 `SocketFactory`；其virtual接口包括两种connect重载、disconnect、is_connected、send、receive_once、start_receive_thread、stop_receive_thread、is_receiving。
- `udp_socket.hpp` 和 `tcp_socket.hpp` 同样位于public include树；两个facade均以 `unique_ptr<...Impl>` 持有前置声明实现类，析构函数声明为out-of-line。
- UDP Asio实现位于 `src/communication/udp_socket_impl.hpp`，不是public include路径；其类定义直接包含Boost.Asio及ROS logging依赖。
- 当前CMake执行 `install(DIRECTORY include/ DESTINATION include)`，因此整个include目录都是安装面；没有按单个头文件allowlist安装，也没有显式排除detail/private子目录的规则。
- 本轮在已读取文件中未发现项目级显式 `CXX_VISIBILITY_PRESET hidden`、`VISIBILITY_INLINES_HIDDEN` 或符号版本脚本配置。此观察不等价于证明编译器/工具链默认导出行为；需读取完整构建配置及实际动态符号表。

### 3.4 ament export与plugin

- 两个shared library target通过同一 `install(TARGETS ... EXPORT export_${PROJECT_NAME})` 安装并导出。
- `ament_export_targets(export_${PROJECT_NAME} HAS_LIBRARY_TARGET)` 导出target集合。
- `ament_export_dependencies` 显式列出rclcpp、std_msgs、sensor_msgs、geometry_msgs、control_msgs、hardware_interface、pluginlib、rclcpp_lifecycle；CMake find依赖列表另含realtime_tools。
- Boost通过 `find_package(Boost REQUIRED COMPONENTS system)` 并链接 `Boost::system`；package.xml本身未显式出现Boost depend条目。本轮不判断其rosdep传递依赖是否足够，需在目标ROS环境用rosdep/colcon验证。
- `target_include_directories(${PROJECT_NAME} PUBLIC ... ${asio_SOURCE_DIR}/asio/include)` 引用了 `asio_SOURCE_DIR`，但本轮读取的该CMake文件未看到为该变量设置值或执行对应find_package。它可能来自外层构建/宏或缺失配置；当前只能登记为需要追踪的变量来源，不能断言配置必然失败。
- plugin XML的library path为hardware interface库；类名为 `staubli_robot_driver/StaubliHardwareInterface`，类型为 `staubli_robot_driver::StaubliHardwareInterface`，基类为 `hardware_interface::SystemInterface`。

## 4. Private seam placement proof

### 4.1 当前证据支持的候选位置

优先候选：`staubli_robot_driver/src/communication/` 下的私有backend/core实现文件，供 `udp_socket.cpp` 通过内部头使用；test-only builder/fake 放在 `staubli_robot_driver/test/` 或独立未安装的test-support源码目录。生产构造路径仍只实例化Asio backend。

该候选基于以下已观察事实：
1. 当前UDP Asio实现已处于src私有实现头，而非public include目录。
2. UDP facade已具有PIMPL，且public facade可以保持既有接口不变。
3. 主库target已有UDP实现编译单元，test目标通过主库链接；当前没有单独test-support target。
4. include目录整体安装，因此任何放入include树的seam/fake头文件都默认落入安装面，除非改造安装规则。

### 4.2 尚未完成的placement proof

下列证据缺失，故不能判定A1.1准入：
- 固定commit recursive tree的完整、可审计文件清单及所有socket相关include/call-site交叉引用；
- CMake configure后的实际target graph、compile command与生成的ament export/package config；
- 完整安装manifest与安装后include closure；
- 真实 `nm -D`/`readelf -Ws` 导出符号与plugin动态依赖清单；
- 对所有public headers、inline/template代码、宏和可见性属性的全量扫描；
- test-only support在BUILD_TESTING=OFF/ON两种配置下的依赖闭包证据；
- plugin unload、callback与backend completion生命周期屏障的可运行验证。

### 4.3 Placement准入判据

只有全部满足后，才能将A1.1从SPECIFIED提升为通过：
1. private interface及Fake源码不在install include树、不进入安装manifest；
2. production core/plugin target不链接test-support、gtest或Fake；
3. 测试目标可通过受限私有入口构造同一SocketCore，不复制状态机；
4. CMake graph、ament export、plugin DT_NEEDED及动态导出符号均无test-only泄漏；
5. BUILD_TESTING=OFF时无test-support target/符号，生产目标仍可构建；
6. BUILD_TESTING=ON时Fake只由测试可执行文件使用；
7. 无ODR冲突、重复Core或双重cleanup owner；
8. callback、worker、backend与plugin unload屏障通过确定性测试。

## 5. Reproducible ABI baseline feasibility

### 5.1 当前可获得的环境线索

- README明确写明当前开发基于ROS 2 Jazzy、Ubuntu 24.04 LTS，目标控制器CS9。
- CI workflow使用 `rostooling/setup-ros-docker:ubuntu-noble-latest`，并设置 `target-ros2-distro: jazzy`。
- package CMake要求C++17，并在GNU/Clang条件下增加 `-Wall -Wextra -Wpedantic`。
- CMake要求Boost system，但未在该文件中固定Boost精确版本；本轮没有找到锁定ROS二进制仓库快照、编译器精确版本、系统包清单或完整colcon构建参数的证据。
- workflow使用可变容器标签 `ubuntu-noble-latest`；该标签本身不能保证跨时间重建相同编译器、系统库和ROS依赖。
- 本轮没有读取到固定commit对应的同环境已构建shared library、debug info、compile_commands.json、install tree或ABI dump。

### 5.2 ABI baseline可行性判断

**当前状态：BLOCKED（可复现二进制基线未建立）。**

可以基于固定commit源码生成API/头文件审查清单；但不能据此声称已完成ABI兼容性比较。生成可用ABI基线至少需要：
- 固定OS镜像digest，而不是latest标签；
- 固定ROS Jazzy apt仓库快照及全部二进制包版本；
- 固定GCC/Clang、binutils、CMake、Ninja/Make、Boost版本；
- 固定架构、构建类型、编译器flags、宏、visibility、LTO与链接选项；
- 固定colcon/ament构建命令及环境变量；
- 从固定commit构建并归档两个shared library、debug info、compile commands、install manifest、plugin metadata；
- 同一环境下运行ABI dumper/compliance checker，或使用readelf/nm + DWARF/layout probe作为有记录的替代方案。

本轮未确认abi-dumper、abi-compliance-checker、libabigail/abidiff等工具是否安装，也未获得任何旧版二进制产物。工具可用性与基线产物均为NOT_RUN/BLOCKED，不得用源码签名比对替代二进制ABI结论。

## 6. 风险登记与行动

| ID | 风险/问题 | 当前证据 | 处置 |
|---|---|---|---|
| INV-01 | include目录整体安装 | CMake install(DIRECTORY include/) | private seam/fake禁止放入include |
| INV-02 | TCP public header安装但TCP wrapper未列入主库 | tcp_socket.hpp存在；CMake无tcp_socket.cpp；factory拒绝TCP | 保持TCP实现范围独立，不把头文件存在误判为可用 |
| INV-03 | asio_SOURCE_DIR来源未在本文件中闭合 | CMake使用变量但未见定义 | 查完整tree/外层构建及CI实际configure |
| INV-04 | Boost依赖声明闭包待核验 | CMake find/link Boost；package.xml无显式Boost depend | 在干净Jazzy环境rosdep/colcon验证 |
| INV-05 | ABI环境不固定 | CI latest标签；依赖/编译器未锁定 | 建立镜像digest与包版本锁定 |
| INV-06 | 缺少基线产物 | 未获得旧版so/debug info/ABI dump | 先从固定commit可复现构建并归档 |
| INV-07 | test-only target隔离尚未实现 | 当前gtest helper直接链接主库，无独立test-support target | 设计CMake graph断言后再实施 |
| INV-08 | 符号可见性和导出闭包未知 | 未读取产物 | 获取so后nm/readelf检查 |

## 7. SERVO-888验收矩阵

| ID | 验收项 | 状态 | 说明 |
|---|---|---|---|
| SRC-INV-01 | 固定commit CMake/package/README/CI关键文件读取 | STATIC_REVIEWED | 已读取并记录blob SHA |
| SRC-INV-02 | Socket/SocketFactory/UDP façade与impl位置 | STATIC_REVIEWED | 已核对具体路径与内容 |
| SRC-INV-03 | CMake source-to-target映射 | STATIC_REVIEWED | 主库、hardware interface、测试与receiver executable已核对 |
| SRC-INV-04 | plugin XML注册信息 | STATIC_REVIEWED | XML文件已读取 |
| SRC-INV-05 | 完整recursive tree及全部include/call-site inventory | BLOCKED | 本轮未获得可审计完整tree |
| PLACE-01 | private seam候选目录识别 | SPECIFIED | 候选src/communication私有实现层 |
| PLACE-02 | private/install/ament/plugin泄漏证明 | NOT_RUN | 缺install manifest、target graph、符号和动态依赖产物 |
| PLACE-03 | 单一Core与测试注入所有权证明 | NOT_RUN | 尚无实现 |
| ABI-FEAS-01 | README/CI环境线索核验 | STATIC_REVIEWED | Jazzy/Noble/C++17线索 |
| ABI-FEAS-02 | 完整依赖与工具链精确锁定 | BLOCKED | 缺image digest、包版本、编译器精确版本 |
| ABI-FEAS-03 | 固定commit同环境构建产物 | BLOCKED | 未获得/未构建so与debug info |
| ABI-FEAS-04 | ABI工具可用性与结构比较 | NOT_RUN | 未运行abi-dumper/abidiff/nm/readelf |
| CMAKE-BASE-01 | BUILD_TESTING ON/OFF target graph | NOT_RUN | 未configure |
| CMAKE-BASE-02 | install manifest与ament export closure | NOT_RUN | 未安装/未检查 |
| CMAKE-BASE-03 | plugin动态依赖和导出符号 | NOT_RUN | 无构建产物 |
| GATE-01 | 允许进入A1.1实现 | BLOCKED | placement proof与ABI baseline尚未满足 |

## 8. 决策与下一步

1. **不进入A1.1代码实现。** 当前只确认了候选私有目录和部分真实CMake/source映射；安装面、target graph、全树引用、ABI baseline仍不闭合。
2. 下一步优先补齐固定commit recursive tree及所有Socket引用/头文件清单，核对`asio_SOURCE_DIR`的定义来源与Boost依赖声明。
3. 在可访问的Ubuntu 24.04 + ROS Jazzy环境建立固定commit构建配方；锁定镜像digest、apt包版本、编译器、Boost、CMake/colcon参数。
4. 若构建可复现，归档legacy两个shared libraries、debug info、compile commands、install manifest和plugin metadata；运行符号/ABI/layout工具。
5. 只有ABI基线与private/install/test-only边界证据齐备，才进入A1.1 private interface/PIMPL implementation；否则维持BLOCKED并记录精确缺口。

## 9. 明确未执行事项

未修改固定上游；未创建、应用或合并上游PR；未实施SocketV2/private seam/Fake/CMake改动；未运行CMake configure/build、colcon、gtest、ABI工具、nm/readelf、install-space consumer、plugin load/unload、sanitizer、loopback、SIL/HIL、VAL3/CS9、FAT/SAT或实机测试。未确认硬件/控制器协议兼容性。工程级验收未通过，`TODO-EXT-001`仍未授权。历史同步缺口§9.3.281–§9.3.294继续透明保留，不伪造回填。
