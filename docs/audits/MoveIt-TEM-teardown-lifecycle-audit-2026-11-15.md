# MoveIt Jazzy TEM / MoveGroup teardown 生命周期审查

**审查日期：** 2026-11-15  
**状态：** 静态源码所有权审查已完成；Run #102 的 C=off A+B overlay 五轮 mock 回归已通过；Run #103 独立重复正在执行。  
**适用边界：** MoveIt 2 Jazzy + ROS 2 Jazzy 的 Stäubli mock CI teardown。本文不是上游修复，也不构成 CS9、HIL 或真实机器人验收。

## 1. 结论摘要

Run #73 的三轮崩溃采样中，Waitable weak control block 的 vptr 均相对 `libmoveit_simple_controller_manager.so` 基址偏移 **0x5ed88**；该 DSO 在 weak-count release 崩溃前已卸载。三轮相同偏移、相同 DSO 映射关系，将证据从“插件卸载与崩溃时间相邻”推进到“待析构 control block 的虚表地址属于已卸载 controller-manager plugin DSO”的强生命周期机制证据。其具体 `_Sp_counted` 动态类型仍未通过完整 RTTI/符号解析确认，故不宣称模板实例已被完全识别。

MoveIt Jazzy 的 TEM 成员声明与默认析构顺序确实存在危险：`controller_mgr_node_`、private executor 和 `active_handles_` 声明在 `controller_manager_loader_` 之前；`controller_manager_` 声明在 loader 之后。默认逆序析构会先销毁 controller-manager instance 和 loader，再销毁更早声明的 node/executor/handle 容器。原始析构函数体只执行 `stopExecution(true)`、cancel private executor 和 join thread，没有明确建立 node / CallbackGroup / WaitSet 均先于 loader 销毁的保证。

ROS 2 Jazzy 的 action-client 与 CallbackGroup 实现为这一故障机制提供了源码解释：action-client 自定义 deleter 会尝试 `remove_waitable()`，但 `CallbackGroup::remove_waitable()` 以 `weak_ptr.lock()` 取得原 Waitable 后比较裸指针；当原 control block 的 strong count 已归零时，lock 会失败，expired weak entry 可能继续保留在 CallbackGroup 中，直至 CallbackGroup / Node 销毁或后续 prune。因此安全性不能只依赖 deleter 调用过 `remove_waitable()`；必须保证关联 node / CallbackGroup 在插件 DSO 卸载前销毁。

## 2. 固定源码证据

以下文件来自 MoveIt 2 Jazzy 与 ROS 2 rclcpp Jazzy。文件 blob SHA 已在任务记录中固定：

