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
