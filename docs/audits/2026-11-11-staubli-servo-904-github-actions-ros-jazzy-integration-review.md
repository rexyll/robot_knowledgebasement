# Stäubli SERVO-904：GitHub Actions 与 ROS Jazzy 双配置证据接入审查

- 节点：§9.3.321 / SERVO-904
- 日期：2026-11-11
- 仓库：rexyll/robot_knowledgebasement，main
- 固定上游：ICube-Robotics/staubli_driver_ros2@bd658e2d266e315d2ee35f985fb352ea88306b79
- 审查类型：静态 workflow、采集脚本、固定上游 CMake/package 元数据审查
- 本节点未修改固定上游；未执行真实 ROS Jazzy configure/build/install/consumer/plugin/HIL。

## 1. 当前 CI 实际覆盖

审查 `.github/workflows/ci.yml`（当前 blob `904abdafbaad0991030b45d93d4cad198ec4aeef`）确认只有：
- Python 3.10/3.11/3.12 矩阵：锁定安装、知识库 validator、Ruff、pytest、固定 rustypot 源码 SHA 校验；
- Python runtime/development/build/generator SBOM；
- Python 锁定依赖 OSV 扫描。

CI #3560（Run ID 42951823527）及 #3561（Run ID 42952280106）成功，但二者均不执行 ROS Jazzy 容器、colcon、上游 CMake 配置或 C++ 编译。不能将这两个运行作为 Stäubli 上游构建验收。

## 2. 固定上游结构与 CMake/package 静态发现

固定 commit 的仓库树没有根级 CMakeLists.txt；ROS 包分布在 staubli_driver_ros2、staubli_robot_driver、staubli_robot_description、staubli_bringup、staubli_moveit_config 等子目录。目标 C++ driver 包应使用：
`staubli_robot_driver/CMakeLists.txt`，而不是仓库根目录作为 `cmake -S` 输入。

静态核对 `staubli_robot_driver/CMakeLists.txt` 与 `package.xml`：
- CMake 显式 `find_package(backward_ros REQUIRED)`、`find_package(Boost REQUIRED COMPONENTS system)`，但该包 package.xml 未声明对应的 build dependency；仅依赖 rosdep 从 package.xml 自动安装时，不能证明这些依赖已安装。
- CMake 将 `${asio_SOURCE_DIR}/asio/include` 添加为 include 路径，但在已检查的包 CMakeLists.txt 中未看到定义 `asio_SOURCE_DIR` 或声明/获取 Asio 源码的逻辑。其解析结果和依赖来源必须在真实环境中核实，不能假设系统路径自动满足。
- BUILD_TESTING=ON 时还需 `ament_cmake_gtest`；package.xml 声明 test dependency，但 CI 需确保 rosdep 已安装。
- `staubli_robot_driver` 的 CMake 配置还依赖 rclcpp、std_msgs、sensor_msgs、geometry_msgs、control_msgs、realtime_tools、hardware_interface、pluginlib、rclcpp_lifecycle、ament_cmake 等 ROS 包。

这些是固定上游的依赖声明/构建环境风险记录，不在本仓库代替上游修补。

## 3. 现有 SERVO-902/903 工具与接入缺口

- `scripts/run_staubli_build_testing_matrix.sh` 直接执行 `cmake -S "${SOURCE_DIR}" -B ...`，因此 SOURCE_DIR 必须是包含 CMakeLists.txt 的具体 ROS package 路径，而不是上游仓库根目录。
- 脚本只执行 configure 和 codemodel-v2 snapshot 收集；不执行 build 或 install。
- collector 可读取 build 目录中的 `install_manifest.txt`，但该文件通常由 install 阶段产生。未执行 install 时，空 install_entries 不能证明没有安装文件。
- SERVO-903 的 `--export-root` 仅扫描指定安装前缀下的已安装 Targets.cmake；当前双配置脚本没有建立安装前缀，也没有执行 install，因此无法单靠现有脚本获得真实导出 target 证据。
- 现有 collector 的 codemodel 快照与 validator 可以用于目标图静态门禁，但不能替代 C++ 编译、gtest、下游 install-space consumer 或 plugin load/unload。

