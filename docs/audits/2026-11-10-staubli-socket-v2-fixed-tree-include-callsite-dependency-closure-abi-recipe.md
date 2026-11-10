# Stäubli SocketV2 固定树 Socket 引用闭包、Asio/Boost 依赖来源与 ABI 构建配方审查

- **节点：** §9.3.306 / SERVO-889
- **日期：** 2026-11-10
- **固定上游：** `ICube-Robotics/staubli_driver_ros2@bd658e2d266e315d2ee35f985fb352ea88306b79`
- **知识库：** `rexyll/robot_knowledgebasement@main`
- **关联：** SERVO-884至SERVO-888
- **审查性质：** GitHub固定commit文件级静态检索与依赖声明闭包检查；不是完整recursive tree审计、CMake configure或ABI构建验证。

## 1. 执行摘要

本轮补充检索固定提交中Socket/TCP/UDP/Asio引用和调用点，纠正SERVO-888报告中的TCP源码描述，并检查CMake、package.xml与public header的依赖闭包。

**重要纠错：固定提交存在 `src/communication/tcp_socket.cpp`，其实现TCPSocket façade及TCPSocketFactory；但该源文件未加入主库 `LIBRARY_SOURCES`。该文件include `tcp_socket_impl.hpp`，在预期同目录路径读取返回404，代码搜索也只找到这一include引用。** 因而正确描述是：TCP façade源文件存在但未编入当前主库；其Impl定义在固定提交可检索证据范围内未找到；`SocketFactory::create(TCP)`仍明确抛出not implemented。不得将其简化成“tcp_socket.cpp不存在”，也不得宣称TCP可用。

另外，`asio_SOURCE_DIR`只在CMake include path中出现，未发现其定义或Asio standalone package discovery；UDP impl实际包含`<boost/asio.hpp>`，CMake查找Boost system并链接`Boost::system`。package.xml未声明Boost或backward_ros依赖；CMake对`realtime_tools`使用ament target dependency，但`ament_export_dependencies`未列出它，而已安装public header直接包含realtime_tools头。上述均为依赖闭包风险，必须在干净ROS Jazzy环境用rosdep/colcon与独立consumer验证，当前不能直接断言构建必然失败。

## 2. 固定commit文件证据

| 路径 | Blob SHA | 观察 |
|---|---|---|
| `staubli_robot_driver/CMakeLists.txt` | `b21608627b53d66f9910d9a836b053cd7d7fd6bf` | C++17；主库源文件清单；Boost查找；PUBLIC include含asio_SOURCE_DIR；安装/ament导出/test target |
| `staubli_robot_driver/package.xml` | `50ad11f1336aab87a9afca6b9751de9fb6766595` | 声明ROS包依赖与test依赖；未见boost/backward_ros |
| `include/staubli_robot_driver/communication/socket.hpp` | `230af198337e5d047b29b2bbf6354a698fb3a390` | legacy Socket纯虚接口、SocketFactory |
| `include/staubli_robot_driver/communication/udp_socket.hpp` | `31eb5e2e9218e17160fc10dfbd72d77be4b3b0e5` | UDPSocket façade与unique_ptr PIMPL |
| `include/staubli_robot_driver/communication/tcp_socket.hpp` | `55790bb891cb5a4e7c3faefda9ba5d25a7f76909` | TCPSocket façade与unique_ptr PIMPL |
| `src/communication/tcp_socket.cpp` | `cdb18d03b0413cd9d88758c63fefaae51e3f5e29` | TCP façade方法及TCPSocketFactory实现；include tcp_socket_impl.hpp |
| `src/communication/tcp_socket_impl.hpp` | NOT_FOUND | 固定路径contents读取404；代码搜索仅发现tcp_socket.cpp中的include引用 |
| `src/communication/socket_factory.cpp` | `dbbc85d6f036e8d1fc035336022a499830f58686` | UDP走UDPSocketFactory；TCP抛出runtime_error |
| `src/communication/udp_socket.cpp` | `c74fe82be22b378273e29b6aba10f9aaccf1f2d8` | UDP façade与UDPSocketFactory实现 |
| `src/communication/udp_socket_impl.hpp` | `1309a8f2d59e8295869e178af82a66868bb911ff` | 直接包含boost/asio.hpp并定义UDP Asio实现 |
| `include/staubli_robot_driver/real_time_socket_subscriber.hpp` | 由代码搜索定位 | public header include realtime_tools/realtime_thread_safe_box.hpp |
| `src/robot_driver.cpp` | `ede48a314856a455df9d8434f354aaf9fbc47bff` | 两个SocketFactory调用均选择UDP |
| `.github/workflows/ci.yml` | `7073f620d30f10cf595c4211188d349f279ef16e` | ubuntu-latest runner；ubuntu-noble-latest ROS容器；ROS Jazzy |

