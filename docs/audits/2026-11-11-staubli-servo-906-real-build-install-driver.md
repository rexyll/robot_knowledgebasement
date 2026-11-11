# Stäubli SERVO-906：ROS Jazzy 双配置真实 build/install 驱动

- 日期：2026-11-11
- 仓库：rexyll/robot_knowledgebasement
- 固定上游：ICube-Robotics/staubli_driver_ros2@bd658e2d266e315d2ee35f985fb352ea88306b79
- 范围：知识库侧可复现驱动脚本、安装空间 consumer smoke test、静态安全测试
- 未修改固定上游；本节点未在 ROS Jazzy 容器中实际执行构建。

## 1. 依赖闭包复核

固定上游 `.docker/Dockerfile` 使用 `osrf/ros:jazzy-desktop-full`，执行 `rosdep install --from-paths src --ignore-src -r -y`，然后在整个工作区执行 `colcon build`。本节点以此作为真实工作区构建入口依据，不把目标包根目录直接交给 CMake。

`staubli_robot_driver/CMakeLists.txt` 还显式使用：
- `find_package(backward_ros REQUIRED)`
- `find_package(Boost REQUIRED COMPONENTS system)`
- `${asio_SOURCE_DIR}/asio/include` include 路径

但对应 `package.xml` 没有声明 backward_ros、Boost 或 standalone Asio 依赖。新脚本在 rosdep check 之外显式检查 backward_ros 可发现性、`libboost-system-dev`、`libasio-dev` 和 `/usr/include/asio.hpp`。这避免把 package.xml 的 rosdep 结果误认为完整 CMake 依赖闭包。上游的 `asio_SOURCE_DIR` 仍未在固定 commit 的包 CMake 中定义；系统 include 检查只验证 standalone Asio header 存在，不宣称该 CMake 变量已修复。

## 2. 驱动脚本变更

更新 `scripts/run_staubli_build_testing_matrix.sh`：
- 要求 ROS_DISTRO=jazzy、ROS setup 存在、固定上游 commit 精确匹配且工作树 clean；
- 对 BUILD_TESTING=OFF/ON 使用独立 build/install/log 根目录；
- 预先建立 CMake File API codemodel-v2 query；
- 使用 colcon 对固定上游工作区执行 build/install，而非仅 cmake configure；
- 要求目标包 install_manifest.txt 非空及 install/setup.bash 存在；
- 从每个安装前缀采集真实 ament export target 文件；
- 生成独立下游 ament consumer 并在 OFF/ON 安装空间分别构建；
- ON 配置额外执行目标包 colcon test 和 test-result；
- 改为调用 SERVO-905 的 `validate_staubli_upstream_target_graph.py`，不再调用 Fake Harness validator；
- 通过 SERVO-903 evidence packager 生成并验证 SHA-256 manifest，包含环境指纹、双配置快照、validator报告和完整命令日志。

## 3. 测试与验收边界

新增 `tests/test_staubli_ros_jazzy_build_script.py`，对脚本关键合同进行静态回归检查：固定commit/clean checkout、Jazzy guard、colcon build/install、正确validator、双配置 consumer、test-result。

这些测试只证明脚本合同未被意外删改，不证明 ROS 构建成功。实际执行需要具备 ROS Jazzy、colcon、rosdep、backward_ros、Boost.System 和 standalone Asio 的 Ubuntu 24.04 环境。

| 项目 | 状态 |
|---|---|
| 上游 Dockerfile 构建入口核对 | STATIC_REVIEWED |
| CMake/package.xml依赖差异 | FINDINGS_RECORDED |
| 双配置 colcon build/install 驱动 | IMPLEMENTED_NOT_EXECUTED |
| CMake File API 双配置采集 | IMPLEMENTED_NOT_EXECUTED |
| 固定上游 target graph validator 接线 | IMPLEMENTED_NOT_EXECUTED |
| 双配置 install-space consumer | IMPLEMENTED_NOT_EXECUTED |
| BUILD_TESTING=ON colcon test | IMPLEMENTED_NOT_EXECUTED |
| 证据包 SHA-256 package/verify | IMPLEMENTED_NOT_EXECUTED |
| ROS Jazzy真实build/install/gtest/consumer | NOT_RUN |
| plugin load/unload、ABI、TSan/ASan、HIL | NOT_RUN |

**结论：** 真实构建/安装驱动已在知识库侧实现，但当前环境未执行 ROS Jazzy 构建，因此不得标记为构建 PASS。固定上游 CMake/package.xml 的依赖声明缺口未被本仓库擅自修补；下一节点应在固定 digest 的 ROS Jazzy 环境运行脚本，处理真实构建暴露的问题后再接入手动 workflow。

## 4. 安全边界

仅修改知识库 main；不修改、分叉写回或提交固定上游；不创建/应用/合并上游 PR。TODO-EXT-001 未授权，A1.1 保持 BLOCKED。脚本要求固定 commit 与 clean checkout，拒绝对来源不明或被修改的上游源码生成证据。