## 4. 最小 CI 接入方案（设计，不表示已执行）

建议将真实 ROS 验证作为独立的手动触发 workflow（workflow_dispatch），与快速 Python CI 分离，避免每次文档提交都承担 ROS 环境安装成本。环境和命令必须显式固定并归档：

1. 使用 ROS 2 Jazzy / Ubuntu 24.04 环境；镜像需固定 digest，记录 OS、架构、ROS_DISTRO、CMake、编译器、colcon 版本。
2. checkout 知识库 main；clone 固定上游 commit `bd658e2d266e315d2ee35f985fb352ea88306b79`，校验 HEAD 完全匹配且工作树 clean。
3. 从上游 package.xml 执行 rosdep 安装；对 CMake 中未声明的 backward_ros/Boost 以及 asio_SOURCE_DIR 来源进行显式依赖闭包核验。未解决 Asio 来源前，不应宣称配置环境可复现。
4. 对目标包分别建立 BUILD_TESTING=OFF/ON 的独立 build/install/log 目录；在 configure 前预置 CMake File API codemodel-v2 query。通过 colcon/CMake 正式 build 与 install，不能只 configure。
5. 分别收集 OFF/ON codemodel、install manifest、安装前缀中的 imported export target 来源；运行 SERVO-901 validator。
6. 执行 install-space consumer 验证；对 BUILD_TESTING=OFF/ON 均保存真实命令、退出码、stdout/stderr、环境指纹、commit/dirty 状态。
7. 调用 SERVO-903 evidence package/verify，生成 SHA-256 manifest；以 GitHub Actions artifact 归档。缺失任何必需步骤或产物时 fail closed。
8. 将 C++ header self-containment、gtest、plugin load/unload、ABI、TSan/ASan 分别作为独立证据项；未执行的项目必须标记 NOT_RUN，不得以 configure 成功代替。

## 5. 决策与验收状态

| 项目 | 状态 |
|---|---|
| 现有 Python CI 覆盖范围确认 | STATIC_REVIEWED |
| 固定上游目标 package 路径确认 | STATIC_REVIEWED |
| package.xml 与 CMake 依赖闭包差异 | FINDINGS_RECORDED |
| SERVO-902 仅 configure、不 build/install 的缺口 | FINDINGS_RECORDED |
| 真实 ROS Jazzy workflow | NOT_IMPLEMENTED |
| 固定镜像 digest 与依赖闭包 | NOT_RESOLVED |
| BUILD_TESTING OFF/ON 真实 build/install | NOT_RUN |
| install-space consumer | NOT_RUN |
| C++/gtest/plugin/ABI/TSan/ASan/HIL | NOT_RUN |

**结论：** 目前不应把 SERVO-902 的 configure-only 脚本直接包装成“真实构建 CI”。最小可靠接入必须先解决上游依赖闭包与 Asio 来源，改为双配置 build/install，再采集 File API 和导出目标证据。为避免产生虚假 PASS，本节点只完成静态审查和接入设计，不新增一个会将不完整 configure 结果误报为构建通过的 workflow。

## 6. 安全与范围边界

固定上游未修改、未创建/应用/合并上游 PR。TODO-EXT-001 未授权，A1.1 继续 BLOCKED。RACE-01–16、EXEC-01–04、C++/ROS/plugin/ABI/sanitizer/HIL 均未执行。当前 Python CI 成功仅表示知识库工具及供应链检查通过。

下一节点：§9.3.322 / SERVO-905，解析固定上游依赖闭包并设计可复现 ROS Jazzy build/install 驱动脚本；在依赖来源明确前，不启用会给出误导性成功结论的真实构建门禁。
