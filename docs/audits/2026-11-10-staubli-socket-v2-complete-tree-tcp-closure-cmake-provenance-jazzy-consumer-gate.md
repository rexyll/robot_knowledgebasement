# Stäubli SocketV2 固定提交完整 Git Tree、TCP Impl 闭包、CMake 变量来源与 Jazzy Consumer Gate 审查

- 审查日期：2026-11-10
- 固定上游：`ICube-Robotics/staubli_driver_ros2@bd658e2d266e315d2ee35f985fb352ea88306b79`
- Commit Tree：`257face41970c91f95890ddf47db40b168eca331`
- 范围：SERVO-890；只读静态审查，不修改上游。

## 1. 完整 Git Tree 证据

通过 GitHub Git Database commit/tree API 取得固定 commit 元数据及递归 Tree。commit 指向 Tree `257face41970c91f95890ddf47db40b168eca331`；递归结果 `truncated=false`，共 **284** 个条目。固定树顶层包含 `.docker/`、`.github/` 与五个 ROS package；没有 gitlink/submodule entry、`.gitmodules`、`.repos` 或 rosinstall manifest。该结论限于该固定 commit 的 Git Tree，不代表构建环境外部不存在注入。

通信目录完整清单：
- public headers：messages.hpp、protocol.hpp、serialization.hpp、socket.hpp、tcp_socket.hpp、udp_socket.hpp；
- sources：messages.cpp、protocol.cpp、socket_factory.cpp、tcp_socket.cpp、udp_socket.cpp；
- private impl headers：udp_socket_impl.hpp；
- 未发现 `tcp_socket_impl.hpp` 的任何路径或大小写变体。

Tree 的递归响应未截断，因此本轮可以将“固定仓库树中没有 tcp_socket_impl.hpp”从此前的路径级 NOT_FOUND 提升为 **TREE_REVIEWED**。这仍不排除构建系统从仓库外部生成/注入该文件，但本仓库未提供生成器或子模块证据。

## 2. TCP façade 与 factory 闭包

固定 commit 文件证据：
- `staubli_robot_driver/src/communication/tcp_socket.cpp` blob `cdb18d03b0413cd9d88758c63fefaae51e3f5e29`：实现 TCPSocket façade 与 TCPSocketFactory；源码 include 同目录 `tcp_socket_impl.hpp`。
- `staubli_robot_driver/include/staubli_robot_driver/communication/tcp_socket.hpp` blob `55790bb891cb5a4e7c3faefda9ba5d25a7f76909`：声明 TCPSocket 与前置声明 TCPSocketImpl。
- 完整递归 Tree 不含 `tcp_socket_impl.hpp`。
- `staubli_robot_driver/CMakeLists.txt` blob `b21608627b53d66f9910d9a836b053cd7d7fd6bf` 的 LIBRARY_SOURCES 包含 socket_factory.cpp 与 udp_socket.cpp，未包含 tcp_socket.cpp。
- `socket_factory.cpp` blob `dbbc85d6f036e8d1fc035336022a499830f58686` 只 include socket.hpp 与 udp_socket.hpp；UDP 分支返回 UDPSocketFactory，TCP 分支明确抛出 `TCP protocol not implemented yet`。

**结论：** TCP public façade header 和 façade .cpp 存在，但实现闭包不完整（缺失 Impl header），且 façade .cpp 未进入当前主库 target；公共 SocketFactory 明确拒绝 TCP。不能将该 TCP façade 描述为可构建、可链接或可运行的 TCP transport。SERVO-889 对“文件存在但未编译、Impl 未闭合”的描述得到完整 Tree 证据加强；无须反向更正其勘误。

## 3. CMake 变量与 Asio/Boost 来源

- 固定 Tree 中只有五个 CMakeLists.txt，分别属于 bringup、meta package、MoveIt config、robot description、robot driver；未见额外 CMake module 或第三方 Asio 子树。
- 固定 commit 的代码搜索 `asio_SOURCE_DIR` 只命中 driver CMake 的 PUBLIC include path：`${asio_SOURCE_DIR}/asio/include`。未发现 set/cache、find_package(asio)、FetchContent、ExternalProject、add_subdirectory(asio)、toolchain/CI 参数定义或仓库内依赖清单定义该变量。
- driver CMake 实际执行 `find_package(Boost REQUIRED COMPONENTS system)` 并链接 `Boost::system`；UDP Impl 直接 include `<boost/asio.hpp>`。
- Tree 中无 submodule/gitlink、vcs manifest；Dockerfile 只使用 `osrf/ros:${ROS_DISTRO}-desktop-full`，运行 rosdep install 与 colcon build，没有显式拉取 standalone Asio 或设置 `asio_SOURCE_DIR`。
- 因此 `asio_SOURCE_DIR` 在仓库内的定义/供给来源为 **UNRESOLVED**。Boost.Asio 与 CMake 中 standalone Asio include path 同时出现，需在实际配置环境中检查该变量是否为空、是否由外部父工程/缓存/环境注入，以及 include path 是否真实存在；不能仅凭静态代码断言 CMake 必然失败。
- CI workflow 使用 `rostooling/setup-ros-docker:ubuntu-noble-latest` 并通过 `ros-tooling/action-ros-ci@0.4.8` 构建 Jazzy；未锁定镜像 digest 或 apt snapshot。Dockerfile同样使用可变 ROS distro tag。