文件路径及blob SHA以GitHub固定commit读取结果为准。代码搜索索引仅用于定位候选文件/引用，不视为完整树清单；无法据此证明未命中的文件不存在。

## 3. Socket include/call-site closure

### 3.1 Legacy Socket public surface

- `socket.hpp`声明抽象`Socket`，含两种connect overload、disconnect、is_connected、send、receive_once、start_receive_thread、stop_receive_thread、is_receiving等virtual方法；`SocketFactory::create(ProtocolType)`是静态工厂入口。
- `udp_socket.hpp`和`tcp_socket.hpp`均继承`Socket`，分别以`unique_ptr<UDPSocketImpl>`与`unique_ptr<TCPSocketImpl>`持有实现。
- CMake以`install(DIRECTORY include/ DESTINATION include)`安装整个public include目录；两个Socket façade header都在安装面。private seam/fake不得新增到该目录。

### 3.2 UDP生产调用链（本轮检索到的路径）

- `SocketFactory::create(UDP)` -> `UDPSocketFactory::create()` -> `std::make_shared<UDPSocket>()`。
- `UDPSocket`在`udp_socket.cpp`构造`UDPSocketImpl`并逐项转发调用。
- `udp_socket_impl.hpp`直接包含`<boost/asio.hpp>`，使用`boost::asio::io_service`、UDP socket/endpoints、async_receive handler与std::thread。
- `RobotDriver`创建control与diagnostics两个UDP Socket；`MockRobotServer`同样创建UDP sockets。
- 检索结果定位到socket unit test与real-time socket interface test；它们使用Socket/UDPSocket接口，当前没有代码搜索证据显示测试构造TCP Socket。

### 3.3 TCP源码边界

- `tcp_socket.hpp`声明TCPSocket PIMPL及TCPSocketFactory。
- `tcp_socket.cpp`确实存在并实现facade所有方法与factory，但没有出现在CMake `LIBRARY_SOURCES`列表。
- `tcp_socket.cpp`包含同目录`tcp_socket_impl.hpp`，该路径固定commit读取404；对`tcp_socket_impl.hpp`的代码搜索只返回tcp_socket.cpp这个include引用。
- `SocketFactory::create(TCP)`并不调用`TCPSocketFactory::create()`，而是直接抛出`TCP protocol not implemented yet`。
- 因此TCP目前只能认定为“存在未编入的facade translation unit与public declaration；Impl source/header在已检索证据范围未闭合；公共工厂不支持TCP”。是否仓库其他目录/子模块存在实现，因缺完整recursive tree仍为UNKNOWN。

## 4. CMake/manifest依赖闭包

### 4.1 Boost.Asio路径

CMake同时执行：
- `find_package(Boost REQUIRED COMPONENTS system)`
- 主库链接`Boost::system`
- 主库PUBLIC include directories中包含`${asio_SOURCE_DIR}/asio/include`

UDP实现实际使用`#include <boost/asio.hpp>`，因此主要Asio头文件来源应由Boost include目录提供。固定CMake文件中未见`set(asio_SOURCE_DIR ...)`、`find_package(asio ...)`、`FetchContent`或`ExternalProject`定义；固定commit代码搜索对`asio_SOURCE_DIR`仅命中该CMake使用点。其变量来源当前为UNRESOLVED。若它在colcon独立package configure时为空，生成include路径可能退化为`/asio/include`；这是否导致configure/build失败需实测，不能仅凭静态文本下最终结论。该PUBLIC路径看起来可能是遗留的standalone Asio路径，但没有证据证明其历史来源，故不作断言。

