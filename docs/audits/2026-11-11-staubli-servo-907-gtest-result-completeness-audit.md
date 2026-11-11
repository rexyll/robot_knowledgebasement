# Stäubli SERVO-907：gtest 结果完整性与 Actions 验收记录

- 日期：2026-11-11
- 仓库：`rexyll/robot_knowledgebasement`，`main`
- 固定上游：`ICube-Robotics/staubli_driver_ros2@bd658e2d266e315d2ee35f985fb352ea88306b79`
- 范围：知识库侧 ROS Jazzy build/install 驱动脚本、gtest 结果门禁、普通 Actions CI 状态
- 上游源码保持只读；本记录不构成真实 ROS Jazzy 构建通过声明。

## 1. 本轮修复与回归测试

在 `scripts/run_staubli_build_testing_matrix.sh` 中，`colcon test-result --verbose` 后增加独立 XML 完整性门禁。门禁固定要求以下七个上游 gtest 报告全部存在：

- `test_primitives_serialization.gtest.xml`
- `test_message_serialization.gtest.xml`
- `test_sockets.gtest.xml`
- `test_rt_socket_interface.gtest.xml`
- `test_robot_driver.gtest.xml`
- `test_mock_robot_server.gtest.xml`
- `test_staubli_hardware_interface.gtest.xml`

门禁拒绝缺失或额外的 `*.gtest.xml` 文件，并逐个要求 XML 的 `tests >= 1`、`failures == 0`、`errors == 0`。成功时输出 `UPSTREAM_GTEST_XML_PASS reports=7`。该门禁用于避免“只检查已生成结果”的测试结果命令在某个 suite 被跳过时形成假绿。

对应知识库静态回归测试新增 `test_build_matrix_requires_all_upstream_gtest_xml_reports_to_pass`。

提交：
- `c7bfb3577ccb72843d6132c5c8a21f6b7950bb7d` — 增加七项 XML 报告完整性门禁。
- `8ce497cafcd65f86d4622da08b964417acb30e30` — 增加回归测试。

## 2. Actions 验收

| Run ID | 触发提交 | 状态 | Jobs |
|---|---|---|---|
| `43011935479` | `c7bfb3577ccb72843d6132c5c8a21f6b7950bb7d` | completed / success | 5/5 SUCCESS |
| `43011938140` | `8ce497cafcd65f86d4622da08b964417acb30e30` | completed / success | 5/5 SUCCESS |

两次运行均核验了 Python 3.10、3.11、3.12 测试、SBOM 生成和 OSV 依赖审计 Job；全部成功。

## 3. 专用 ROS Jazzy workflow 状态

专用 workflow：`.github/workflows/staubli-ros-jazzy-build.yml`，仅配置 `workflow_dispatch`。当前可用 GitHub 连接能力支持只读查询，未提供 workflow dispatch 写入动作。本轮没有触发新的专用运行。

最近一次专用运行仍为 Run `43008853603`，结论 failure。日志根因已定位并修复：前置依赖安装步骤清理 apt 索引后，rosdep 安装前未刷新 apt 索引。修复提交为 `eb1021a868129a7b6338414514a4d943390ce839`，回归测试提交为 `4e22b6a1f7d916786c12c2eecdf751995e31b511`。本轮最新 main push CI 成功并不能替代专用 workflow 重跑。

因此以下真实动态证据仍为 NOT_RUN / 未验收：
- ROS Jazzy 容器中的 apt/rosdep 依赖闭包安装；
- BUILD_TESTING=OFF 与 ON 的 colcon build/install；
- 两种安装前缀下的 install-space consumer 编译、链接和运行；
- 七个上游 gtest 的实际执行与 XML 报告路径；
- target graph validator、evidence bundle 生成及 SHA-256 manifest verify。

尤其需要通过下一次真实 workflow 确认 gtest XML 目录布局与预期路径一致；目前新增测试是知识库脚本静态合同测试，不能证明该目录在真实 ROS Jazzy 环境中已产生。

## 4. 状态与下一步

- 普通 Python CI：本轮两次运行均 SUCCESS。
- gtest XML completeness gate：已实现，静态回归测试通过。
- 专用 ROS Jazzy build/install：仍 BLOCKED，等待有仓库 Actions 写权限的用户手动触发。
- SERVO-907：BLOCKED / NOT_RUN；不得标记为完成。
- A1.1：BLOCKED；`TODO-EXT-001`：未授权。
- 固定上游 commit：保持不变，未修改、未创建上游 PR。

下一步应从 GitHub Actions 页面在 `main` 上手动运行专用 workflow，并首先检查 apt/rosdep 阶段是否通过；若进入矩阵，再核对 OFF/ON build/install、consumer、七份 gtest XML、validator 与 evidence manifest。若报告目录与预期不符，应按真实日志修正知识库脚本后重新运行。


## 5. 审计文档与计划同步提交的 CI

本审计记录提交 `909673d54bf46c8466f68f78ccdc297555bcf5eb` 对应 Run `43012296237`；第21章同步提交 `abb643c75827fbd2a8dae54feafb3b62a719ee6b` 对应 Run `43012304340`；根计划同步提交 `68a177c0a20aca707fe0ce83e49e7ee60dd3711b` 对应 Run `43012312051`。三次运行均 completed/success，各自五个Job（Python 3.10/3.11/3.12、SBOM、OSV）全部SUCCESS。
