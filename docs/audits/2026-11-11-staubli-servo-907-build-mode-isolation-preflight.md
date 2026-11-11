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
