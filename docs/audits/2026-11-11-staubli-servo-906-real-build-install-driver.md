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

## 5. SERVO-906 后续静态复核（2026-11-11）

- **证据包命名修正：** `scripts/package_staubli_build_evidence.py` 原先将本节点validator报告归档为 `servo-901-validation-report.json`，已修正为 `servo-906-validation-report.json`；新增回归测试防止编号漂移。提交：`d8478f6`、`8d63b0d`。
- **下游依赖导出风险：** 固定上游 `CMakeLists.txt` 将 `Boost::system` 链接到 `staubli_robot_driver`，但 `ament_export_dependencies()` 未导出 Boost。ROS 2 ament 官方文档说明该宏用于向下游导出依赖，使consumer无需自行再次find_package。该缺口因此列为待真实验证的install-space集成风险；当前consumer未主动find_package(Boost)，不会用测试配置掩盖上游导出问题。依据：[ROS 2 ament CMake documentation](https://github.com/ros2/ros2_documentation/blob/rolling/source/Developer-Tools/Build/Ament-CMake-Documentation.rst)。
- **不可夸大的结论：** 该静态证据不能单独证明consumer必然失败；必须由固定digest ROS Jazzy workflow的实际consumer build确定。未修改固定上游。
- **CI复验：** CI #3620 / Run ID `42958035088` 与 CI #3621 / Run ID `42958041757` 均SUCCESS；Python 3.10/3.11/3.12、OSV、SBOM全部成功。仅验证知识库Python/静态测试，不代表ROS/C++ build/install/gtest/consumer通过。
- **当前状态：** SERVO-906 `IMPLEMENTED_NOT_EXECUTED`；SERVO-907仍未发现独立workflow run；真实ROS Jazzy验收继续 `NOT_RUN`。


## 6. 专用 workflow Run #5/#6：安装导出缺陷动态证据（2026-11-11）

### Run #5

- Run ID：`43027974929`；提交：`5102e31ca2c51a5875b108efceb3287f2f02ce07`；结果：`failure`。
- 固定上游 checkout、ROS Jazzy依赖准备、BUILD_TESTING=OFF构建与安装均推进成功；失败出现在独立 install-space consumer。
- CMake报告导入target `staubli_robot_driver::staubli_robot_driver` 的链接接口引用 `Boost::system`，但该target未定义；同时导出include路径包含不存在的 `/asio/include`。
- 两项错误分别对应固定上游缺少Boost下游依赖导出，以及将未定义的 `asio_SOURCE_DIR` 展开为错误绝对路径。该consumer未预先调用 `find_package(Boost)`，因此Run #5保留了Boost导出缺陷的直接动态证据。

### Run #6

- Run ID：`43031245835`；提交：`0fc60dfd911837bbe9e544676f0a4df3671c345e`；结果：`failure`。
- ROS Jazzy容器、固定上游checkout、rosdep、BUILD_TESTING=OFF/ON构建与安装、CMake File API快照均已推进；两个模式的consumer均在CMake生成阶段因导入target包含不存在的 `/asio/include` 而失败。
- target-graph validator在OFF/ON快照中均检测到 `/asio/include`，对应检查 `EXPORT-EXCLUDES-UNRESOLVED-ASIO-INCLUDE-OFF/ON` 均FAIL。证据工件已上传：`13860064639`。
- 对Run #6脚本进行复核时发现consumer夹具增加了 `find_package(Boost REQUIRED COMPONENTS system)`。这会预先创建 `Boost::system`，从而掩盖Run #5已实际暴露的上游Boost依赖导出缺陷；该测试夹具改动方向错误，不能保留。

### 知识库侧纠正

- 提交 `1f698152ebfa41ef82f2efe7389cdb33e26ec851`：移除consumer中的预先 `find_package(Boost)`，让独立消费者直接加载上游安装包，不再人为补齐上游未导出的Boost target。
- 提交 `ad6220b6e6f5cf89e1bbcba31f532928f7ef6349`：新增回归测试，明确禁止consumer夹具预先定义 `Boost::system` 或调用 `find_package(Boost)`。
- 两个提交触发的普通CI Run `43032513964`、`43032558011`在本记录写入时仍未完成，结果待逐Job复核；不得提前标记PASS。
- 固定上游 `ICube-Robotics/staubli_driver_ros2@bd658e2d266e315d2ee35f985fb352ea88306b79`保持只读。本仓库不通过创建空目录、伪造include目录、改写已安装导出文件或consumer手工补依赖来绕过缺陷。

### 当前结论与下一步

- **已由真实ROS Jazzy运行确认的上游安装导出缺陷：**
  1. `asio_SOURCE_DIR`未定义，导致导出接口包含无效路径 `/asio/include`，OFF/ON均失败。
  2. `Boost::system`出现在生产库的导出链接接口，但上游没有通过 `ament_export_dependencies(Boost)` 或等效配置确保下游target存在；Run #5的consumer直接失败，Run #6曾被测试夹具预先find_package掩盖，现已撤销该掩盖。
- 不能通过只改consumer夹具让该包通过。若要使上游安装包真正可消费，需要上游修复CMake依赖/导出合同；但本项目明确禁止修改固定上游或未经授权创建上游PR。
- SERVO-906与SERVO-907继续BLOCKED；完整gtest七项报告、consumer编译链接运行、manifest/SHA-256动态验收均未通过。A1.1保持BLOCKED；`TODO-EXT-001`未授权。


## 7. Consumer夹具回归测试修复与普通CI闭环

- 移除Boost预查找后，普通CI先后暴露了测试合同未同步（Run `43032513964`）以及断言错误地扫描注释文本（Run `43032558011`、`43032661039`、`43032712680`、`43032785783`）。上述失败均为Python静态测试断言问题，不是ROS Jazzy构建失败；SBOM/OSV jobs均成功。
- 首轮测试仍断言旧的 `find_package(Boost)` 存在；更新后测试又因脚本注释中出现 `Boost::system` 字样而误判。已将断言收窄为只检查consumer CMake命令行是否执行 `find_package(Boost...)`，不扫描注释。
- 最终测试修复提交：`962b4194d832c281b019aa164ca9d86e90e23cd1`。
- 普通CI Run `43032966478`（该提交）completed/success；Python 3.10/3.11/3.12测试、Lint、Stäubli lifecycle/test-catalog/runtime evidence静态验证、SBOM、OSV五个Job及全部步骤均SUCCESS。
- 结论边界：普通CI回归已闭环；它不改变Run #5/#6的真实ROS Jazzy失败结论。consumer已不再预先定义Boost target，后续专项运行将重新暴露上游Boost导出缺口；无效 `/asio/include` 仍是确定性阻塞项。
