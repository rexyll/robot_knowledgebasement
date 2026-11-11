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
