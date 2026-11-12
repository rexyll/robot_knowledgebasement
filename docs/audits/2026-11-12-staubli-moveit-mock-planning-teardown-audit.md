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


## 6. 修复实施记录（2026-11-12）

### 6.1 用户镜像 PR

- 在用户镜像创建分支：`fix/mock-planning-shutdown-and-controller-gates`。
- Draft PR：[rexyll/staubli_driver_ros2_from_org#1](https://github.com/rexyll/staubli_driver_ros2_from_org/pull/1)。
- PR head SHA：`4091cb0b731c1003182846e3ea2041a01647336b`；包含2个文件提交。
- 未修改原始上游 `ICube-Robotics/staubli_driver_ros2`，也未将PR合并到用户镜像main。

### 6.2 已提交的代码改动

1. `staubli_moveit_config/test/test_moveit_mock_planning.launch.py`
   - 增加 `@launch_testing.post_shutdown_test()` 测试。
   - 使用 `launch_testing.asserts.assertExitCodes` 检查所有被测进程。
   - 允许退出码0与POSIX SIGINT对应的负信号退出码（`-signal.SIGINT`）；不会放行SIGSEGV（-11）或任意非零退出码。
   - 移除规划成功后固定 `time.sleep(1.0)`，避免把时间延迟误当作teardown验收。

2. `staubli_bringup/launch/launch_robot_control.launch.py`
   - 为joint_state_broadcaster spawner增加OnProcessExit处理；非零退出触发Shutdown。
   - trajectory controller spawner失败路径统一复用失败关闭逻辑。
   - 为 `ros2 control set_controller_state ... active` 增加OnProcessExit returncode gate；CLI非零退出触发Shutdown，零退出才记录激活成功。

### 6.3 API核对与验证边界

- 已读取ROS 2 Jazzy `ros2/launch` 分支中的 `assert_exit_codes.py` 与 `asserts/__init__.py`，确认 `assertExitCodes` 的 `process=None` 默认值会检查全部被测进程，且 `EXIT_OK=0` 可通过 `launch_testing.asserts` 访问。
- POSIX进程因SIGINT终止时Python subprocess returncode以负信号编号表示，因此测试显式使用 `-signal.SIGINT`，而不是把通用非零值列入allowlist。
- PR head combined status查询为空，PR workflow runs查询也为空；尚无Format、Documentation、ROS Jazzy CI或runtime launch test结果。
- 本轮没有运行ROS Jazzy容器，也没有真实CS9/HIL验证；当前源码修复状态为“已提交待验证”，不是PASS。
- 只有PR head的CI与MoveIt teardown运行时退出码全部通过后，才允许更新知识库源码pin并重跑OFF/ON矩阵。


### 6.4 PR自动检查状态更新

在PR创建后再次查询到：
- CI Run `43189959860`，job `build_and_test`，状态 `in_progress`；容器初始化、checkout、pip权限配置成功，正在执行 `ros-tooling/action-ros-ci@0.4.8`。
- Format Run `43189960017`，job `Format`，状态 `in_progress`；初始化、checkout、safe-directory配置及pre-commit安装成功，正在执行pre-commit。
- combined status接口仍返回空statuses；应以workflow run/job最终结论为准。
- 当前未发现Documentation run；MoveIt mock launch test的ROS Jazzy实际退出码仍待CI/运行时结果。


### 6.5 首轮CI失败根因分析与上游关联

**CI Run `43189959860`**
- mock MoveIt规划测试成功：MoveGroup action请求被接受，OMPL规划成功并返回非空轨迹。
- 新增post-shutdown断言失败：`move_group-6`在 `rclcpp::Executor::~Executor()`析构路径SIGSEGV，进程退出码为 `-11`。
- 同一次关闭期间，`ros2_control_node`的 `controller_manager.pal_statistics`后台线程两次报告 `context cannot be slept with because it's invalid`；控制器manager仍完成关闭，进程最终退出码为0。
- 失败不是规划失败，也不是spawner/activation gate失败；是shutdown生命周期缺陷被新测试揭示。

**上游关联证据**
- MoveIt 2开放问题 [#3680](https://github.com/moveit/moveit2/issues/3680)报告ROS Jazzy binary的move_group在SIGINT时于 `rclcpp::Executor::~Executor()`发生SIGSEGV，exit -11，与本次堆栈一致。该问题当前仍open，未见可直接回移的修复提交。
- ros-controls/realtime_tools开放问题 [#480](https://github.com/ros-controls/realtime_tools/issues/480)记录Jazzy关闭期间出现 `context cannot be slept with because it's invalid` 的后台线程异常。当前日志与该症状相符；本次ros2_control_node最终退出码为0。
- 因此本轮不在Stäubli驱动层伪造MoveIt或ros2_control依赖修复，也不允许把 `-11` 加入测试允许码。应把上游依赖缺陷作为显式阻塞项。

**Format Run `43189960017`**
- pre-commit其他检查均通过；Black对 `staubli_bringup/launch/launch_robot_control.launch.py`做了自动格式化并导致该run失败。
- 已提交格式修复 commit `4700b6b4dd010ac5b22459467bfcb970c2013d14`。

**当前复验**
- PR #1最新head：`4700b6b4dd010ac5b22459467bfcb970c2013d14`。
- CI Run `43192150453`、Format Run `43192150570`均为in_progress；尚无最终结论。
- PR保持Draft；不合并，不更新ROS Jazzy source pin。只有上游MoveIt shutdown缺陷得到修复且新head运行时teardown断言通过，才解除此阻塞。


## 6.6 第二轮 CI 结果、Black 格式根因与上游状态（2026-11-12）

### CI Run 43192150453

- Job `build_and_test`（ID `131093890219`）已完成，结论 FAILURE。
- MoveGroup 规划本体成功：mock hardware、loopback、headless 配置下，`/move_action` 请求被接受；`plan_only=true`，返回 `MoveItErrorCodes.SUCCESS`、非空轨迹及六关节名称集合。没有请求执行轨迹。
- 失败发生在 post-shutdown 断言：`move_group-6` 于 `rclcpp::Executor::~Executor()` 崩溃，exit `-11`。CTest 与 JUnit 各自报告同一 launch test 失败，因此 colcon 汇总为 73 tests、2 failures；唯一失败断言是进程关闭退出码，不是两个独立功能故障。
- 其余 71 项及其他包测试未报告失败。日志中 lcov `no .gcno files found` 是 coverage 收集阶段的附带输出，不是最终失败根因。

### Format Run 43192150570

- Job `Format`（ID `131093890103`）已完成，结论 FAILURE。
- pre-commit 中除 Black 外的检查通过；Black 自动重排 `staubli_bringup/launch/launch_robot_control.launch.py`。
- 逐行长度复核定位两处应由 Black 拆分的表达式：robot_description 字典中的 ParameterValue 调用（92列）和 joint_state_broadcaster 的 arguments 列表（93列）。此前格式提交只处理了另一处字符串日志行，因此不足以令 Black 幂等。
- 已按 Black 风格拆分两处表达式，提交 `18a6560bb65f8d81289c7a3b999da29dd0ce5a89`；该提交触发新的 Format 与 CI。

### 上游关联复核

- 通过 GitHub 集成重新读取 MoveIt 2 issue [#3680](https://github.com/moveit/moveit2/issues/3680)：状态仍为 OPEN，comments=0。报告中的 ROS Jazzy binary、`rclcpp::Executor::~Executor()` 栈帧及 SIGSEGV 症状与本次高度相似，但没有证据证明根因完全相同，也没有可直接回移的修复提交。
- 因此将其记录为上游关联/阻塞线索，而不是已证实的根因结论；不在 Stäubli 仓库中伪修外部 MoveIt 二进制，也不放宽 SIGSEGV 断言。

### 新一轮验证状态

- PR #1 当前 head：`18a6560bb65f8d81289c7a3b999da29dd0ce5a89`，仍为 Draft。
- CI Run `43197493740` / job `131112070965`：in_progress。
- Format Run `43197493726` / job `131112077084`：in_progress。
- 需在两项工作流完成后再次读取 job 状态和完整日志。Format 成功仅表示静态格式门槛通过，不代表 MoveIt shutdown runtime 通过。
- 不更新知识库 ROS Jazzy source pin；旧 pin `9e617a9e323ef3342f5151a89239bfd93c089f8c` 的历史 build/install/consumer PASS 不可外推至 PR head。
- 不接真实 CS9，不发送真实运动命令；SERVO-906/907、A1.1 继续 BLOCKED，`TODO-EXT-001` 未授权。


## 6.7 精确 Black 差异与 MoveIt shutdown 源码时序假设（2026-11-12）

### Format 诊断与修复

- 为避免 Black 只报告文件被重排却不展示差异，在用户镜像 PR 分支的 `.github/workflows/ci-format.yml` 增加了一个 `if: always()` 诊断步骤，在 pre-commit 失败后输出目标 launch 文件的 git diff。该诊断步骤本身不改变格式门槛。
- 诊断 Format Run `43197993909` / job `131113778634` 输出精确 diff：
  1. `robot_description` 字典中的 `ParameterValue(value=robot_description_content, value_type=str)` 应保持单行；
  2. 成功分支 `return [LogInfo(msg=f"Controller '{controller_name}' activated successfully.")]` 应保持单行。
- 仓库 `.pre-commit-config.yaml` pin Black 25.1.0，且参数为 `--line-length=99`。此前将这两处按88列拆分是错误的；现已按真实 formatter diff 还原为 Black 25.1.0 的输出。
- 精确修复提交：`01a3646c73e23d571627bf4e2acea0fc3f9ea6d9`。新 Format Run `43198319316`、CI Run `43198319123` 正在执行，最终结论待检查。

### MoveIt 2.12.4 / ROS 2 Jazzy shutdown 时序复核

- 读取 MoveIt 2.12.4 tag 的 `moveit_ros/move_group/src/move_group.cpp`。main 路径调用 `rclcpp::init(argc, argv)`，构造 `MultiThreadedExecutor executor`，再构造 `MoveGroupExe mge`，添加 node 并执行 `executor.spin()`，返回后调用 `rclcpp::shutdown()`。
- ROS Jazzy `rclcpp::InitOptions` 默认 `shutdown_on_signal=true`；`rclcpp::init()` 默认安装 SIGINT/SIGTERM handler。Context 文档说明 signal handler 会在启用该选项时 shutdown context，shutdown 会使派生节点、guard condition 等实体失效。
- ROS Jazzy `rclcpp::Executor::~Executor()` 在析构时仍调用 `notify_waitable_->remove_guard_condition(...) `、从 wait-set 移除实体，并通过 `context_->remove_on_shutdown_callback(...) ` 注销回调。
- 这给出一个与观察结果相容的假设：SIGINT 触发异步 context shutdown 后，executor 与其 guard conditions 的后续析构清理可能存在时序/生命周期问题。该假设不能仅凭源码顺序确认；还需要针对 move_group 的最小复现、gdb/ASan/调试构建和上游维护者确认。
- 若上游验证该假设，研究方向应是可控的信号处理：避免默认 handler 先销毁 context，使用线程安全的信号等待机制请求 executor.cancel，等待 spin 返回，按依赖顺序销毁 MoveGroup capabilities、node 和 executor，最后 shutdown context。不能在 POSIX async signal handler 中直接调用不保证 async-signal-safe 的 ROS API；也不能简单把 Executor 的析构清理跳过。
- 当前不修改 Stäubli 仓库中的外部 MoveIt/rclcpp 二进制或源代码；不以 sleep、SIGKILL、忽略 exit -11 或移除 post-shutdown assertion 作为解决方案。

### realtime_tools 关联问题状态修正

- ros-controls/realtime_tools issue [#480](https://github.com/ros-controls/realtime_tools/issues/480) 当前 CLOSED，讨论显示因长期无活动且未补充 stack trace 而自动关闭；没有证据表明其症状已修复。
- 因此，CI 中 `controller_manager.pal_statistics` publisher thread 的 `context cannot be slept with because it's invalid` 仍作为单独待调查症状，不再描述为“开放问题”。该进程本次最终退出码为0，不能将它与 move_group 的 SIGSEGV 混为同一个失败。

### 验证状态

- 最新 PR head：`01a3646c73e23d571627bf4e2acea0fc3f9ea6d9`。
- Format Run `43198319316` / job `131114885647`：运行中。
- CI Run `43198319123`：运行中。
- 旧 CI Run `43197493740` 再次确认同一 move_group exit `-11`，没有新发现其他功能失败；旧 Format Run `43197493726` 的精确差异已由诊断步骤定位。
- PR #1 保持 Draft，不合并；知识库源码 pin 保持旧 SHA `9e617a9e323ef3342f5151a89239bfd93c089f8c`。不连接真实 CS9、不发送真实运动命令；SERVO-906/907、A1.1 继续 BLOCKED，`TODO-EXT-001` 未授权。


## 6.8 最新 head 的 Format 通过与 CI 状态（2026-11-12）

- PR #1 最新 head：`01a3646c73e23d571627bf4e2acea0fc3f9ea6d9`。
- Format Run `43198319316` / job `131114885647` 已完成 SUCCESS。Black 25.1.0 使用仓库配置 `--line-length=99`；精确格式修复后所有 pre-commit 检查通过，formatter diagnostic step 正常完成。
- CI Run `43198319123` / job `131114885750` 仍在运行 `ros-tooling/action-ros-ci@0.4.8`；目前不能宣称 CI 通过。
- 最新 Format PASS 仅清除了格式门槛，不改变 MoveIt shutdown 的 runtime 验收状态。历史 head 的 CI 已两次在 move_group SIGSEGV (-11) 处失败，最新 head 仍需实测。
- PR 保持 Draft；不更新 ROS Jazzy source pin、不合并。真实 CS9/HIL 与运动命令仍禁止。


## 6.9 CI Run 43198319123 失败复核与 MoveIt shutdown-before-destruction 源码定位（2026-11-12）

### 最新 CI 的实际失败证据

- CI Run `43198319123` / job `131114885750` 已完成 FAILURE；同一 PR head `01a3646c73e23d571627bf4e2acea0fc3f9ea6d9` 的 Format Run `43198319316` SUCCESS。
- 完整日志显示 mock MoveGroup planning 已成功：日志为 `Motion plan was computed successfully.`，Python test `Ran 1 test ... OK`；没有请求真实轨迹执行。随后 launch_testing 向 move_group 发送 SIGINT，rclcpp 输出 `signal_handler(SIGINT/SIGTERM)`，进程在 `rclcpp::Executor::~Executor()` 崩溃并退出 `-11`。
- `test_all_processes_exit_cleanly` 在 post-shutdown assertion 失败，证明测试正确捕获崩溃。colcon 汇总的 73 tests / 2 failures 是 CTest 与 JUnit 对同一 launch test 的重复计数；唯一独立失败是 move_group 的退出码。
- 另一个进程 `ros2_control_node` 在 controller_manager shutdown 时输出两次 PAL statistics publisher thread 的 context-invalid 异常，但进程最终 clean exit；应独立跟踪，不能与 move_group SIGSEGV 合并成同一个根因。
- CI apt 安装的 MoveIt 版本可由日志直接确认：`ros-jazzy-moveit-ros-move-group 2.12.4-1noble.20260915.202214`；MoveIt Core、Planning、OMPL 等包也是 2.12.4 系列。

### MoveIt 2.12.4/Jazzy 的对象生命周期顺序

对照 [MoveIt 2.12.4 move_group.cpp](https://github.com/moveit/moveit2/blob/2.12.4/moveit_ros/move_group/src/move_group.cpp) 与 [ROS 2 Jazzy executor.cpp](https://github.com/ros2/rclcpp/blob/jazzy/rclcpp/src/rclcpp/executor.cpp)：

1. `main()` 在第220行调用默认 `rclcpp::init(argc, argv)`，没有传入自定义 `InitOptions`，因此使用默认 signal handler 行为。
2. 在 `if (planning_scene_monitor->getPlanningScene())` 作用域内先构造 `MultiThreadedExecutor executor`，后构造 `MoveGroupExe mge`。
3. 调用 `executor.spin()`；SIGINT 默认 handler 会触发 rclcpp Context shutdown 并使 spin 返回。
4. `move_group.cpp` 第331行又显式调用 `rclcpp::shutdown()`。
5. 之后才离开 if 作用域，按 C++ 逆序析构 `mge`，再析构 `executor`。Executor 析构在 Jazzy 中仍移除 interrupt/shutdown guard condition、wait-set entities，并注销 Context shutdown callback。

这条源代码顺序与“context 已 shutdown，而 MoveGroupExe/Executor 仍在进行析构清理”相吻合，且失败栈顶正落在 Executor 析构中。因此它比先前泛化的“signal handler 与析构可能竞争”更具体，是当前最强候选根因。仍不能仅凭静态顺序断言已证明具体 use-after-free：需要用受控的 source-built MoveIt overlay 调整生命周期后，在相同 launch test 中复测，最好取得带调试符号的完整 backtrace。

### 历史同栈问题与已合并修复的边界

- MoveIt issue [#3268](https://github.com/moveit/moveit2/issues/3268) 于 2025-04-15 报告 ROS Jazzy binary MoveIt 2.12.1 在 SIGINT 时于 `rclcpp::Executor::~Executor()` SIGSEGV，与本次栈特征几乎相同；该 issue 随 PR [#3435](https://github.com/moveit/moveit2/pull/3435) 合并而关闭。
- PR #3435 的实际改动是：planning request/response adapter 增加 virtual destructor；logger 全局节点从静态裸指针改为静态 `rclcpp::Node::SharedPtr`。这些改动已经存在于本轮 CI 所使用的 2.12.4/Jazzy 源码。
- 但 PR #3435 没有修改 `move_group.cpp` 中 `executor.spin()` 后、局部对象析构前调用 `rclcpp::shutdown()` 的顺序。故不能把 #3435 的标题“close move_group gracefully”理解为所有 Executor teardown SIGSEGV 都已消除。
- MoveIt issue [#3680](https://github.com/moveit/moveit2/issues/3680) 仍 OPEN，报告同类 MoveGroup shutdown SIGSEGV；截至本次查询没有评论或修复链接。
- MoveIt issue [#3721](https://github.com/moveit/moveit2/issues/3721) 是 MoveItPy 2.12.4 的不同代码路径：其评论指出 detached executor thread、先 `rclcpp::shutdown()` 再 delete MoveItCpp 的析构顺序问题。该案例支持 MoveIt 2.12.x 中存在 context/object teardown 次序风险，但不能当作本次 move_group 的直接根因证据。

### 验证计划与安全边界

- 在受控 MoveIt 源码实验分支中验证一个方案：通过 ROS 2 支持的信号处理机制避免默认 handler 先 shutdown Context；由专用 signal-wait/control thread 请求 `executor.cancel()`，等待 spin 完全返回；先析构 MoveGroupExe、相关节点和 Executor，最后 shutdown Context。不能在 POSIX async signal handler 中直接调用不保证 async-signal-safe 的 ROS API。
- 使用 source-built MoveIt overlay 对相同 Jazzy 环境运行现有 mock planning + post-shutdown launch test。必须同时证明 planning PASS、所有进程退出码合规、重复运行稳定；仅编译通过不算修复。
- 不在 Stäubli 驱动仓库伪修 MoveIt/rclcpp，不允许 SIGSEGV、不删除 post-shutdown assertion、不用 sleep/SIGKILL/日志过滤掩盖崩溃。未验证前 PR #1 保持 Draft，ROS Jazzy source pin 不更新、不合并。
- 不连接真实 CS9，不发送真实运动命令；SERVO-906/907、A1.1 继续 BLOCKED，`TODO-EXT-001` 未授权。


## 6.10 当前 MoveIt main 与 ROS 2 Jazzy rclcpp 默认信号处理参数复核（2026-11-12）

- 读取 MoveIt main 分支 moveit_ros/move_group/src/move_group.cpp：rclcpp::init(argc, argv) 位于 main 开始处；局部 Executor 与 MoveGroupExe 在同一作用域；executor.spin() 后仍先调用 rclcpp::shutdown()，之后才退出作用域并析构局部对象。当前 main 仍有与 Jazzy 2.12.4 相同的顺序，说明该候选问题并未在当前 main 通过简单重排解决。
- 读取 ROS 2 Jazzy rclcpp/include/rclcpp/init_options.hpp：InitOptions.shutdown_on_signal = true 是默认值。
- 读取 ROS 2 Jazzy rclcpp/include/rclcpp/utilities.hpp 与 utilities.cpp：rclcpp::init(...) 的默认 SignalHandlerOptions 为 All，并在 Context 初始化后安装信号处理器。
- 这使本次 teardown 的顺序链条更明确：SIGINT → 默认 handler shutdown Context → executor.spin 返回 → main 显式 shutdown → 离开作用域时析构 MoveGroupExe 和 Executor。它与 Executor 析构栈和 SIGSEGV 现象高度吻合，但仍需受控实验验证修复。
- 后续实验只在用户控制的隔离分支/临时工作区进行，不推送或修改 MoveIt 上游。候选方案为禁用默认自动 shutdown，使用受支持的同步信号等待/control thread 请求 executor.cancel，等待 spin 返回，销毁 MoveGroupExe/相关对象与 Executor，最后 shutdown Context。必须先确认 ROS 2 signal API 的安全用法，不能在异步 POSIX signal handler 中直接调用 ROS API。
- 现阶段不改动 Stäubli PR 的 MoveIt 依赖，不更新 source pin；PR #1 继续 Draft，exit -11 继续作为失败。


## 6.11 MoveIt 对象析构作用域与 logger pre-shutdown 修复的区分（2026-11-12）

### 直接析构顺序

- MoveIt Jazzy `moveit_ros/move_group/src/move_group.cpp` 的 main 中，`rclcpp::init(argc, argv)` 后创建 `nh`、`moveit_cpp` 与 `planning_scene_monitor`。
- 在 planning scene 的 if 块内，先声明 `MultiThreadedExecutor executor`，再声明 `MoveGroupExe mge`。C++ 逆序析构意味着退出该作用域时先析构 `mge`，再析构 `executor`。
- 当前代码在 `executor.spin()` 返回后、退出 if 作用域之前执行 `rclcpp::shutdown()`。因此析构 `mge` 和 `executor` 时 Context 已 shutdown；退出 main 时更外层的 `planning_scene_monitor`、`moveit_cpp`、`nh` 也在 shutdown 后才析构。
- 默认 `InitOptions.shutdown_on_signal=true` 且 `rclcpp::init()` 默认安装 SIGINT/SIGTERM handler，故 teardown 期间还可能发生先由 signal handler shutdown Context，再从 spin 返回的路径。
- 这一明确的作用域顺序与实际 SIGSEGV 栈帧 `rclcpp::Executor::~Executor()` 直接吻合，现列为首要根因候选。尚未宣称已证实：必须通过受控对象生命周期重排实验及重复运行验证。

### 与 MoveIt logger PR #3833 的区别

- MoveIt PR [#3833](https://github.com/moveit/moveit2/pull/3833) 于 2026-09-10 合入 main，修复 logger helper 中静态 `rclcpp::Node` 在 RMW shutdown 之后才进行静态析构的问题。实现通过 Context pre-shutdown callback 在 RMW teardown 前 reset node，并增加回归测试。
- 当前 MoveIt `jazzy` 分支的 `moveit_core/utils/src/logger.cpp` 尚不包含 `registerNodeResetOnPreShutdown` / `add_pre_shutdown_callback`。这与 main 分支已合入的修复不同；不能将 #3833 误认为已经进入 Jazzy 分支。
- Stäubli CI 安装的二进制包为 `ros-jazzy-moveit-ros-move-group 2.12.4-1noble.20260915.202214`。其构建日期晚于 #3833 合入日期，但当前未取得 bloom release source revision，故不能仅凭日期断言二进制是否包含 #3833。
- #3833 解决的是 logger static Node/RMW teardown 生命周期；本次观测栈帧明确位于 Executor 析构。两者可能都涉及 Context shutdown 顺序，但属于不同对象/路径，必须分别验证。

### 隔离实验

- 在用户镜像仓库创建分支 `experiment/move-group-shutdown-order`，workflow commit `5f33199b2b6615124df9ca67ea53b68e20ecf38a`。
- Workflow Run [43200850967](https://github.com/rexyll/staubli_driver_ros2_from_org/actions/runs/43200850967) 从 MoveIt `jazzy` 源码构建 `moveit_ros_move_group`，仅在本地临时 overlay 中把 main 的 MoveIt 对象生命周期包进一个外层作用域，使所有局部对象先析构，再执行 `rclcpp::shutdown()`。之后构建 Stäubli workspace 并运行原有 mock planning + strict post-shutdown launch test。
- 该实验不修改、不推送 MoveIt 上游；不修改 PR #1 的 source pin；不放宽 SIGSEGV 断言。Workflow 目前 RUNNING，job `131123588792`。
- 实验若通过，只能支持对象析构顺序假设，不能直接替代上游评审、release/backport 或重复运行。若失败，必须读取 backtrace 并判断是否是源码编译、运行环境或实际 teardown 缺陷。

### 验收边界

- PR #1 保持 Draft；不允许 exit -11，不删除 post-shutdown assert，不更新 ROS Jazzy source pin，不合并。
- 不连接真实 CS9、不发送真实运动命令；SERVO-906/907、A1.1 继续 BLOCKED；`TODO-EXT-001` 未授权。


## 6.12 隔离实验首次运行的环境失败与重试（2026-11-12）

- 首轮实验 Run [43200850967](https://github.com/rexyll/staubli_driver_ros2_from_org/actions/runs/43200850967) 在 `Install workspace tooling` 步骤失败：容器内不存在 `/opt/ros/jazzy/setup.bash`。workflow 使用的 `rostooling/setup-ros-docker:ubuntu-noble-latest` 并不等同于已安装 Jazzy 的 ROS 环境；失败发生在源码 clone/patch/build 之前。
- 因此首轮失败仅是 CI 环境准备错误，不能作为 MoveIt 对象作用域补丁失败或通过的证据。
- 已在实验 workflow 中加入 `ros-tooling/setup-ros@v0.7`，明确安装 `jazzy`；修复提交 `c1b664f0b2dd6f1f600ceabfa8241756ccaea04c`。
- 第二轮 Run [43201304163](https://github.com/rexyll/staubli_driver_ros2_from_org/actions/runs/43201304163) / job `131125130553` 已启动，当前 `Set up ROS Jazzy` step in_progress；后续步骤待执行。
- 保持实验范围不变：只在隔离 MoveIt Jazzy source overlay 中调整 move_group 局部对象作用域；不修改/推送 MoveIt 上游、不更新 Stäubli source pin、不放宽 SIGSEGV 断言。


## 6.13 ROS setup 脚本与 shell nounset 冲突修复（2026-11-12）

- 第二轮 Run [43201304163](https://github.com/rexyll/staubli_driver_ros2_from_org/actions/runs/43201304163) 已成功完成 ROS Jazzy setup、MoveIt Jazzy 源码 clone 和 move_group 对象作用域 patch。
- 在 `Install MoveIt source dependencies` 步骤 source `/opt/ros/jazzy/setup.bash` 时失败：`AMENT_TRACE_SETUP_FILES: unbound variable`。原因是脚本使用 `set -u`（nounset），而 ROS setup 脚本引用的变量并非全部预先定义；rosdep 本身尚未开始依赖解析。
- 将 workflow 五处 `set -euo pipefail` 改为 `set -eo pipefail`，保留失败即停与管道失败检测，只移除不兼容的 nounset。修复提交 `8ce23a0e3ba6579176cb295afc4968f73e8501c9`。
- 第三轮 Run [43201789602](https://github.com/rexyll/staubli_driver_ros2_from_org/actions/runs/43201789602) / job `131126782233` 已启动，当前 in_progress。
- 第二轮没有进入 rosdep dependency resolution、MoveIt build 或 mock test；不能据此判断源码补丁是否可编译或是否修复 SIGSEGV。
