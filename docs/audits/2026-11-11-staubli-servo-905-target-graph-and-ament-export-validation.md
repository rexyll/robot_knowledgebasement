# Stäubli SERVO-905：固定上游 Target Graph 与 Ament Export 采集校正

- 节点：§9.3.322 / SERVO-905（进行中）
- 日期：2026-11-11
- 仓库：rexyll/robot_knowledgebasement，main
- 固定上游：ICube-Robotics/staubli_driver_ros2@bd658e2d266e315d2ee35f985fb352ea88306b79
- 范围：知识库侧CMake File API采集器与静态target graph validator；不修改固定上游源码。

## 1. 本节点发现

### 1.1 Ament export 文件名与 collector glob 不匹配

ROS 2 Jazzy 的 `ament_export_targets()` package hook 通过 `install(EXPORT ... FILE "${_target}Export.cmake")` 安装导出文件，默认位于 `share/<package>/cmake/`。官方实现：
- [ament_export_targets.cmake](https://github.com/ament/ament_cmake/blob/jazzy/ament_cmake_export_targets/cmake/ament_export_targets.cmake)
- [ament_cmake_export_targets_package_hook.cmake](https://github.com/ament/ament_cmake/blob/jazzy/ament_cmake_export_targets/cmake/ament_cmake_export_targets_package_hook.cmake)

SERVO-903 collector原先只搜索 `*Targets.cmake`，因此不能发现典型的 `export_staubli_robot_driverExport.cmake`，会漏采 Ament imported targets。

**修复：** `scripts/collect_staubli_cmake_file_api.py` 的受限扫描现在同时搜索 `*Targets.cmake` 与 `*Export.cmake`，仍限定在指定前缀下的 `lib/cmake` 与 `share/**/cmake`，并保持路径越界防护和来源文件记录。新增 `tests/test_staubli_cmake_file_api.py::test_export_root_scans_ament_export_targets_file` 合成fixture。

### 1.2 SERVO-901 validator 默认目标名与固定上游不匹配

固定上游 `staubli_robot_driver/CMakeLists.txt` 实际目标：
- 生产库：`staubli_robot_driver`、`staubli_robot_driver_hardware_interface`
- BUILD_TESTING gtest：`test_primitives_serialization`、`test_message_serialization`、`test_sockets`、`test_rt_socket_interface`、`test_robot_driver`、`test_mock_robot_server`、`test_staubli_hardware_interface`
- 始终定义并安装的诊断程序：`test_receive_robot_state`
- pluginlib 导出对应硬件接口库：`staubli_robot_driver_hardware_interface`

SERVO-901 Fake harness validator默认使用 `staubli_socket_core`、`staubli_driver_plugin`、`staubli_socket_test_support`、`staubli_socket_unit_tests`，属于未来架构合同，不能直接用于当前固定上游。

**修复：** 新增 `scripts/validate_staubli_upstream_target_graph.py`，专门按固定上游实际target命名校验OFF/ON双配置：
- 两个生产库在OFF/ON均存在；
- 七个gtest目标在OFF不存在、ON存在；
- 生产依赖闭包和plugin闭包不依赖gtest/fake目标；
- OFF/ON安装清单均不安装gtest目标；
- Ament export集合包含两个生产库且不导出gtest目标；
- 明确校验 `test_receive_robot_state` 在两种配置下存在并安装，避免把这个历史诊断程序误判为gtest泄漏。

新增 `tests/test_staubli_upstream_target_graph.py`，覆盖正向矩阵、OFF/ON目标缺失/泄漏、生产闭包泄漏、安装/导出泄漏、诊断程序安装和配置标记错误。

## 2. CI 失败与修复

新增fixture和validator后，CI #3574–#3577曾因Ruff E501阻断，原因是测试fixture字符串与validator限制说明超过100字符；这些失败是本轮知识库新增代码引入的Lint回归，不是上游ROS构建失败。

- `0a7359c`：拆分测试fixture长字符串。
- `f00c383`：拆分validator限制说明长字符串。
- [CI #3578](https://github.com/rexyll/robot_knowledgebasement/actions/runs/42954198499)：SUCCESS。
- [CI #3579](https://github.com/rexyll/robot_knowledgebasement/actions/runs/42954266515)：SUCCESS。

历史失败run不改写；#3574–#3577已追加至逐条CSV索引。

## 3. 上游依赖元数据静态检查

- `staubli_robot_driver/CMakeLists.txt` 显式 `find_package(backward_ros REQUIRED)` 和 `find_package(Boost REQUIRED COMPONENTS system)`；该包 `package.xml` 未直接声明对应依赖。真实ROS环境应核对依赖是否由系统包/其他包间接提供，并在可复现环境中显式确认，不能只假定rosdep一定覆盖。
- `asio_SOURCE_DIR` 在固定上游CMakeLists中只有一处引用；源码实际包含 `<boost/asio.hpp>`，未发现 `find_package(asio)` 或 `FetchContent` 定义。该变量更像遗留的无效build-interface include路径，而非已证实的独立Asio源码依赖。固定上游未获授权修改；真实configure需记录其展开/诊断情况。
- BUILD_TESTING=ON使用 `ament_cmake_gtest`，package.xml声明了test dependency；rosdep安装仍需纳入test dependencies。

## 4. 状态与边界

| 项目 | 状态 |
|---|---|
| Ament `*Export.cmake` 发现修复 | IMPLEMENTED |
| Ament export合成fixture | IMPLEMENTED；CI #3578通过 |
| 固定上游实际target graph validator | IMPLEMENTED；CI #3578通过 |
| validator正/负向合成测试 | IMPLEMENTED；CI #3578通过 |
| 固定上游真实CMake File API快照 | NOT_RUN |
| BUILD_TESTING OFF/ON真实build/install | NOT_RUN |
| install-space consumer | NOT_RUN |
| C++/gtest运行、plugin load/unload、ABI、TSan/ASan/HIL | NOT_RUN |

本节点仅完成知识库侧采集器修复与validator实现。没有真实上游ROS Jazzy构建证据；合成fixture通过不能被标记为真实target graph PASS。固定上游未修改、未创建/应用/合并上游PR；TODO-EXT-001未授权，A1.1保持BLOCKED。

下一步：SERVO-906，核对ROS Jazzy环境依赖闭包和目标包构建入口，扩展双配置脚本为真正的build/install采集流程，再决定是否接入独立手动触发workflow。
