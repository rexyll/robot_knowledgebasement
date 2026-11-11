# SERVO-907 ROS Jazzy 双配置 install-space consumer 隔离预检

- 日期：2026-11-11
- 仓库：`rexyll/robot_knowledgebasement`，分支 `main`
- 上游审查对象：`ICube-Robotics/staubli_driver_ros2@bd658e2d266e315d2ee35f985fb352ea88306b79`
- 相关工作流：`.github/workflows/staubli-ros-jazzy-build.yml`
- 相关驱动脚本：`scripts/run_staubli_build_testing_matrix.sh`

## 1. 预检发现

在真实 ROS Jazzy workflow 尚未触发前，对 SERVO-906 双配置脚本进行执行路径复核。脚本依次执行 `BUILD_TESTING=OFF` 与 `ON` 两套 build/install，并在每套安装空间构建独立 consumer。

原脚本在同一个父 Bash 进程中依次执行：

1. source 当前模式的 `install/setup.bash`；
2. 构建当前模式的 install-space consumer；
3. 再 source `/opt/ros/jazzy/setup.bash`，继续下一模式。

ROS setup 脚本会扩展而非重置环境前缀。父进程因此可能保留上一模式的 `AMENT_PREFIX_PATH`、`CMAKE_PREFIX_PATH`、`COLCON_PREFIX_PATH`、`PYTHONPATH`、`LD_LIBRARY_PATH` 或 `ROS_PACKAGE_PATH`。在 OFF/ON 连续执行时，这可能使后续 consumer 搜索路径包含前一模式安装空间，削弱双配置独立性；这是脚本环境隔离风险，不是已观察到的构建失败，也未在 ROS 容器中动态复现。

## 2. 修复

- 提交 `e03ed8a3e862354f0bf6693daadbfd3b2dc20f9d`：将每个 install-space consumer 构建放入独立子 shell。
- 在子 shell 内先清除上述 ROS/CMake/Python/动态库前缀变量，再 source 基础 ROS Jazzy setup 和当前模式的 install setup。
- 子 shell 退出后不向父 shell传播当前模式的 overlay 环境，避免 OFF/ON consumer 互相污染。
- 提交 `44068f6b470781f6e2b26b821153e46830741a69`：新增脚本合同测试，静态断言每个 consumer 使用清洁环境并 source 当前模式的安装空间。

## 3. 验收状态

| 项目 | 状态 | 说明 |
|---|---|---|
| 脚本修复 | IMPLEMENTED | 已提交知识库 main |
| 回归合同测试 | IMPLEMENTED | 已增加静态测试断言 |
| Bash 语法 | PENDING_CI | 等待main CI执行 |
| Python pytest/Ruff | PENDING_CI | 等待main CI执行 |
| ROS Jazzy OFF/ON build/install | NOT_RUN | 独立手动workflow尚未触发 |
| OFF/ON install-space consumer | NOT_RUN | 需真实容器运行 |
| gtest | NOT_RUN | 需真实容器运行 |
| ABI/plugin/sanitizer/HIL/实机 | NOT_RUN | 不属于本次静态预检 |

## 4. 结论与限制

本次发现并修复的是测试驱动脚本的双配置环境隔离风险。修复提交与静态合同测试不构成真实 ROS 构建通过证据。必须在固定 ROS Jazzy 镜像中触发 `workflow_dispatch`，检查两个配置各自的 build/install/consumer 日志与证据包，才能更新运行状态。

未修改固定 Stäubli 上游；未创建、应用或合并上游 PR；`TODO-EXT-001`未授权；A1.1保持BLOCKED。不得将本报告中的静态修复描述为ROS构建、gtest、plugin、ABI、sanitizer、HIL或实机验收通过。

 
## 5. 追加静态复核：Ament 导出依赖闭包待实测

对固定上游 `staubli_robot_driver/CMakeLists.txt` 与 `package.xml` 再次逐项比对，确认：

- CMake 的生产目标通过 `target_link_libraries(${PROJECT_NAME} Boost::system)` 显式链接 `Boost::system`。
- CMake 对生产目标和硬件接口目标调用 `ament_target_dependencies(... ${DEPENDENCIES})`；`DEPENDENCIES` 包含 `realtime_tools`。
- CMake 还执行 `find_package(backward_ros REQUIRED)`。
- 但末尾的 `ament_export_dependencies(...)` 清单没有列出 `Boost`、`backward_ros` 或 `realtime_tools`；package.xml 也没有声明 Boost/backward_ros 对应依赖（此前SERVO-905/906已记录该类依赖元数据缺口）。