### 4.2 package.xml与ament exports

- CMake的`DEPENDENCIES`含rclcpp、std_msgs、sensor_msgs、geometry_msgs、control_msgs、realtime_tools、hardware_interface、pluginlib、rclcpp_lifecycle；逐项find_package并ament_target_dependencies主库。
- package.xml声明上述ROS依赖，包括realtime_tools。
- CMake另执行`find_package(backward_ros REQUIRED)`，但package.xml未见`backward_ros`依赖声明。
- CMake执行`find_package(Boost REQUIRED COMPONENTS system)`并链接Boost::system，但package.xml未见`boost`依赖声明。
- `ament_export_dependencies`列表含rclcpp、std_msgs、sensor_msgs、geometry_msgs、control_msgs、hardware_interface、pluginlib、rclcpp_lifecycle，**遗漏realtime_tools**。
- 已安装public header `real_time_socket_subscriber.hpp` include `realtime_tools/realtime_thread_safe_box.hpp`，因此对外头文件依赖与ament export清单存在待闭合点。
- 是否可由ROS环境的系统依赖、其他包传递依赖或特定rosdep规则补齐，必须通过干净环境rosdep/colcon和下游consumer验证；静态证据只证明声明不对称，不足以断言必然失败。

### 4.3 依赖闭包风险表

| ID | 观察 | 风险 | 后续证据 |
|---|---|---|---|
| DEP-01 | asio_SOURCE_DIR只有使用点，没有定义点 | include path来源不可复现，可能产生无效PUBLIC include | 干净colcon configure trace、CMakeCache、compile_commands |
| DEP-02 | Boost由CMake查找/链接，package.xml无boost | rosdep依赖声明可能不完整 | rosdep check/install与干净环境构建 |
| DEP-03 | backward_ros由CMake REQUIRED查找，package.xml无依赖 | 干净环境依赖安装可能缺失 | rosdep check与干净环境构建 |
| DEP-04 | realtime_tools出现在package.xml及ament_target_dependencies，但不在ament_export_dependencies | 下游包含安装public header时依赖传播可能不完整 | install-space独立consumer configure/build |
| DEP-05 | TCP facade源文件存在但未进LIBRARY_SOURCES；impl头未找到 | 不可将TCP声明当作受支持实现 | 完整tree与CMake target graph核验 |

## 5. ABI baseline构建配方（定义，不执行）

建议建立一次性可追溯的legacy baseline构建容器，要求记录：

1. OCI镜像：固定Ubuntu 24.04基础镜像digest；禁止使用latest标签作为最终身份。
2. ROS：固定ROS 2 Jazzy apt snapshot及每个相关deb的精确版本；记录rosdep数据库版本/解析结果。
3. 工具链：固定GCC/G++、binutils、CMake、Ninja/Make、Python、colcon、Boost与所有ROS包版本。
4. 源码：固定上游commit SHA及所有submodule/vcs依赖SHA；保存git status与source manifest。
5. 构建：固定`BUILD_TESTING`、Release/Debug选择、C++ flags、宏、visibility、LTO、架构、环境变量及完整colcon命令。
6. 产物：归档两个SHARED library、debug symbols、compile_commands.json、CMakeCache、生成的ament package config、install manifest、plugin XML及依赖版本清单。
7. ABI工具：记录abi-dumper/abi-compliance-checker或libabigail/abidiff版本；若工具不可用，保存`readelf -Ws`、`nm -D --defined-only`、DWARF/layout probe与public header consumer结果。
8. 重建验证：在干净容器中重复构建，比较导出符号、ABI dump与关键产物哈希；不一致时先解释非确定因素，不能把一次成功构建称为可复现基线。

**当前可行性状态仍为BLOCKED**：没有执行容器构建，没有锁定镜像digest/apt快照/编译器Boost版本，没有同环境旧版shared library和debug info；本节只是待执行配方。

