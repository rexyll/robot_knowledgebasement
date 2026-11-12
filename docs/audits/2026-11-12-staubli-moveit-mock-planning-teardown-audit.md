# Stäubli MoveIt mock planning 与 launch teardown 审查

日期：2026-11-12

## 1. 审查范围与固定基线

- 用户镜像：`rexyll/staubli_driver_ros2_from_org`
- 当前检索到的镜像 main 最新提交：`4f9a37e12038174a010a9ad1f4523807fbb1434b`
- 最新提交内容：对 MoveIt mock planning launch test 中 controller state 字典应用 Black 格式修复。
- 前序整改：`7096035d13c20233f3fa58145d6337e0f29f99b1`等待 mock controller active；`84ba020e784fd7a8ab43b9c7a9f538b0a352db67`声明 controller manager service 测试依赖。
- 知识库当前既有 build/install/consumer 证据仍只覆盖旧 pin `9e617a9e323ef3342f5151a89239bfd93c089f8c`，不能外推到当前镜像 main。
- 当前提交 `4f9a37e...` 的 combined status 查询返回空状态列表；没有取得可验证的最新 Format/Documentation/CI 运行结果。

## 2. 已确认的测试能力

读取 `staubli_moveit_config/test/test_moveit_mock_planning.launch.py`，确认测试：
1. 使用 TX2-60L mock hardware、loopback IP、关闭 GUI；
2. 等待 controller manager 的 `list_controllers` 服务；
3. 轮询直到 joint_state_broadcaster 与 joint_trajectory_controller 均为 active；
4. 等待 `/move_action`；
5. 提交六关节 `MoveGroup` 规划请求，设置 `plan_only=True`；
6. 检查 goal accepted、MoveIt SUCCESS、轨迹非空及六个 joint name；
7. 规划断言结束后仅等待固定 1 秒。

因此，规划结果断言已建立，但不能据此证明 launch 进程正常退出。

## 3. 新发现的 teardown 与生命周期缺口

### 3.1 测试没有验证 shutdown 退出码

当前 launch test 文件没有发现 `@launch_testing.post_shutdown_test()` 测试，也没有发现对 `proc_info` 的退出码断言。此前记录的 move_group SIGSEGV（exit -11）与 controller activation CLI SIGINT（exit -2）因此仍未被本测试明确作为验收门槛捕获。

建议增加 post-shutdown 检查，对预期长期运行的 launch 进程验证退出状态；对测试框架发出的正常 SIGINT 关闭路径建立明确 allowlist，并将 SIGSEGV、非预期非零退出设为失败。不得简单把所有非零退出码都放行。

### 3.2 controller activation 命令缺少退出门控

读取 `staubli_bringup/launch/launch_robot_control.launch.py`：
- trajectory controller spawner 的 OnProcessExit 检查了 spawner returncode；
- 但成功路径启动的 `ros2 control set_controller_state ... active` 是独立 ExecuteProcess，没有对应 OnProcessExit handler，也没有等待/确认 activation CLI 成功；
- joint_state_broadcaster spawner 直接加入 launch description，没有与 trajectory spawner 相同的失败关闭处理。

因此，“spawner 启动成功”不等于“controller 最终 active”。mock planning test 的 active 轮询可以发现部分结果失败，但生产 bringup launch 本身的错误传播仍不完整。

### 3.3 MoveIt readiness gate 已有基本失败关闭

读取 `staubli_bringup/launch/launch_moveit.launch.py`，确认 wait_for_robot_ready 的退出码为 0 才启动 MoveIt；非零退出会输出错误并触发 Shutdown。此项保留为已实现的静态检查结论，但仍需运行时正/负向验证。

### 3.4 固定 sleep 不是 teardown 证明

MoveIt test 末尾的 `time.sleep(1.0)` 不能证明 controller activation 子进程已结束，也不能证明 move_group/ros2_control 进程在 launch_testing SIGINT 后正常退出。应使用明确的服务/状态/进程生命周期同步与 post-shutdown exit-code 断言替代基于时间的猜测。

## 4. 下一步修复顺序

1. 在 launch_testing 中增加 post-shutdown process exit validation，保留明确且最小化的正常 SIGINT allowlist。
2. 为 joint_state_broadcaster spawner 增加失败关闭处理。
3. 为 controller activation ExecuteProcess 增加 OnProcessExit returncode gate；失败时触发 Shutdown，成功时才允许后续阶段。
4. 移除或缩小固定 sleep，改用可观测的 lifecycle/service readiness。
5. 在 ROS Jazzy 镜像上运行 Format、Documentation、CI；逐条检查 move_group 与 controller_manager 的最终退出码及日志。
6. 只有最新镜像 SHA 的 CI 全通过后，才更新知识库源码 pin 并重新运行 OFF/ON build/install、独立 consumer、gtest、validator 与证据 manifest 矩阵。
7. 后续单独增加 mock trajectory action/feedback 测试；仍禁止真实硬件执行。

## 5. 安全边界与状态

- 本轮只做只读源码审查与知识库记录；没有修改 ICube 原始上游。
- 没有修改用户镜像源代码；没有触发或伪造 CI 运行结果。
- 不连接真实 CS9，不发送真实机器人运动命令。
- build/install/consumer 历史子门槛对旧 pin 保持 PASS；当前镜像 main 的 MoveIt teardown、controller activation lifecycle、trajectory action/feedback 仍 BLOCKED。
- SERVO-906/907 整体仍 BLOCKED；A1.1 BLOCKED；`TODO-EXT-001` 未授权。