这构成 install-space 下游导入/链接的**待验证风险**：导出的 imported target 可能引用未被下游自动发现的依赖目标或 include/link 元数据。它尚不是已复现失败；最终判定必须以固定ROS Jazzy镜像中的 OFF/ON install-space consumer build及其完整CMake错误日志为准。当前consumer fixture通过 `find_package(staubli_robot_driver REQUIRED)` 并包含上游公开头文件，原则上应保留真实依赖暴露路径，不应在consumer侧额外调用 `find_package(Boost)` 来掩盖上游导出缺口。

**处理决策：** 不修改固定上游；不在知识库中伪造上游修复。若真实consumer失败，先保存最小失败日志与导出文件证据，再归类为上游包元数据/导出缺陷，并按授权边界提出修复建议。若consumer通过，也只关闭该具体导入路径风险，不推导出所有依赖导出均完备。

## 6. 当前执行状态复核

- main HEAD复核：`17fad6eb2d8007e4b4629ebe47cb58a0f9ad005e`。
- ROS Jazzy手动workflow检查：最近workflow runs列表中没有该workflow的 `workflow_dispatch` 运行；仅有常规Python CI push runs。
- CI #3622（Run ID `42958783662`）及其后续TaskPlan提交触发的常规CI均为SUCCESS；不代表ROS/C++构建。
- OFF/ON真实colcon build/install、install-space consumer、gtest仍为`NOT_RUN`。
- A1.1继续`BLOCKED`；`TODO-EXT-001`未授权；固定上游不修改。


## 7. Consumer 测试加强：显式链接 Ament 导出的 CMake target

复核发现，原consumer虽然执行`find_package(staubli_robot_driver REQUIRED)`，但通过`ament_target_dependencies()`间接消费包。为使测试直接覆盖固定上游的现代CMake导出接口，现将consumer改为显式链接：

```cmake
find_package(staubli_robot_driver REQUIRED)
add_executable(staubli_install_consumer main.cpp)
target_link_libraries(
  staubli_install_consumer
  PRIVATE staubli_robot_driver::staubli_robot_driver
)
```