## 4. package.xml / rosdep / ament export 声明闭包

固定 driver package.xml 包含 realtime_tools，但不显式声明 boost 或 backward_ros。CMake 对 Boost system 和 backward_ros 使用 REQUIRED 查找；Dockerfile 依赖 `rosdep install --from-paths src --ignore-src -r -y` 安装声明依赖。故静态上存在 package manifest 与 CMake 直接依赖不对称，但底层 ROS 镜像/系统包可能预装相关组件，当前证据不足以推断干净环境必然失败。

另有 export 风险：realtime_tools 位于 package.xml 和 `ament_target_dependencies`，但未列入 `ament_export_dependencies`；安装的 public header `real_time_socket_subscriber.hpp` include realtime_tools 头文件。是否影响 install-space 下游 consumer，须以实际 install metadata 和独立 consumer 验证。

## 5. 干净 Jazzy 验证边界

本轮没有运行容器、apt/rosdep、CMake configure、colcon build/test、install-space consumer 或 ABI 工具。因此以下均为 NOT_RUN：
1. Noble/Jazzy 固定镜像 digest + apt snapshot 的干净环境；
2. rosdep resolve/install 对 Boost、backward_ros 的实际覆盖；
3. CMake configure 时 `asio_SOURCE_DIR` 的最终值、include path存在性与 target property；
4. BUILD_TESTING=ON/OFF 的构建与测试；
5. install-space 的独立 ament consumer（不继承原 workspace build 环境）；
6. plugin metadata、DT_NEEDED/导出符号、ABI dump 与可复现 ABI baseline。

## 6. A1.1 准入门禁（仍未满足）

进入 A1.1 前至少需：
- 取得并归档固定 commit 的可复现基线构建环境与依赖版本；
- 解决 `asio_SOURCE_DIR` 的定义来源，确认它是必要依赖还是陈旧 include 项；
- 对 Boost/backward_ros/realtime_tools 完成 manifest、rosdep、CMake 与 ament export 的一致性核验；
- 在干净 Jazzy 环境完成 rosdep + colcon build/test；
- 完成 install-space 独立 consumer，验证 public headers/include closure 与 exported dependencies；
- 取得 shared library、debug info、compile_commands、install manifest、plugin metadata、ABI/symbol baseline；
- 对 TCP façade 作明确处置：保持不可用并排除未闭合源文件，或在另行授权范围内补齐实现；不得将缺失 Impl 当作已实现功能；
- 保持 private seam/Fake 仅在 private/test-only 层，完成 production/test target、install/export 与 plugin 依赖隔离证明。

任一关键证据缺失，A1.1 = BLOCKED。不得通过静态推断将 NOT_RUN 改为 PASS。

## 7. 状态

| 项目 | 状态 |
|---|---|
| 固定 commit recursive Tree（284 entries, not truncated） | TREE_REVIEWED |
| TCP Impl 文件在固定 Tree 中缺失 | TREE_REVIEWED |
| TCP façade source/header 存在但未进入主库 target | STATIC_REVIEWED |
| SocketFactory TCP 分支拒绝 | STATIC_REVIEWED |
| `asio_SOURCE_DIR` 仓库内定义来源 | UNRESOLVED |
| Boost/backward_ros manifest 对称性 | STATIC_REVIEWED / RISK |
| realtime_tools ament export 闭包 | STATIC_REVIEWED / RISK |
| rosdep/colcon/build/test | NOT_RUN |
| install-space consumer | NOT_RUN |
| ABI baseline | BLOCKED |
| A1.1 implementation gate | BLOCKED |

## 8. 安全边界与后续

未修改固定上游；未创建、应用或合并上游 PR；`TODO-EXT-001`仍未授权。未运行构建、测试、ABI、plugin 或硬件验证。历史同步缺口 §9.3.281–§9.3.294 继续透明保留。

**下一节点：§9.3.308 / SERVO-891**：在不修改上游的前提下，整理 clean Jazzy validation harness / dependency provenance evidence package、install-space consumer fixture 与 A1.1 gate checklist；若本执行环境无法运行 ROS Jazzy，则明确列出需外部CI提供的证据与最小复现命令，保持所有运行项 NOT_RUN。