| 文件 | Blob SHA | 审查位置 |
|---|---|---|
| [trajectory_execution_manager.hpp](https://github.com/moveit/moveit2/blob/jazzy/moveit_ros/planning/trajectory_execution_manager/include/moveit/trajectory_execution_manager/trajectory_execution_manager.hpp#L302-L333) | `de453558b79662a2f473c0eb5c7999d7a6d34fa3` | 成员声明顺序 |
| [trajectory_execution_manager.cpp](https://github.com/moveit/moveit2/blob/jazzy/moveit_ros/planning/trajectory_execution_manager/src/trajectory_execution_manager.cpp#L86-L93) | `126469542aa546046e6e305b18b56213e91d69a8` | 析构函数 |
| [move_group.cpp](https://github.com/moveit/moveit2/blob/jazzy/moveit_ros/move_group/src/move_group.cpp#L97-L102) | `2389100756b420935a911a4b4764b196ec0a430f` | MoveGroupExe 析构 |
| [create_client.hpp](https://github.com/ros2/rclcpp/blob/jazzy/rclcpp_action/include/rclcpp_action/create_client.hpp#L53-L93) | `f594bca78d64a922670273edd568778a527e4199` | action-client custom deleter |
| [callback_group.cpp](https://github.com/ros2/rclcpp/blob/jazzy/rclcpp/src/rclcpp/callback_group.cpp#L205-L228) | `73cd458bbcdb1457e02a7e89df27aa09cd6ef45d` | Waitable weak refs 与 remove |
| [executor.cpp](https://github.com/ros2/rclcpp/blob/jazzy/rclcpp/src/rclcpp/executor.cpp#L224-L240) | `c922be8a0d70834c7ff1ef73e4c56e19575816ed` | remove_node |

### 2.1 TEM 成员与默认析构

在 `trajectory_execution_manager.hpp` 中，关键成员顺序为：

1. `node_`、`controller_mgr_node_`、`private_executor_`、`private_executor_thread_`；
2. `event_topic_subscriber_`、执行线程与状态锁；
3. `active_handles_`、`trajectories_`；
4. `controller_manager_loader_`；
5. `controller_manager_`。

C++ 成员按声明顺序构造、按相反顺序析构。因此默认析构时，`controller_manager_` 先于 loader 销毁，但 loader 仍早于 `trajectories_`、`active_handles_`、event subscription、private executor 和 controller node 销毁。这意味着不能把“manager instance 已析构”视为全部 plugin-owned 对象已经释放。

当前 `TrajectoryExecutionManager::~TrajectoryExecutionManager()` 的函数体为：

- `stopExecution(true)`；
- private executor 存在时调用 `cancel()`；
- private executor thread 可 join 时执行 `join()`。

随后才进入成员逆序析构。它没有显式 remove/reset controller node，也没有在 loader 销毁前对 CallbackGroup / Waitable weak control block 的最终释放建立保证。

### 2.2 Action-client Waitable 所有权链

MoveIt Simple Controller Manager 持有 controller node，并通过 ActionBasedControllerHandle 创建 ROS action client。Jazzy 的 `rclcpp_action::create_client()` 使用自定义 deleter closure，捕获 `weak_node` 与 `weak_group`；创建的 `Client<ActionT>` 作为 Waitable 注册到 NodeWaitables / CallbackGroup。CallbackGroup 保存的是 Waitable weak pointers。

自定义 deleter 会构造一个不拥有原 control block 的 fake shared pointer，仅用于将原 client 的裸地址传给 `remove_waitable()`。然而 `CallbackGroup::remove_waitable()` 对已存储的 weak pointer 调用 `lock()` 后才比较指针。如果原 client 已经进入最后一个 strong reference 的销毁流程，`lock()` 可能返回空，不能保证对应 expired weak entry 被即时移除。Executor 的 collector / WaitSet 还可能在执行期间持有相关实体引用，所以需要先停止、join 并销毁 executor，再释放 node / group。

## 3. 候选 teardown 顺序（仅作为验证假设）

### 3.1 MoveGroup 主作用域

1. executor.spin() 返回后先停止并 join PlanningSceneMonitor 的 scene publisher，再执行 Context shutdown，避免 publisher thread 与 Context 同时销毁。
2. 将 `MoveGroupExe` 声明在 `MultiThreadedExecutor` 之前，使逆序析构先销毁 executor / WaitSet，再析构 MoveGroupExe 及其 capability 实例。
3. Context shutdown 后释放 main scope 的 PSM、MoveItCpp 和 node 外部 shared owners；MoveGroupExe 仍持有其 context/capability 所需对象。
4. MoveGroupExe 析构先 clear capability instances，再 reset context，最后 reset capability plugin loader。必须确保 executor / WaitSet 已经结束使用 plugin-owned callbacks 后，才卸载 capability DSO。

### 3.2 TrajectoryExecutionManager

候选顺序为：

1. 停止轨迹执行，cancel private executor，并 join private executor thread。
2. reset event subscription 与 parameter callback handle；对专用 event callback group 显式管理生命周期。
3. 从 private executor 移除 controller node，reset private executor，使 WaitSet / collector 不再保留执行期 Waitable 引用。
4. 在 controller node 和 plugin loader 仍存活时 reset controller-manager plugin instance，让其 action-client custom deleter 在 DSO 仍加载时执行。
5. reset controller node，使 CallbackGroup 中仍可能存在的 expired weak entry / control block 在 DSO 卸载前完成析构。
6. 最后才让 `controller_manager_loader_` 销毁并卸载 DSO。

上述顺序是基于 Jazzy 源码与 Run #73 vptr 映射证据推导出的候选，不是已经合入上游的生产修复。实验 workflow 中对 event subscription 新增了独立 callback group 字段，属于 CI-only overlay 改动；不能把该插桩直接当成正式 API/生产补丁。

## 4. active_handles_ 与 trajectories_ 边界

`active_handles_` 是 `MoveItControllerHandlePtr` vector，声明在 `controller_manager_loader_` 之前。如果其中残留由 plugin 创建的 controller handle，默认成员逆序析构可能晚于 loader 卸载。

Jazzy 常见执行路径确实有清理逻辑：

- 未取得 controller handle 的分支会 clear；
- sendTrajectory 失败分支会 clear；
- executePart 正常/停止收尾路径会在 execution state mutex 下 clear；
- 该函数的局部 handle vector 在返回时析构。

但需要注意：

- `clear()` 只删除 `trajectories_` 中的 raw trajectory contexts，不会清理 `active_handles_`。
- `stopExecution(true)` 在进入时 `execution_complete_ == false` 的分支中 join 后才会调用 `clear()`；若进入时 `execution_complete_ == true` 且仍有 joinable execution thread，当前实现只 join/reset thread，不调用 auto_clear。
- 因此常见路径上 handle vector 由 executePart 自身清理，但不能仅凭调用了 `stopExecution(true)` 就证明所有边界路径都已经释放 plugin handles / trajectory contexts。

**要求：** teardown candidate 在执行线程 join 后、controller-manager loader reset 前，验证 `active_handles_.empty()`；必要时在确认无并发访问并持有正确状态锁的情况下显式释放残余 handles。对 `trajectories_` 也应覆盖尚未执行、`auto_clear=false`、执行已完成但 thread 尚未 join、controller manager 缺失、异常/早退和部分构造失败等路径。

该项是尚待验证的生命周期边界，不是 Run #73 已证实的第二处崩溃根因。不得将其写成已发生的独立 use-after-unload。

## 5. 受控实验与当前验证状态

| 实验 | 变量/输入 | 结果 |
|---|---|---|
| Run #75 | A=off、B=on、C=on | 3/3 FAIL |
| Run #76 | A=on、B=on、C=on | 3/3 PASS |
| Run #77 | A=on、B=off、C=on | 3/3 FAIL |
| Run #78 | A=on、B=on、C=on | 3/3 PASS |
| Run #79–#81 | A+B+C overlay | 5/5 PASS |
| Run #54 | stock ROS Jazzy + PR 原始测试，无 MoveIt overlay | teardown SIGSEGV |
| Run #102 | A+B overlay、C=off、PR 原始测试输入 | **5/5 PASS；每轮6 tests、0 errors、0 failures、0 skipped** |

其中 A 表示 MoveGroup 主作用域 owner / executor 顺序调整；B 表示 TEM 显式 cleanup；C 表示测试侧预先 deactivate joint_trajectory_controller。Run #75–#81 的 C=on 与 PR 原始 launch test 不同，所以其 5/5 通过不能替代 C=off 验证。

Run #102 的 workflow commit 为 `b49a934e16243b8c81039e5d3d9fd5876b76d046`，实验分支为 `experiment/move-group-shutdown-order`，Actions run ID 为 `43673306520`，job ID 为 `132687888928`。真实日志确认 checkout 到 PR #1 head `7d9fa0d715db46060199eeca541514ddeed9c4c1`，`git rev-parse HEAD`断言通过；测试文件原始 blob SHA `2f23d471e2c2dd6ee9e6e5a9560bac88e5cdf14b`已独立核验，workflow明确未对测试副本注入controller deactivation。rclcpp Jazzy诊断overlay、MoveIt A+B overlay和Stäubli mock workspace均成功构建；native non-ASan严格回归五轮均实际运行，每轮planning成功、`test_all_processes_exit_cleanly`为ok，GDB child clean exit，汇总6 tests/0 errors/0 failures/0 skipped，`colcon_test=0`、`test_result=0`，最终`failures=0/5`。无MoveGroup SIGSEGV、GDB wrapper 255或异常进程退出。Artifact 14145626553，SHA-256为`f08745fa82a6121649e8a6017f6eeb1fb9cb06e11e35b47b29b7efcf26198809`。

五轮TEM dtor probes均记录main/controller context已invalid（valid=0），事件订阅、callback group、controller node释放按序完成；MoveGroup Executor destructor body END先于MoveGroupExe dtor，随后依次clear capabilities、reset context和loader。当前overlay中的executor cancel与默认`remove_node(..., notify=true)`在这五轮未造成测试失败。另有`ros2_control_node`的`controller_manager.pal_statistics` publisher thread在Context invalid后报`context cannot be slept with because it's invalid!. Aborting!`，部分日志还显示rosout publisher context invalid；尽管进程退出测试通过，这仍是需独立分析的controller-manager shutdown线程现象，不能将其忽略或与MoveGroup Waitable SIGSEGV混为一谈。

为满足独立复跑要求，workflow commit `f99d3475fc37d55aa81604d3da31e0acaa0ca513`（Run #103，ID `43674935564`）已新增运行时测试文件blob SHA校验与controller-deactivation负向检查；Run #103结果待核验。

## 6. Run #102 原始 PR 测试条件 C=off 的五轮结果

Run [#102](https://github.com/rexyll/staubli_driver_ros2_from_org/actions/runs/43673306520)（workflow commit `b49a934e16243b8c81039e5d3d9fd5876b76d046`，job `132687888928`）完成，run/job conclusion 均为 success。运行时日志显示 Stäubli source commit checkout 到 `7d9fa0d715db46060199eeca541514ddeed9c4c1`，并通过 `rev-parse HEAD`断言；运行前打印“Using the PR launch test file unchanged; no test-side controller deactivation overlay”。该 launch test 文件 blob SHA为`2f23d471e2c2dd6ee9e6e5a9560bac88e5cdf14b`，与PR head原始文件相符。

五轮 native non-ASan strict regression均真实执行。每轮都记录到planning request与`Motion plan was computed successfully`；`test_all_processes_exit_cleanly`每轮均为`ok`，GDB子进程均clean exit；每轮测试汇总均为6 tests、0 errors、0 failures、0 skipped，`colcon_test=0`、`test_result=0`，最后`failures=0/5`。日志检索未发现MoveGroup SIGSEGV、Segmentation fault、GDB wrapper exit 255或测试失败。

Artifact：[moveit-shutdown-order-experiment-logs](https://github.com/rexyll/staubli_driver_ros2_from_org/actions/runs/43673306520/artifacts/14145626553)，ID 14145626553，SHA-256 `f08745fa82a6121649e8a6017f6eeb1fb9cb06e11e35b47b29b7efcf26198809`。

### Lifecycle markers 与残余现象

- 五轮TEM析构探针均记录`main_context_valid=0`、`controller_context_valid=0`；event subscription reset、callback group reset、controller node reset均执行完成。
- 五轮MoveGroup侧均记录Executor destructor body END后才进入MoveGroupExe析构，之后依次执行`capabilities_.clear()`、`context_.reset()`、`capability_plugin_loader_.reset()`。
- 当前overlay在Context invalid后执行private executor cancel、并以默认`notify=true`调用`remove_node`，本次五轮均未因此失败。由于executor线程已join、非spinning，未来最小化补丁可以评估将`remove_node(controller_mgr_node_, false)`作为明确的无通知收尾；这属于代码整洁/健壮性检查，不是本次已观测故障。
- 五轮中多次出现`ros2_control_node`的`controller_manager.pal_statistics` publisher thread在Context invalid后报告`context cannot be slept with because it's invalid!. Aborting!`；某些轮次还报告rosout publisher context invalid。它没有导致当前进程退出断言失败，但应单列为controller-manager统计发布线程的shutdown顺序/退出边界；当前没有证据表明它与Run #73的MoveGroup Waitable control-block/DSO崩溃为同一原因。

### 结论边界

Run #102证明：A+B临时MoveIt/rclcpp源码overlay在Stäubli PR原始launch测试输入（C=off）下，取得五轮连续的native non-ASan mock planning与严格进程退出PASS。它没有证明未修改的`/opt/ros/jazzy` stock MoveIt/rclcpp通过；Run #54 stock CI仍有MoveGroup teardown SIGSEGV。因此这项结果提高了候选修复的可信度，但还不能解锁PR #1或SERVO-906/907。

独立重复Run #103已由workflow commit `f99d3475fc37d55aa81604d3da31e0acaa0ca513`触发；该轮额外要求运行时checkout test blob SHA精确等于`2f23d471e2c2dd6ee9e6e5a9560bac88e5cdf14b`，并拒绝任何controller-deactivation逻辑。Run [#103](https://github.com/rexyll/staubli_driver_ros2_from_org/actions/runs/43674935564)结果待验证。

### PAL statistics shutdown message: confirmed upstream issue, non-fatal

- 上游 [pal_statistics issue #28](https://github.com/pal-robotics/pal_statistics/issues/28) 于2026-09-10报告完全相同的ROS 2 Jazzy / Ubuntu 24.04消息：`Exception in publisher thread: context cannot be slept with because it's invalid!. Aborting!`。issue仍open。
- 对照 `pal-robotics/pal_statistics` 的 `humble-devel` 源码，package version为2.8.2；`pal_statistics/src/pal_statistics.cpp` blob SHA `03a4037c0a4ab73af488ea984cd96e86e2f43530`，`StatisticsRegistry::publisherThreadCycle()` 位于342–367行。外层循环检查 `rclcpp::ok()`，但内层 `while (!is_data_ready_ && !interrupt_thread_)` 只执行 `rclcpp::WallRate(2000).sleep()`。Context shutdown后sleep抛runtime_error，由同函数catch记录ERROR；随后外层循环重新检查 `rclcpp::ok()`，返回并退出线程。
- 因此日志中的“Aborting!”是误导性文本，不表示调用`abort()`或进程异常终止；上游issue说明进程退出码为0。Run #102中move_group与ros2_control_node均正常退出，与该上游已知行为一致。
- 本项目不改pal_statistics源代码、不把此日志计作MoveGroup teardown失败；仅保留上游引用与日志归因。此issue仍可能影响log-based health checks，但不构成本轮mock退出回归blocker。

## 8. TEM execution_thread_ teardown race discovered after Run #102

A second, separate lifecycle hazard is visible in the unmodified MoveIt Jazzy source. This is **not** the Run #73 Waitable control-block crash root cause and has not yet been dynamically reproduced.

### 8.1 Check-lock-recheck window

In [`TrajectoryExecutionManager::stopExecution()`](https://github.com/moveit/moveit2/blob/jazzy/moveit_ros/planning/trajectory_execution_manager/src/trajectory_execution_manager.cpp#L1209-L1252):

- Line 1211 reads `execution_complete_` before taking `execution_state_mutex_`.
- Lines 1213–1214 then lock and read the same flag again.
- Meanwhile `executeThread()` writes `execution_complete_ = true` under that mutex at lines 1357–1359.
- If the first read sees false, and the execution thread completes before the second read, the second check takes the unlock branch at 1239–1240. It does not join `execution_thread_`; the `else if (execution_thread_)` at 1242 belongs to the outer initial `if` and is skipped.
- The TEM destructor at lines 86–93 calls `stopExecution(true)`, then cancels/joins only `private_executor_thread_`; it has no independent unconditional join of `execution_thread_`.

The header declares `execution_complete_` as a plain bool, not atomic, at line 327. Its execution-thread write is mutex-protected, but the first read in stopExecution is outside that mutex, so this path also deserves a data-race review. `executeThread()` does not reset the `execution_thread_` pointer itself. If the join path is missed, later destruction of a still-joinable `std::thread` may call `std::terminate`.

### 8.2 Why Run #102 does not cover it

Run #102 executed mock planning and strict process teardown five times, but it did not start a real trajectory execution thread. Its 5/5 pass therefore strengthens the main-node/TEM/plugin teardown evidence under the original launch file; it does not exercise the execution-thread completion race described above.

### 8.3 Candidate fix and test plan (not implemented)

1. Make every read/write of `execution_complete_` use `execution_state_mutex_`, or adopt a reviewed atomic-state design; eliminate the current unlocked plain-bool read.
2. After `stopExecution(true)`, independently acquire `execution_thread_mutex_`; if `execution_thread_` still exists and is joinable, join and reset it. Guard against self-join, and ensure destructor execution is external to the trajectory execution thread.
3. Once both the execution thread and private executor thread have stopped, call `clear()` to delete any remaining `trajectories_` raw contexts, then clear `active_handles_` under `execution_state_mutex_`.
4. Perform both cleanups before resetting `controller_manager_` or allowing `controller_manager_loader_` to unload the plugin DSO.
5. Add a dedicated mock trajectory-execution test with a barrier around the natural-completion flag transition; cover natural completion racing with destructor, stop request racing with completion, `auto_clear=true/false`, callback reentrancy, no-start/early-return, missing manager, exception path, and repeated shutdown.

This is a static source-derived risk, not an observed failure. Do not patch MoveIt/rclcpp or production Stäubli code without separate authorization.

### 8.4 Workflow signal-handling correction

The experiment script had a stale message claiming a “structured signal-wait patch” was applied. Source inspection found no `sigwait`, `pthread_sigmask`, or `SignalHandlerOptions::None` implementation; the workflow only rejects such customization and retains MoveIt Jazzy's stock rclcpp signal handling. The experiment step name and output message have been corrected in workflow commit `1c151888bcbac4a62125db62d8890c6aef6071a1`. This is a description correction only; no signal-handler behavior or MoveIt source patch was added.

## 9. 下一步验收条件

- [x] Run #102实际checkout SHA、原始PR launch test blob与未注入controller deactivation的约束已核验；五轮mock planning和严格进程退出均通过。
- [ ] 核验独立重复Run #103的运行时test blob SHA guard、五轮执行摘要、GDB/进程退出结果与artifact；若出现不一致，不将结果并入通过统计。
- [ ] 增加/验证 `active_handles_.empty()` invariant：在线程join后、controller-manager loader reset前检查；覆盖异常/早退、未启动执行线程、`auto_clear=false`、controller manager缺失和部分构造失败。
- [ ] 覆盖 `trajectories_` 的未执行、执行已完成但thread未join、Context已shutdown、重复shutdown、controller update in-flight等边界。
- [ ] 将MoveIt overlay A/B有效改动与Jazzy upstream逐hunk最小化，对诊断marker、workflow-only和测试instrumentation做剥离，形成仅供审查的候选补丁说明。
- [x] PAL statistics日志已归因到上游issue #28与内层WallRate sleep异常catch，不作为MoveGroup teardown失败；不修改该第三方上游。
- [ ] stock ROS Jazzy Run #54仍失败；在生产PR/stock环境得到独立修复验证前，PR #1不得合并，SERVO-906/907及A1.1保持BLOCKED。
- [ ] 不修改MoveIt/rclcpp upstream，不改变Stäubli pin，不连接真实CS9，不发送真实运动命令，不宣称HIL/实机验收。任何production source/PR改动仍需单独授权。

---

**本报告的结论边界：** Run #73 对control-block vptr与plugin DSO的三次映射证据、Jazzy源码所有权链已核验；Run #102在PR原始输入C=off下A+B overlay五轮通过，但stock Run #54仍失败；Run #103独立复跑待核验；新增的TEM execution_thread_竞争窗口只是静态风险、尚未动态复现；PAL statistics日志已确认是非致命上游shutdown现象；PR #1继续Draft / BLOCKED。