依据ROS 2官方ament_cmake文档，`ament_export_targets()`导出CMake targets，供下游通过`target_link_libraries(client PRIVATE package::target)`消费；`ament_export_dependencies()`负责让下游无需自行find_package库的传递依赖。来源：[ROS 2 ament_cmake documentation](https://github.com/ros2/ros2_documentation/blob/rolling/source/Developer-Tools/Build/Ament-CMake-Documentation.rst)。

**改动提交：** 脚本`ed422168d8669eb683281c80101b6e60ade61f36`；静态合同测试`22fc89228c9533bc9adfc91e442b05ee324b3cc7`。新增测试要求consumer直接链接`staubli_robot_driver::staubli_robot_driver`，并禁止回退为间接ament_target_dependencies写法。

此改动让真实consumer更直接地检查导出target及其传递链接接口；若导出target名称、Boost::system目标发现或其他依赖元数据不完整，预期会在真实CMake配置/链接阶段暴露。它仍未在ROS Jazzy容器中运行，故当前只能标记为IMPLEMENTED / NOT_RUN，不能宣称已验证通过。

## 8. 2026-11-11 最新 CI 与手动工作流状态复核

- **main HEAD：** `f457650bd8eea50276c55c910dee9508fc87af74`。
- **CI #3638：** Run ID `42960630349`，完成状态 `success`；五个作业（Python 3.10/3.11/3.12、OSV、SBOM）均成功。
- **CI #3639：** Run ID `42960648358`，由当前 main HEAD 触发，完成状态 `success`；五个作业全部成功，无失败步骤。该结果验证知识库 Python/静态合同及供应链检查，不执行 ROS Jazzy 容器构建。
- **手动 ROS workflow：** 检查 main 最近 100 条 Actions runs，未发现路径 `.github/workflows/staubli-ros-jazzy-build.yml` 的运行记录，也未发现该 workflow 的 `workflow_dispatch` 运行。工作流文件本身已存在，触发方式仍为 GitHub Actions 页面手动运行。
- **真实验收：** `BUILD_TESTING=OFF/ON` colcon build/install、两套 install-space consumer、gtest、证据包生成与SHA-256验证仍为 `NOT_RUN`。不得以CI #3638/#3639替代。
- **当前处理：** 无需修复本轮普通CI；继续保持固定上游未修改、未创建/应用/合并上游PR、`TODO-EXT-001`未授权、A1.1 `BLOCKED`。

**下一步：** 用户需手动运行 [Stäubli ROS Jazzy build/install workflow](https://github.com/rexyll/robot_knowledgebasement/actions/workflows/staubli-ros-jazzy-build.yml)。运行完成后再依据job日志和artifact决定是否存在可修复的脚本缺陷或上游依赖导出问题。

## 9. CI #3640–#3641 最终结果与手动触发条件

- **CI #3640 / Run ID `42961639340`：** `completed / success`；Python 3.10、3.11、3.12、OSV、SBOM五个job均成功，无失败step。
- **CI #3641 / Run ID `42961648789`：** `completed / success`；Python 3.10、3.11、3.12、OSV、SBOM五个job均成功，无失败step。
- **触发提交：** #3640对应`95d139d8b953fafc6542860f476a7764b1f92f21`；#3641对应`293b849738f46996000aa4b55e383223fe2684ef`。
- **ROS workflow定义复核：** `.github/workflows/staubli-ros-jazzy-build.yml`在main中存在，触发器为`workflow_dispatch`，固定ROS镜像digest及固定上游commit。最近Actions运行列表仍无该workflow的运行记录。
- **权限边界：** GitHub官方文档说明手动运行要求workflow文件位于默认分支，且操作者需要仓库write权限；可在Actions页面选择workflow、分支并点击Run workflow。当前集成GitHub工具没有可用的workflow-dispatch写操作，因此本轮不能代替用户触发，也不能伪称已启动。
- **验收结论：** 常规CI #3640/#3641成功仅验证知识库Python/静态合同/OSV/SBOM；真实ROS Jazzy OFF/ON build/install、install-space consumer、gtest、artifact与SHA-256仍`NOT_RUN`。

**用户触发入口：** [Stäubli ROS Jazzy build/install evidence](https://github.com/rexyll/robot_knowledgebasement/actions/workflows/staubli-ros-jazzy-build.yml)。需要有仓库write权限；选择`main`后点击`Run workflow`。真实运行完成后再审查失败日志及证据包。

## 10. Consumer 链接验证加强与 CI #3643–#3645 复核

### 10.1 普通 CI 复核

- CI #3643 / Run ID `42962209018`：SUCCESS；Python 3.10/3.11/3.12、OSV、SBOM五个job全部成功。
- CI #3644 / Run ID `42962218477`：SUCCESS；Python 3.10/3.11/3.12、OSV、SBOM五个job全部成功。
- CI #3645 / Run ID `42962228904`：SUCCESS；Python 3.10/3.11/3.12、OSV、SBOM五个job全部成功。
- 上述均为常规知识库CI，不执行ROS Jazzy/C++构建。

### 10.2 新发现与修正

此前install-space consumer的`main.cpp`仅包含`protocol.hpp`并立即返回0。即使CMake声明链接了`staubli_robot_driver::staubli_robot_driver`，也没有实际调用上游共享库中的非内联符号，因而不足以证明链接器完成了该库符号解析。

依据固定上游commit中的`FrameHeader::serialize(uint8_t*, size_t) const`实现（定义于`src/communication/protocol.cpp`，声明于公开`protocol.hpp`），将consumer改为构造`FrameHeader`、准备8字节缓冲区并调用`header.serialize(buffer, sizeof(buffer))`。这会让链接阶段必须解析共享库中定义的函数符号，并在运行时执行一次纯内存序列化调用；不连接机器人、不发送网络数据。

- 脚本提交：`bd3f26b4a4afdfcf6dcd83b140d8e2ce2ca4ce98`。
- 随后复核发现上游`get_serialized_size()`不是constexpr，不能作为标准C++数组长度常量表达式；已改用协议明确规定的8字节固定帧头长度。
- 修正提交：`013c71fc1f9f7fc1f163bc6b10c78536cd29e565`。
- 静态合同测试提交：`e86865ac0d6c101de537866a6a1e74bbcd306a68`，要求consumer实际调用`header.serialize(buffer, sizeof(buffer))`，禁止保留空main。

### 10.3 验收边界

本次只增强了consumer测试的链接强度，不等于真实consumer已构建或运行。新提交触发的常规CI仍需检查；真实ROS Jazzy OFF/ON build/install、consumer、gtest及证据包仍为`NOT_RUN`。固定上游未修改，未创建/应用/合并上游PR，`TODO-EXT-001`未授权，A1.1保持`BLOCKED`。


## 11. 最新提交 CI #3646–#3651 最终复核

- CI #3646 / Run ID `42962553186`：SUCCESS；五个job全部成功。
- CI #3647 / Run ID `42962559047`：SUCCESS；五个job全部成功。
- CI #3648 / Run ID `42962578756`：SUCCESS；五个job全部成功。
- CI #3649 / Run ID `42962631093`：SUCCESS；五个job全部成功。
- CI #3650 / Run ID `42962639114`：SUCCESS；五个job全部成功。
- CI #3651 / Run ID `42962648302`：SUCCESS；五个job全部成功。
- 六次普通CI均包含Python 3.10/3.11/3.12、OSV和SBOM检查，所有job及失败步骤检查均无失败。
- 当前最新代码已包含consumer对`FrameHeader::serialize`非内联符号的调用及静态合同断言；上述普通CI成功验证了知识库测试代码，但没有执行专用ROS Jazzy workflow。
- 专用ROS workflow仍无运行实例；真实OFF/ON colcon build/install、consumer、gtest、证据包和SHA-256仍为`NOT_RUN`。


## 12. Install-space consumer 运行检查与 CI #3655–#3657

### 12.1 Consumer 验证强度修正

此前consumer在OFF/ON两种安装空间分别执行colcon build，能够验证编译和链接，但未实际启动生成的可执行文件。为补齐动态库装载及最小运行检查，现于每个模式的独立ROS环境中，在consumer构建成功后直接执行安装产物：

`consumer/install-<mode>/lib/staubli_install_consumer/staubli_install_consumer`

该程序调用固定上游`FrameHeader::serialize`，只执行8字节内存序列化，不连接机器人或网络。只有consumer编译、链接且程序退出码为0，脚本才会写入对应的`INSTALL_SPACE_CONSUMER_PASS`标记。

- 脚本提交：`8384fd19176a32f7aa0411da64df474979f2a0e6`。
- 新增静态合同测试提交：`a6b720c7565a15cbdcfd0402ebde6d79636d80a4`。
- CI #3655 / Run ID `42963172585`：SUCCESS，五个job全部成功。
- CI #3656 / Run ID `42963178378`：FAILURE，Python 3.10/3.11/3.12三个测试job均在Ruff Lint失败，原因是新增测试的两行断言超过100字符；其余OSV和SBOM job成功。失败日志已检查，未发现运行逻辑错误。
- 修复提交：`0f415e6ec7675954a14265971236e3d400bfc456`，将断言改为分段字符串表达式。
- CI #3657 / Run ID `42963282701`：SUCCESS，Python 3.10/3.11/3.12、OSV、SBOM五个job全部成功，无失败步骤。

### 12.2 当前验收边界

CI #3657验证的是静态合同、Ruff及知识库Python/供应链检查；**没有执行**专用ROS Jazzy容器workflow。因此OFF/ON真实colcon build/install、consumer实际运行、上游gtest、证据包及SHA-256校验仍为`NOT_RUN`。新增consumer运行步骤尚未在ROS Jazzy容器中动态执行，必须等专用workflow结果确认。

固定上游未修改；未创建/应用/合并上游PR；`TODO-EXT-001`未授权；A1.1保持`BLOCKED`。


## 13. Evidence manifest 完整性缺口修复与 CI #3661

### 13.1 发现

原 `verify_manifest()` 对manifest列出的每个文件执行路径边界、文件存在、size和SHA-256检查，但没有验证manifest是否包含全部必需证据。攻击性或误操作导致的manifest条目删除，可能让一个不完整的证据包仅凭剩余文件全部匹配而返回PASS。

### 13.2 修复

- 必需条目集合固定为：`artifacts/build-testing-off.json`、`artifacts/build-testing-on.json`、`artifacts/servo-906-validation-report.json`、`environment-fingerprint.json`。
- `commands.log`仅在调用方提供命令日志时加入，因此不列入所有包都必须具备的集合。
- manifest遗漏任一必需条目时增加MISSING检查并返回FAIL。
- 拒绝重复artifact路径，避免重复记录掩盖清单结构异常。
- 新增两项回归测试：删除manifest中的必需ON快照条目应失败；重复artifact路径应抛出验证错误。

提交：`ed5bd7d7dc3f1aee628b0f98b6bf2b74f0b3b1b4`。

### 13.3 CI结果及边界

- CI #3661 / Run ID `42964535212`：SUCCESS；Python 3.10、3.11、3.12、OSV、SBOM五个job全部成功。
- 新测试文件和打包器无超过100字符的新增行；Ruff通过。
- 该CI不运行ROS Jazzy容器，也不执行C++ build/install或consumer程序。
- 真实OFF/ON colcon build/install、consumer运行、gtest、证据包生成及SHA-256验证仍为NOT_RUN。
- 固定上游未修改；未创建/应用/合并上游PR；`TODO-EXT-001`未授权；A1.1保持BLOCKED。


## 14. Public-header dependency export coverage补强（2026-11-11）

### 14.1 固定上游静态证据

在固定commit `bd658e2d266e315d2ee35f985fb352ea88306b79` 中进一步核对：

- 已安装公共头文件 `include/staubli_robot_driver/real_time_socket_subscriber.hpp` 明确包含 `<realtime_tools/realtime_thread_safe_box.hpp>`，并在类成员中使用 `realtime_tools::RealtimeThreadSafeBox<MessageType>`。
- 该包的 `CMakeLists.txt` 将 `realtime_tools` 放入生产目标 `DEPENDENCIES`，并通过 `ament_target_dependencies()` 配置构建目标。
- 同一文件的 `ament_export_dependencies()` 清单遗漏 `realtime_tools`。
- `package.xml` 已声明 `<depend>realtime_tools</depend>`，但这不能替代CMake config对下游导出依赖的声明。

因此，realtime_tools不是仅供实现文件使用的私有依赖，而是公开安装头文件的直接依赖。此前consumer只包含`protocol.hpp`，没有覆盖这个公共头文件，不能充分验证该导出路径。

### 14.2 Consumer fixture补强

- 更新 `scripts/run_staubli_build_testing_matrix.sh` 生成的consumer `main.cpp`，新增包含 `staubli_robot_driver/real_time_socket_subscriber.hpp`；继续调用非内联 `FrameHeader::serialize`，同时覆盖共享库链接与公共头文件依赖。
- 新增静态合同测试，要求consumer fixture包含该公共头文件。
- 脚本提交：`1ff335332f37185d2d52f8cfcf7917aeca0e8eb4`。
- 测试提交：`dfd9af37452c90ef559159325abe69b7feb518d0`。

该consumer不显式`find_package(realtime_tools)`，也不手工添加其include目录，避免掩盖被测包的导出缺口。若真实ROS Jazzy install-space consumer因此无法编译，应保存完整CMake/编译日志和导出文件，归类为上游Ament依赖导出问题；不得在知识库侧修改固定上游。

### 14.3 依赖风险分级修正

- **realtime_tools：** 已有明确公共头文件依赖证据，且Ament导出清单遗漏；列为高优先级待真实consumer验证项。
- **Boost.System：** 当前仅在上游实现源/私有实现头中使用，CMake的`target_link_libraries()`未显式指定PUBLIC/INTERFACE范围；不能仅凭`ament_export_dependencies()`未列Boost就断言它必然是下游导出target缺陷。但`package.xml`未声明Boost构建依赖，仍需核实干净rosdep环境的依赖可复现性；当前workflow通过apt显式安装，不能替代包元数据正确性。
- **backward_ros：** 固定CMake中可见`find_package(backward_ros REQUIRED)`，但本次检索未发现其在已检索源文件中的公开头文件或导出target使用。暂列为构建依赖元数据待核实项，不将其直接认定为下游传递导出缺陷；`package.xml`未声明该依赖。
- **asio_SOURCE_DIR：** CMake仍使用该变量构造include路径；当前静态检索未发现变量定义来源。保留为独立构建配置待验证项，不与Ament export问题混为一谈。

### 14.4 验收边界

上述代码与静态合同测试已提交知识库`main`，但尚未取得这些提交对应的CI结果。真实ROS Jazzy OFF/ON colcon build/install、公共头文件consumer编译/运行、gtest和manifest真实证据包仍为`NOT_RUN`。本次不修改固定上游，不创建/应用/合并上游PR；`TODO-EXT-001`未授权，A1.1保持`BLOCKED`。

## 15. Boost.Asio 与未定义 asio_SOURCE_DIR 静态核查（2026-11-11）

### 15.1 源码依赖证据

固定上游 `staubli_robot_driver/src/communication/udp_socket_impl.hpp` 使用 `#include <boost/asio.hpp>`，并通过 `boost::asio`、`boost::system::error_code` 实现 UDP socket。`CMakeLists.txt` 对应执行 `find_package(Boost REQUIRED COMPONENTS system)` 并链接 `Boost::system`。本轮仓库代码搜索未发现对 standalone Asio 的 `#include <asio.hpp>` 或其他直接使用。

### 15.2 可疑 CMake include 路径

同一固定上游 `CMakeLists.txt` 却额外向生产库的 PUBLIC include directories 添加 `${asio_SOURCE_DIR}/asio/include`。对固定commit全仓搜索仅找到这一处引用；未找到 `FetchContent_Declare(asio)`、`find_package(asio)` 或其他变量赋值。当前知识库workflow也未向CMake传入 `asio_SOURCE_DIR`。因此在当前执行入口下，该变量没有已知定义来源，空变量展开后形成 `/asio/include` 这一可疑PUBLIC include路径。

这项静态证据说明该路径与实际 `Boost.Asio` include 不一致，且 standalone Asio 的系统包并非当前源码已证实的直接依赖；但在真实ROS Jazzy CMake configure/build前，不把它夸大为已复现的编译阻断。它可能只是无效/遗留的PUBLIC include目录，也可能在导出的INTERFACE_INCLUDE_DIRECTORIES中污染下游consumer。真实影响须由OFF/ON build快照和install-space consumer结果确定。

### 15.3 知识库侧构建环境清理

- 从专用workflow移除未被固定上游源码使用的 `libasio-dev` 安装项。
- 从构建矩阵脚本移除对 `libasio-dev` 和 `/usr/include/asio.hpp` 的强制检查；保留 `libboost-system-dev` 检查，因为源码明确使用 Boost.Asio 且CMake要求 Boost.System。
- 新增静态合同测试，确保workflow不再把 standalone Asio 当作必需依赖，同时保留 Boost.System。
- 以上只清理知识库构建入口，不修改固定上游CMake，也不擅自改写上游package.xml。

### 15.4 其他依赖元数据

`package.xml`未声明 `Boost` 和 `backward_ros`，但CMake分别执行 `find_package(Boost REQUIRED COMPONENTS system)` 与 `find_package(backward_ros REQUIRED)`。当前workflow显式安装对应系统/ROS包，因而可能使CI环境掩盖上游manifest依赖缺口。源码检索确认Boost.Asio用于私有实现头；backward_ros当前仍只有CMake查找证据，未证实其需要导出给下游。两项均保留为上游构建依赖元数据待核实，不擅自推定其rosdep key或修改上游。

### 15.5 当前验收边界

本次只调整知识库workflow/script/test，并增加静态审计证据。新提交对应普通CI尚待复验；真实ROS Jazzy OFF/ON build/install、PUBLIC include path导出内容、consumer编译/运行、gtest和SHA-256 evidence仍为`NOT_RUN`。固定上游commit不变；无上游PR；`TODO-EXT-001`未授权；A1.1保持`BLOCKED`。


## 16. 安装导出 include 路径的动态证据采集（2026-11-11）

- CMake File API collector现从安装空间的`*Targets.cmake` / `*Export.cmake`中提取`INTERFACE_INCLUDE_DIRECTORIES`，写入OFF/ON快照字段`exported_target_include_directories`。
- target graph validator新增OFF/ON检查：拒绝精确的`/asio/include`空变量展开路径，以及仍未展开的`${asio_SOURCE_DIR}`。不因任意合法目录名含`asio/include`而误报。
- 该机制让真实ROS Jazzy install export能直接验证上游PUBLIC include路径是否污染下游包；仍需手动运行专用workflow取得实际快照，静态测试不等于动态验收。


实现提交：collector`71e59c4`、`5648092`；validator`0d5fa7f`、`d0d03d6`；静态合同测试`44f1564`、`2a21c4c`。尚未取得这些提交的CI结果，动态ROS Jazzy矩阵仍未执行。


## 17. 安装导出采集器行为测试与快照证据强制性（2026-11-11）

### 17.1 实现复核与补强

- 将安装导出 include 路径扫描提取为可单独调用的`collect_exported_target_include_directories()`，扫描安装前缀下`lib/cmake`与`share`中的`*Targets.cmake`、`*Export.cmake`，读取`INTERFACE_INCLUDE_DIRECTORIES`并拆分分号列表。
- 新增行为回归测试：在临时安装前缀中构造真实格式的`INTERFACE_INCLUDE_DIRECTORIES`属性，断言collector能同时提取`${_IMPORT_PREFIX}/include`和`/asio/include`。这比仅断言源文件包含某些字符串更直接地覆盖路径提取行为。
- 修正validator的证据缺口：此前`exported_target_include_directories`字段缺失时默认空数组，会使旧快照绕过新增检查。现要求OFF/ON快照必须显式包含该字段；缺失时中止验证并提示重新采集，不能静默判定PASS。
- 静态合同测试增加断言，确保缺失字段不会被默认空数组放行。
- collector helper提交：`84549734e255f6b640565d8e1fe282e8943fafe0`；行为测试提交：`14ed24307d634c09ddd6ab5d880eaab4e32a4beb`；测试格式/换行修正：`9dcfddedd394b4deaf06d80c836ea483b07e87be`、`196e32a2ba7f858b3bbf2818d4ec7c65f0159a84`；validator要求字段提交：`dec8e76fe389ab277325f6c5d5abb6b4054777c8`；静态测试提交：`f4785e9462f87ee54b38107fcd7ceae95182e18a`。

### 17.2 依赖元数据补充核查

- 固定上游`udp_socket_impl.hpp`检索到`<boost/asio.hpp>`及`boost::asio`使用；检索范围内没有找到`backward::`、`Backward::`、`backward.hpp`或`backward_ros::`源码引用。
- 固定上游`CMakeLists.txt`仍执行`find_package(backward_ros REQUIRED)`，但没有证据表明其被链接到生产目标或被公开头文件使用。故当前仅列为未解释的CMake构建依赖查找，不升级为下游传递依赖缺陷。
- Boost依赖通过实现私有头`udp_socket_impl.hpp`使用，当前证据不支持将Boost头路径认定为公共API依赖；但`package.xml`未声明Boost和backward_ros，而workflow显式安装会掩盖manifest可复现性问题。仍需在干净rosdep/colcon环境中验证，且不猜测rosdep key、不修改固定上游。

### 17.3 验收边界

- 本轮代码/静态测试提交基线为`f4785e9462f87ee54b38107fcd7ceae95182e18a`；随后审计报告、根TaskPlan和第21章TaskPlan同步提交分别为`fb15cfe18477cc98a381a7afc4d33787869972f4`、`45339859829eb463fe0bd2868ec8e706decd4fb6`、`42885783138d511d25118dc52d08982a0554ea37`。代码基线的combined status为空，PR触发workflow查询也为空；这两项均不能证明push workflow成功或未运行，故普通CI结果仍标记为待确认。
- 本轮只检查并提交静态代码/测试；没有在本地执行pytest、Ruff或shellcheck，也没有执行ROS Jazzy容器构建。真实OFF/ON colcon build/install、安装空间consumer编译与运行、gtest、证据包及SHA-256仍为`NOT_RUN`。
- 固定上游commit不变；未创建/应用/合并上游PR；`TODO-EXT-001`未授权；A1.1保持`BLOCKED`。


## 18. CI #3686–#3698 失败根因、修复与复验（2026-11-11）

### 18.1 失败范围与根因

- GitHub Actions push run #3686–#3696（11次连续运行）均以失败结束；失败集中在Python测试矩阵，并非所有job都失败。OSV审计与SBOM作业在最新失败run #3696均成功。
- 早期失败日志显示Ruff F821：collect()调用collect_exported_target_include_directories()，但该函数在当时提交中尚未定义，属于重构提交顺序/函数定义遗漏。
- helper补入后，测试矩阵仍失败：一项静态测试仍要求asio_SOURCE_DIR字面量出现在collector源文件中，但该判断职责已位于validator；另有8项target graph测试快照fixture未提供新增必需字段exported_target_include_directories，validator按设计拒绝旧fixture。
- 最新失败run #3696的lint成功，测试为9 failed / 114 passed；Python 3.10/3.11/3.12均在同一测试集合失败。这些失败不是OSV漏洞、SBOM上传、Python安装或依赖解析故障。

### 18.2 修复内容

- collector合同测试改为检查collect_exported_target_include_directories(prefix)被调用，不再要求实现源文件出现asio_SOURCE_DIR字面量；未解析路径判定由validator负责。
- target graph测试snapshot fixture统一加入exported_target_include_directories字段，默认空列表；增加两项回归测试：/asio/include必须失败，缺失证据字段必须拒绝。
- 早期helper未定义问题已由独立函数定义提交修复；本轮最终修复提交：静态合同测试2f7601e68951f1be5c6b0922de32cb5841abc91a，target graph fixtures与回归测试a04999e1d398e732262a0dd6d83603e0d075fa40。

### 18.3 CI复验结果

- 最终提交触发push run #3698（Run ID 42968264032），结论SUCCESS。OSV审计、SBOM及Python 3.10/3.11/3.12三个测试job全部成功。
- 三个Python版本均报告Ruff All checks passed!，pytest均为125 passed（3.10：0.92s；3.11：1.38s；3.12：1.00s）。
- 前一提交#3697（仅调整collector合同测试）仍失败，因为target graph fixture尚未同步；随后#3698在完整修复提交上通过。历史失败run保留，不重写为成功。

### 18.4 后续验收边界

- 普通CI现已在a04999e1d398e732262a0dd6d83603e0d075fa40通过；该结果只证明Python lint/tests、OSV与SBOM jobs，不代表ROS Jazzy/C++构建通过。
- ROS Jazzy OFF/ON colcon build/install、安装空间consumer编译与运行、gtest、证据包SHA-256仍为NOT_RUN。专用workflow仍需真实workflow_dispatch运行。
- 固定上游commit保持bd658e2d266e315d2ee35f985fb352ea88306b79；未创建/应用/合并上游PR；TODO-EXT-001未授权；A1.1保持BLOCKED。


## 19. colcon isolated install 导出扫描覆盖修复（2026-11-11）

- 对专用矩阵脚本进行静态执行路径审查，确认collector的export_root传入colcon install-base。colcon默认isolated install时，包导出文件通常位于install-base/<package>/share/<package>/cmake，而此前collector仅扫描install-base/share与install-base/lib/cmake，存在漏采集风险。
- 新增find_export_files()统一扫描merged install根目录和isolated install下一级包前缀；collector的target name扫描与INTERFACE_INCLUDE_DIRECTORIES扫描共用该文件发现函数，避免两条扫描路径布局行为不一致。
- 新增行为测试，模拟install-base/staubli_robot_driver/share/staubli_robot_driver/cmake/staubli_robot_driverExport.cmake，确认isolated布局可发现导出文件并提取include目录。
- 实现提交6bf1fa5146b7ceb32aead67b2706608637fde11b；行为测试提交99242ab4fa9d8a6c68f9734c3d36a3aa5a03b60f。
- CI #3702（Run ID 42968762503）在实现提交上SUCCESS；CI #3703（Run ID 42968810375）在行为测试提交上SUCCESS，Python 3.10/3.11/3.12、OSV、SBOM全部成功；三个版本Ruff均通过，pytest均为126 passed。
- 这修复了静态确认的采集器布局覆盖缺口，但不是ROS Jazzy真实构建结果。仍需手动触发专用workflow确认真实install tree、导出文件、consumer与gtest；当前workflow_dispatch运行数为0。固定上游commit不变，未创建/应用/合并上游PR；TODO-EXT-001未授权；A1.1保持BLOCKED。


## 20. CI #3704–#3706复验与下一阶段阻塞项（2026-11-11）

### 20.1 普通CI最终状态

- 当前main HEAD（本节更新前）：`843e18595dacdc77527b87004ea88b443c9ec651`。
- CI #3704 / Run ID `42968933020`（审计报告提交）：SUCCESS。
- CI #3705 / Run ID `42968943114`（第21章TaskPlan提交）：SUCCESS。
- CI #3706 / Run ID `42968965060`（根TaskPlan提交）：SUCCESS。
- #3706五个job全部完成且成功：Python 3.10、3.11、3.12测试，OSV依赖审计，SBOM生成。此结果确认普通CI无遗留失败；不代表ROS Jazzy/C++构建成功。

### 20.2 专用workflow与上游风险状态

- 再次查询Actions最近100条运行记录，未发现Stäubli ROS Jazzy专用workflow的`workflow_dispatch`运行。
- 当前静态复核确认固定上游公共头文件`real_time_socket_subscriber.hpp`包含`realtime_tools/realtime_thread_safe_box.hpp`，而`ament_export_dependencies()`遗漏`realtime_tools`。这仍是高优先级真实consumer验证风险，不是已复现的动态失败。
- 固定上游README说明该驱动面向ROS 2 Jazzy/Ubuntu 24.04及CS9控制器，但项目仍处于prototype状态，且README称自2025年11月POC后开发暂停。故即使CI通过，也不能将其描述为工业级或量产就绪驱动。来源：上游项目README（https://github.com/ICube-Robotics/staubli_driver_ros2）。

### 20.3 真实验收仍未执行

以下项目全部保持`NOT_RUN`：
- ROS Jazzy固定镜像中的`BUILD_TESTING=OFF/ON`真实colcon build/install；
- OFF/ON两套install-space consumer编译、链接和运行；
- 上游gtest及测试结果；
- 安装导出target/include快照、validator报告；
- evidence manifest生成及SHA-256验证。

下一步仍是由具备仓库write权限的用户在Actions页面手动触发专用workflow；取得真实日志和artifact后，优先判断`realtime_tools`公共头文件依赖导出是否阻断consumer，再决定是否提交知识库侧修正或形成上游修复建议。

固定上游commit保持`bd658e2d266e315d2ee35f985fb352ea88306b79`；未修改上游、未创建/应用/合并上游PR；`TODO-EXT-001`未授权；A1.1保持`BLOCKED`。