## 6. Private seam placement影响

- 继续建议把private backend/core放在`src/communication/`未安装实现层，避免改变legacy public Socket vtable与安装头文件集合。
- UDP seam必须围绕现有`UDPSocketImpl`实际Asio依赖设计；生产路径继续默认Boost.Asio。
- TCP façade/Impl现状不闭合，不能将其纳入共享Core迁移范围或以TCP测试证明通用transport抽象已经成立。
- Fake/TestBuilder放test-only源码/target；不得由public header、主库生产依赖或plugin间接引入。
- 任何A1.1准入前，必须先获取完整recursive tree，确认TCP Impl是否缺失/在其他位置、所有include/call sites、构建变量来源、manifest依赖和独立consumer闭包。

## 7. SERVO-889验收矩阵

| ID | 项目 | 状态 | 说明 |
|---|---|---|---|
| CALL-01 | SocketFactory UDP/TCP分支 | STATIC_REVIEWED | 固定commit socket_factory.cpp |
| CALL-02 | RobotDriver与MockRobotServer UDP构造调用点 | STATIC_REVIEWED | 搜索定位并读取RobotDriver |
| CALL-03 | TCP façade source存在性与内容 | STATIC_REVIEWED | tcp_socket.cpp已读取 |
| CALL-04 | TCP Impl定义完整闭包 | BLOCKED | 同目录impl header 404，完整树不可用 |
| CALL-05 | 完整recursive tree与所有include/call-site穷尽证明 | BLOCKED | GitHub连接器未提供tree/list API；代码搜索不是穷尽性证明 |
| CMAKE-01 | asio_SOURCE_DIR定义来源 | BLOCKED | 固定文件/代码搜索仅找到使用点 |
| DEP-01 | Boost/backward_ros manifest闭包 | STATIC_REVIEWED | CMake与package.xml声明不对称 |
| DEP-02 | realtime_tools ament export闭包 | STATIC_REVIEWED | public header include，但export list未列 |
| DEP-03 | rosdep/干净环境构建验证 | NOT_RUN | 无干净ROS Jazzy构建环境 |
| ABI-RECIPE-01 | 可复现构建配方定义 | SPECIFIED | 本报告第5节 |
| ABI-RECIPE-02 | 镜像/apt/工具链锁定 | BLOCKED | 尚无锁定产物 |
| ABI-RECIPE-03 | 固定commit基线构建/ABI dump | NOT_RUN | 未执行 |
| PLACE-01 | private seam候选边界 | SPECIFIED | src/communication私有实现层 |
| GATE-01 | 进入A1.1实现 | BLOCKED | 源码树、依赖闭包、ABI基线仍不满足 |

## 8. 决策与下一步

1. 修正SERVO-888记录：TCP源码文件存在但未编入主库；TCP Impl头未在固定预期路径找到。保留其余已核验事实。
2. 下一节点应先取得固定commit完整Git tree（可通过GitHub tree API、git clone/checkout或可复现源码归档），不能继续仅凭代码搜索宣称穷尽。
3. 在真实ROS Jazzy/Noble环境执行CMake configure trace，查明`asio_SOURCE_DIR`的实际值、include path与变量来源；验证Boost/backward_ros manifest依赖和realtime_tools export闭包。
4. 取得完整TCP相关文件后决定TCP scope：若实现缺失/不可构建，明确列为unsupported/deferred；不得让它混入UDP Slice A1验收。
5. 完成锁定环境及legacy ABI基线构建后，重新评估A1.1准入。当前保持BLOCKED。

## 9. 未执行事项与治理限制

未修改固定上游；未创建、应用或合并上游PR；未执行CMake configure/build、colcon、rosdep、gtest、ABI dumper/abidiff、nm/readelf、install-space consumer、plugin load/unload、sanitizer、SIL/HIL、VAL3/CS9、FAT/SAT或实机测试。未证明TCP实现完整、未证明依赖闭包在干净环境可用、未建立ABI baseline。工程级验收未通过；`TODO-EXT-001`仍未授权。历史同步缺口§9.3.281–§9.3.294继续透明保留。
