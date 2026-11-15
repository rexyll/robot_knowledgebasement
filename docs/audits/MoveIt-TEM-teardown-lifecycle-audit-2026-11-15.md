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

### 8.2 Full access-point audit

The member is a plain `bool` in the Jazzy header. A scan of the entire source file found these important accesses that are not uniformly protected by `execution_state_mutex_`:

| Function | Source line | Access | Synchronization note |
|---|---:|---|---|
| `push()` | 397 | read | before trajectory append; no state lock at the check |
| `stopExecution()` | 1211 | read | outer condition before acquiring the state mutex |
| `execute()` | 1281 | write `false` | before creating the execution thread; no state lock |
| `clear()` | 1302 | read | condition outside the following scoped lock |
| `executeThread()` | 1317, 1337 | read | initial gate and post-part loop check outside the state mutex |
| `executePart()` | 1379, 1542, 1563 | read | pre-execution, timeout test and stop test outside the state mutex |

Other accesses are protected, including `stopExecution()` lines 1214/1220, `waitForExecution()` line 1290, `executeThread()` lines 1348/1357–1359, and `executePart()` lines 1384–1385. The issue is inconsistent synchronization across the full call graph, not the absence of a mutex. Because the member is a plain bool, a lock-free read concurrent with a mutex-protected write is still a potential C++ data race. A call-graph audit is required to determine which external API calls may actually overlap; source inspection alone does not prove a specific runtime UB event.

### 8.2 Why Run #102 does not cover it

Run #102 executed mock planning and strict process teardown five times, but it did not start a real trajectory execution thread. Its 5/5 pass therefore strengthens the main-node/TEM/plugin teardown evidence under the original launch file; it does not exercise the execution-thread completion race described above.

### 8.3 Candidate fix and test plan (not implemented)

1. Build a call/thread map for all access sites listed in §8.2, then make concurrent reads/writes consistently use `execution_state_mutex_` or a reviewed atomic-state design. Also review synchronization for the `execution_thread_` pointer itself.
2. After `stopExecution(true)`, independently acquire `execution_thread_mutex_`; if `execution_thread_` still exists and is joinable, join and reset it. Guard against self-join, and ensure destructor execution is external to the trajectory execution thread.
3. Once both the execution thread and private executor thread have stopped, call `clear()` to delete any remaining `trajectories_` raw contexts, then clear `active_handles_` under `execution_state_mutex_`.
4. Perform both cleanups before resetting `controller_manager_` or allowing `controller_manager_loader_` to unload the plugin DSO.
5. Add a dedicated mock trajectory-execution test with a barrier around the natural-completion flag transition; cover natural completion racing with destructor, stop request racing with completion, `auto_clear=true/false`, callback reentrancy, no-start/early-return, missing manager, exception path, and repeated shutdown.

This is a static source-derived risk, not an observed failure. The full set of reads/writes must be assessed against the actual API caller, execution thread and private executor callback threads before deciding which accesses can race. Do not patch MoveIt/rclcpp or production Stäubli code without separate authorization.

### 8.4 Workflow signal-handling correction

The experiment script had a stale message claiming a “structured signal-wait patch” was applied. Source inspection found no `sigwait`, `pthread_sigmask`, or `SignalHandlerOptions::None` implementation; the workflow only rejects such customization and retains MoveIt Jazzy's stock rclcpp signal handling. The experiment step name and output message have been corrected in workflow commit `1c151888bcbac4a62125db62d8890c6aef6071a1`. This is a description correction only; no signal-handler behavior or MoveIt source patch was added.

## 10. `active_handles_` strong-owner chain reaches plugin-defined controller handles

Additional Jazzy source inspection confirms that `active_handles_` can retain the last strong reference to a controller object implemented by the Simple Controller Manager plugin.

1. `MoveItControllerHandle` is a polymorphic base with a virtual destructor ([header lines 102–116](https://github.com/moveit/moveit2/blob/jazzy/moveit_core/controller_manager/include/moveit/controller_manager/controller_manager.hpp#L102-L116)).
2. The Jazzy Simple Controller Manager constructs `FollowJointTrajectoryControllerHandle` with `std::make_shared` ([source lines 216–221](https://github.com/moveit/moveit2/blob/jazzy/moveit_plugins/moveit_simple_controller_manager/src/moveit_simple_controller_manager.cpp#L216-L221)), stores handles in its `controllers_` map as `ActionBasedControllerHandleBasePtr` ([lines 327–331](https://github.com/moveit/moveit2/blob/jazzy/moveit_plugins/moveit_simple_controller_manager/src/moveit_simple_controller_manager.cpp#L327-L331)), and returns another shared-pointer owner from `getControllerHandle()` ([lines 252–258](https://github.com/moveit/moveit2/blob/jazzy/moveit_plugins/moveit_simple_controller_manager/src/moveit_simple_controller_manager.cpp#L249-L264)).
3. The plugin-defined `ActionBasedControllerHandle` creates its action client using `rclcpp_action::create_client<T>()` in its constructor ([lines 82–90](https://github.com/moveit/moveit2/blob/jazzy/moveit_plugins/moveit_simple_controller_manager/include/moveit_simple_controller_manager/action_based_controller_handle.hpp#L75-L92)). The action client teardown therefore participates in the same custom-deleter / CallbackGroup Waitable lifecycle discussed earlier.
4. TEM `executePart()` copies the returned owner into `active_handles_` at line 1412 and into a local `handles` vector at line 1414. The normal path clears `active_handles_` at lines 1577–1587; the local vector releases its references when `executePart()` returns.

Consequently, `controller_manager_.reset()` alone is insufficient: it releases the manager map's shared pointers, but any remaining TEM or execution-thread copies retain the plugin-defined object. If the last release occurs after `controller_manager_loader_` unloads the plugin DSO, the object's deleter / virtual destruction path can point into unmapped code. This is directly relevant to the Run #73 vptr-to-DSO evidence, though the exact control-block dynamic type is still not RTTI-resolved.

**Required candidate invariant:** join the execution thread (so the local vector is gone) → clear `active_handles_` while the manager and loader are still alive → reset the manager instance (releasing its map) → reset controller node / CallbackGroup (allowing action-client cleanup while mapped) → unload the plugin loader last.

Run #102 did not start trajectory execution, so it has not dynamically validated this final-release sequence. A dedicated mock trajectory execution regression is still required.

## 11. 下一步验收条件

- [x] Run #102实际checkout SHA、原始PR launch test blob与未注入controller deactivation的约束已核验；五轮mock planning和严格进程退出均通过。
- [x] Run #103与#104的运行时PR原始test blob SHA guard、五轮执行摘要、GDB/进程退出结果与artifact均已核验；两轮各5/5通过。
- [x] Run #106已在CI临时副本中首次实际执行plan_only=false mock trajectory；五轮controller action均报告Goal reached、TEM status SUCCEEDED、MoveGroup返回成功日志，失败只由错误的可选executed_trajectory字段断言引起；修正后的Run #107待验证。
- [ ] 核验Run #107的测试结果与TEM析构快照：execution_thread_joinable应为0，active_handles_after_stop应为0；若不是，分析残留引用和线程join路径。
- [ ] 把§10的owner chain落实为candidate teardown patch：execution thread join后清`active_handles_`，随后reset manager instance和node/group，loader最后卸载；在loader reset前断言`active_handles_.empty()`与manager为空。
- [ ] 覆盖`trajectories_`未执行/auto_clear=false/已完成但thread未join等边界，并为多个controller、send fail、cancel、natural completion race与异常早退建立mock真实轨迹执行用例。
- [ ] 将MoveIt overlay A/B有效改动与Jazzy upstream逐hunk最小化，对诊断marker、workflow-only和测试instrumentation做剥离，形成仅供审查的候选补丁说明。
- [x] PAL statistics日志已归因到上游issue #28与内层WallRate sleep异常catch，不作为MoveGroup teardown失败；不修改该第三方上游。
- [ ] stock ROS Jazzy Run #54仍失败；在生产PR/stock环境得到独立修复验证前，PR #1不得合并，SERVO-906/907及A1.1保持BLOCKED。
- [ ] 不修改MoveIt/rclcpp upstream，不改变Stäubli pin，不连接真实CS9，不发送真实运动命令，不宣称HIL/实机验收。任何production source/PR改动仍需单独授权。

---

## 12. Original-input reruns and first real mock trajectory execution (Run #103–107)

### 12.1 Independent C=off reruns

- Run [#103](https://github.com/rexyll/staubli_driver_ros2_from_org/actions/runs/43674935564), workflow commit `f99d3475fc37d55aa81604d3da31e0acaa0ca513`, completed successfully. Runtime checks confirmed PR #1 HEAD `7d9fa0d715db46060199eeca541514ddeed9c4c1` and original launch-test blob `2f23d471e2c2dd6ee9e6e5a9560bac88e5cdf14b`; no test-side controller deactivation was present. Five repetitions each reported 6 tests, 0 errors, 0 failures, 0 skipped; GDB inferiors exited normally. Artifact 14146697019, SHA-256 `3ecca283424de7b76e65c39d23fb21de2d39f48ba22b5d13a86c50b753eb3133`.
- Run [#104](https://github.com/rexyll/staubli_driver_ros2_from_org/actions/runs/43675449944), workflow commit `1c151888bcbac4a62125db62d8890c6aef6071a1`, also completed successfully with the same original HEAD/blob assertions and five clean repetitions. The workflow wording was corrected to clarify stock MoveIt Jazzy signal handling; no `sigwait` patch is applied. Artifact 14146433733, SHA-256 `3e237ebf0cd4856b2ccbb736d298184580c239e8383881689ce42aaa7b9d0c64`.

### 12.2 First plan-and-execute mock regression

The original PR launch test intentionally sets `planning_options.plan_only=true`; it never enters PlanExecution and does not create controller handles. A separate temporary CI-only test was added after the runtime original-blob check, leaving the PR source and its original test blob unchanged. It sends a MoveGroup goal with `plan_only=false` to the existing mock-hardware FollowJointTrajectory controller.

- Run #105 failed closed at the test-injection step because the Python overlay script over-escaped the newline anchor. It did not compile or execute the test; no upstream/project source was changed.
- Run [#106](https://github.com/rexyll/staubli_driver_ros2_from_org/actions/runs/43676118015), workflow commit `15783991d8d8fcf07c0d805ba44bc5f397f5aa6f`, built successfully and executed the plan-and-execute path in all five repetitions. Logs show the controller accepted the action goal and reported `Goal reached, success!`; TEM logged `Completed trajectory execution with status SUCCEEDED`; MoveGroup logged `Solution was found and executed.`.
- The new test nevertheless returned FAIL because it asserted that `MoveGroup.Result.executed_trajectory.joint_trajectory.points` must be non-empty. In this successful path that optional result member was empty; this assertion was invalid. The result error code was SUCCESS and the controller/TEM/MoveGroup logs independently confirmed execution. The launch post-shutdown process-exit test passed and all launched processes exited cleanly. Artifact 14147055556, SHA-256 `59ab7eade5bb17d5cf0f0d4fe87bf7b704358d73041fea27522903c9a597573a`.
- The assertion has been corrected to check the returned non-empty `planned_trajectory`, while retaining the `plan_only=false` request and SUCCESS result check. The workflow also snapshots `execution_thread_ && execution_thread_->joinable()` under `execution_thread_mutex_`, and `active_handles_.size()` under `execution_state_mutex_`, after stopExecution/private-executor join in the temporary TEM destructor.
- Run [#107](https://github.com/rexyll/staubli_driver_ros2_from_org/actions/runs/43677374898), workflow commit `18fea00298ee542c304cbf73d652cd540262712e`, is in progress. It will show whether the corrected assertion passes and whether the normal-completion path leaves a joinable execution thread or residual active handles.

### 12.3 Scope and interpretation

Run #103 and #104 add two independent original-input A+B C=off 5/5 mock-planning/teardown passes (10 more repetitions). Run #106 is **not** counted as a passing workflow, even though all five mock controller goals were accepted and reached success: the test failed on an invalid optional-result-field assertion. Run #107 is the first corrected plan-and-execute + teardown regression. §13 has now confirmed the concrete `/move_action` cancel → PlanExecution::stop → TEM stopExecution path can race the TEM execution thread.

A Run #107 PASS would establish only normal mock trajectory execution and shutdown. It does not deterministically exercise the §8 check-lock-recheck race where natural completion overlaps stopExecution/destruction. A barrier-controlled concurrency test is still required before claiming that thread-join race is fixed. None of these overlay results fixes stock ROS Jazzy Run #54, and they do not unblock Stäubli PR #1.

## 13. Concrete MoveGroup cancel-to-TEM concurrency path

A full call-graph check now confirms a real concurrent access path for TEM's plain-bool `execution_complete_`; this is stronger than merely assuming public APIs might be called from different threads.

### 13.1 `/move_action` path

1. MoveIt Jazzy `MoveGroupMoveAction::initialize()` creates the `/move_action` server. Its accepted callback starts a detached `std::thread` that runs `executeMoveCallback(goal)` ([source lines 64–82](https://github.com/moveit/moveit2/blob/jazzy/moveit_ros/move_group/src/default_capabilities/move_action_capability.cpp#L64-L82)).
2. That detached thread enters `executeMoveCallbackPlanAndExecute()` and calls `PlanExecution::planAndExecute()` ([lines 85–128 and 131–189](https://github.com/moveit/moveit2/blob/jazzy/moveit_ros/move_group/src/default_capabilities/move_action_capability.cpp#L85-L189)).
3. The action cancel callback runs in the ROS executor callback and calls `preemptMoveCallback()`, which writes `preempt_requested_=true` and calls `context_->plan_execution_->stop()` ([lines 74–77 and 281–285](https://github.com/moveit/moveit2/blob/jazzy/moveit_ros/move_group/src/default_capabilities/move_action_capability.cpp#L74-L77)).
4. `PlanExecution::stop()` calls `preempt_.request()`. Meanwhile `planAndExecuteHelper()` continues on the detached goal thread, launches TEM `execute()`, and monitors for `preempt_.checkAndClear()`. On preemption it calls TEM `stopExecution()` ([plan_execution.cpp lines 113–116 and 457–532](https://github.com/moveit/moveit2/blob/jazzy/moveit_ros/planning/plan_execution/src/plan_execution.cpp#L113-L116)).
5. TEM `execute()` creates another `execution_thread_`; `executeThread()` writes `execution_complete_=true` at lines 1357–1359 under `execution_state_mutex_`. Thus the caller executing TEM `stopExecution()` and the trajectory execution thread can overlap.

This makes the unlocked read at TEM `stopExecution()` line 1211 concurrent with the execution-thread write at line 1358 on a reachable call path. The other unlocked reads in `executeThread()` and `executePart()` may also overlap the stop caller's state write at line 1220. Because the member is a plain bool, this is a concrete data-race risk, not just a theoretical multi-caller possibility.

### 13.2 Separate `/execute_trajectory` capability

Do not conflate that path with `MoveGroupExecuteTrajectoryAction`. It uses a private `SingleThreadedExecutor` and a `MutuallyExclusive` callback group. Its goal callback synchronously calls TEM `execute()` and `waitForExecution()`; its cancel callback only returns `CancelResponse::ACCEPT`. The class helper `preemptExecuteTrajectoryCallback()` has a declaration and definition but no call site in the Jazzy source, so it must not be cited as a functioning concurrent stop path. The direct concurrency evidence above comes from `/move_action` + `PlanExecution::stop()`.

An adjacent issue exists in `MoveGroupMoveAction`: `preempt_requested_` is also a plain bool written by the cancel callback and read from the detached goal thread (e.g. source lines 176/198). This should be reviewed separately; it is not the DSO/Waitable crash root cause.

### 13.3 Deterministic race test design

- Add a test-only barrier after TEM `stopExecution()` has read `execution_complete_ == false` but before it acquires `execution_state_mutex_`.
- Allow the controller/trajectory execution thread to naturally finish and write the flag to true, then release the barrier.
- Confirm the second check takes the unlock path and determine whether `execution_thread_` remains joinable. A corrected implementation should guarantee join/reset regardless of which state transition wins.
- Explicitly join any remaining test thread before test teardown; never intentionally let a joinable std::thread reach ordinary object destruction in the test process.
- Add TSAN or equivalent coverage for `execution_complete_` and `preempt_requested_` accesses.
- Do not use the ExecuteTrajectory capability's currently unreferenced preempt helper as the test trigger.

### 13.4 Existing test harness limitation

The Jazzy `trajectory_execution_manager/test/test_execution_manager.cpp` retrieved from the upstream branch still includes ROS 1 `ros/ros.h`. The package `CMakeLists.txt` keeps its old catkin/rostest test registration commented out under `CATKIN_ENABLE_TESTING`. Its adjacent `test_moveit_controller_manager.hpp` is rclcpp-shaped, but the existing cpp test is not a ready-to-run Jazzy ament test target. Therefore a dedicated Jazzy ament test target or isolated temporary test executable is needed for the barrier-controlled test; do not claim an existing Jazzy GTest already covers this case.

## 14. Normal mock trajectory execution and five teardown snapshots (Run #107)

Run [#107](https://github.com/rexyll/staubli_driver_ros2_from_org/actions/runs/43677374898), workflow commit 18fea00298ee542c304cbf73d652cd540262712e, completed successfully with the temporary A+B MoveIt/rclcpp overlay and the fixed Stäubli PR #1 head. It ran both the original plan-only test and the separate plan_only=false FollowJointTrajectory execution test, then the strict process-shutdown assertion.

Artifact [14147826279](https://github.com/rexyll/staubli_driver_ros2_from_org/actions/runs/43677374898/artifacts/14147826279), SHA-256 b0e13044c3b51e9e7da2bd2b5653e5ed30a9e09692ab3677d206ef8c6250697a, contains five separate launch-test stdout directories. Each shows:
- test_move_group_plans_joint_goal_without_execution and test_z_move_group_executes_joint_goal_on_mock_controller: Ran 2 tests ... OK.
- test_all_processes_exit_cleanly: Ran 1 test ... OK.
- Controller: Goal reached, success!; TEM: Completed trajectory execution with status SUCCEEDED; MoveGroup: Solution was found and executed.
- TEM destructor snapshots: execution_thread_joinable=0 and active_handles_after_stop=0.

Thus all five normal mock trajectory executions completed and were followed by a clean TEM join / active-handle teardown. This complements the 15/15 plan-only original-input C=off repetitions from Runs #102–104. It does not prove the stopExecution check-lock-recheck race safe: in the normal successful path, PlanExecution's wait path has already joined the TEM execution thread before the destructor snapshot.

### Deterministic barrier harness status

- Run [#111](https://github.com/rexyll/staubli_driver_ros2_from_org/actions/runs/43678571443) failed closed in the CI-only injection step because the source slice for stopExecution() retained an extra blank line after its closing brace; the script required an exact newline-plus-closing-brace suffix. No MoveIt build or test ran, and no product source was modified.
- Run [#112](https://github.com/rexyll/staubli_driver_ros2_from_org/actions/runs/43678885235), workflow commit e61fd811175ad78b3d226b357e668aea8d0a5a3b, now trims the function slice before locating the final closing brace and re-inserting the state marker. It is in progress.
- For a valid reproduction, the test must record entered, thread_finished, released, and state; the post-barrier state should be execution_thread_joinable=1, active_handles=0 before MoveGroup teardown, followed by a clean process exit as the TEM destructor joins the leftover completed thread.
- A failure before those markers (e.g. no MONITOR feedback, trajectory completed before cancel, barrier not entered, or timeout) is a harness/trigger failure, not evidence that the race does not exist.
**本报告的结论边界：** Run #73 对control-block vptr与plugin DSO的三次映射证据、Jazzy源码所有权链已核验；Run #102–104在PR原始输入C=off下A+B overlay合计15次mock-planning/teardown repetitions通过；Run #107正常mock FollowJointTrajectory执行与析构快照5/5通过，五轮execution_thread_joinable=0、active_handles=0。Run #111屏障注入因函数尾部空白校验失败，Run #112正在验证修正后的barrier；execution_thread_竞态尚未动态复现；stock Run #54仍失败，PAL statistics日志已确认是非致命上游shutdown现象；PR #1继续Draft / BLOCKED。


## 7. Run #112 barrier test injection failure and Run #113 syntax correction (2026-11-15)

Run [#112](https://github.com/rexyll/staubli_driver_ros2_from_org/actions/runs/43678885235) 的 rclcpp overlay、MoveIt A+B overlay 与 Stäubli mock workspace 均已构建；失败发生在最终 mock regression 中。保存的 job log 报告临时生成的 test_moveit_mock_planning.launch.py 第 260 行出现 unterminated string literal。根因是 workflow 外层 Python 三引号字符串将 release_file.write("release\n") 中的转义提前解释，写入生成文件的是实际换行，破坏了字符串字面量。五轮均未真正运行新增 barrier test；因此 Run #112 不是 race reproduced，也不是 MoveIt 编译失败。

已在新的隔离分支 experiment/move-group-shutdown-order-barrier-fix 提交 workflow-only 修正：
- workflow commit：1d0787c71346144ad2950c537297562b7a73b81b；
- 将注入模板改为保留字面量反斜杠的双重转义；
- 在写入临时 launch test 前加入 ast.parse(source, filename=str(test_path))，使语法错误在 CI 注入步骤 fail-closed；
- workflow push trigger 加入新分支，便于独立复跑；
- 未修改 Stäubli driver source、PR #1、MoveIt/rclcpp upstream、main 或固定 source pin。

Run [#113](https://github.com/rexyll/staubli_driver_ros2_from_org/actions/runs/43680932114) 已由该分支触发。最近状态检查为 in_progress，job 132711175800 已完成 ROS Jazzy setup 和 workspace tooling，正在构建 unmodified rclcpp Jazzy overlay；其余构建、屏障回归和结果尚未完成。等待本轮真实测试结果前，不把 barrier 竞态写为已复现。

**边界：** Run #107仍只证明正常 mock trajectory execution 的 join 与 active_handles 清理；Run #112的测试注入语法错误未覆盖竞争窗口；Run #113成功与否都需要验证 entered/thread_finished/release/state marker 以及 execution_thread_joinable、active_handles、严格进程退出结果。stock Run #54 SIGSEGV 与 PR #1 Draft 状态不变。


## 8. Run #113 pre-completion CI progress snapshot (historical; superseded by §9)

This section preserves the in-progress snapshot written before Run #113 completed. Its final test evidence and conclusion are recorded in §9 below.

The GitHub Jobs API last reported the single `source-overlay-regression` job as `in_progress`. These steps have completed successfully:
- Unmodified ROS 2 Jazzy rclcpp overlay build.
- MoveIt Jazzy source fetch and CI-only teardown-order experiment preparation.
- Deterministic TEM stopExecution barrier injection (including the new Python AST syntax preflight).
- MoveIt source dependency installation.

The job is currently at **Build patched MoveIt move_group** (step 9), started at 2026-11-15 05:29:24 UTC. GitHub's job-log download endpoint currently returns BlobNotFound, so there is no readable compiler output and no basis to call this a failure or a hang. The Stäubli mock workspace build and the five-round mock execution/barrier race tests have not started. No race reproduction result exists yet.

The static injection review confirms the intended sequence: pause after the first `execution_complete_ == false` read and before locking `execution_state_mutex_`; allow the execution thread to finish and clear active handles; release the barrier; inspect whether the first stop call returns with a joinable execution thread and zero active handles; then verify the MoveGroup action result and subsequent strict teardown. This is test design review, not runtime evidence.


## 9. Run #113 deterministic check-lock-recheck missed-join reproduction (2026-11-15)

Run [#113](https://github.com/rexyll/staubli_driver_ros2_from_org/actions/runs/43680932114) completed successfully on workflow-only branch experiment/move-group-shutdown-order-barrier-fix, commit 1d0787c71346144ad2950c537297562b7a73b81b. Artifact 14148018987 was downloaded and inspected; ZIP SHA-256: d8fcea6f09eac1dbe4d1fcebc9459d6e6ebb9b401beefdae104babea466fcc4b.

### 9.1 Five-round marker evidence

All five marker directories (staubli_tem_barrier_1 through _5) contain entered=1, thread_finished=1, release=release, released=1. Every state file contains execution_thread_joinable=1 and active_handles=0.

The order is important: MoveGroup /move_action cancel enters stopExecution(); the CI-only barrier pauses before the state mutex is acquired; the controller/trajectory execution thread naturally completes and emits thread_finished; only then does the test release the barrier. After the original stopExecution() returns, the state marker still sees a joinable execution_thread_ while active controller handles are already zero. This directly exercises the inner re-check path where the original implementation takes the unlock branch and skips its first join.

### 9.2 Test and teardown outcome

Each of the five per-iteration logs (05-40-01, 05-40-19, 05-40-33, 05-40-46, 05-40-59) shows:
- The normal plan/execute test and the cancellation race test ran; the race test returned MoveGroup PREEMPTED.
- Controller reports Goal reached, success!; TEM reports trajectory execution SUCCEEDED (the action-level PREEMPTED is the externally requested MoveGroup cancellation result).
- Python test summary Ran 3 tests ... OK; CTest reports 100% passed; colcon reports 8 tests, 0 errors, 0 failures, 0 skipped.
- Later TEM destructor probes show execution_thread_joinable=0 and active_handles_after_stop=0, consistent with a subsequent teardown call joining the leftover completed thread.
- No SIGSEGV appears in any of the five iteration stdout logs.

The full workflow summary is failures=0/5, and Run #113 conclusion is success. Therefore the original TEM check-lock-recheck missed-join path is deterministically reproduced in 5/5 mock iterations.

### 9.3 Scope of the conclusion

This is strong evidence of a real lifecycle bug: the first stopExecution() can return without joining a thread that finished while the caller was between its outer check and state lock. The destructor later compensates by joining it. It does not establish that this path is the sole or direct cause of stock Run #54's DSO Waitable SIGSEGV. It is a mock/SIL lifecycle experiment only; it does not validate CS9, physical robot motion, EtherCAT/VAL3 behavior, HIL, SAT, or safety certification. No MoveIt/rclcpp upstream source or Stäubli driver product source was changed.

## 10. CI-only always-join candidate (pending)

A new isolated branch, experiment/move-group-stop-execution-join-fix, tests a minimal candidate on the same MoveIt Jazzy source overlay:
1. The test arms the barrier only immediately before sending the /move_action cancel request, so earlier normal planning tests do not block.
2. The candidate acquires execution_state_mutex_ and makes the stop/cancel decision only under that lock.
3. After releasing the state mutex, it always checks execution_thread_ under execution_thread_mutex_ and joins/resets any existing thread, including when natural completion won before the state lock was acquired.
4. clear() remains conditional on an actual stop request and auto_clear, preserving the existing behavior for already-completed executions.
5. The test now requires execution_thread_joinable=0, active_handles=0, and join_performed=1 after stopExecution returns; it also verifies the barrier's released marker is 1.

Latest candidate workflow commit: 065f2385f9519777db2af89924ad2520cd94a402. Run [#43682618698](https://github.com/rexyll/staubli_driver_ros2_from_org/actions/runs/43682618698) is in progress. The candidate changes workflow-injected MoveIt source only; no upstream or product repository file is modified.

**Remaining synchronization audit:** this candidate addresses the stopExecution outer unlocked check and missed join. It does not yet prove every execution_complete_ access in push(), executeThread(), executePart(), or MoveGroupMoveAction::preempt_requested_ is properly synchronized. These need a separate access/lock-domain review and TSAN or equivalent coverage. Do not mark the complete MoveIt lifecycle/data-race issue fixed based on this single candidate.

## 11. Remaining synchronization access-domain inventory (2026-11-15)

A targeted static pass over the MoveIt Jazzy source blobs (TEM cpp SHA 126469542aa546046e6e305b18b56213e91d69a8; MoveGroup action capability cpp SHA 0198a71b5be709bb1a5f62c97a8bb60961e948ac; header SHA 4306130dfc5d591d585696823e6c3af03670096e) found that the reproduced missed-join path is not the only synchronization concern.

### 11.1 execution_complete_ accesses in TrajectoryExecutionManager

| Source location | Access | Lock observation |
|---|---|---|
| push(), line 397 | read | No execution_state_mutex_ held at the read |
| stopExecution(), line 1211 (stock) | read | Outer fast-path read is unlocked; the CI-only always-join candidate removes it |
| stopExecution(), line 1214 (stock) | read | Re-check occurs while execution_state_mutex_ is held |
| stopExecution(), line 1220 (stock) | write true | Under execution_state_mutex_ |
| execute(), line 1281 | write false | Immediately before creating execution_thread_; not under state mutex |
| waitForExecution(), line 1290 | read | Under execution_state_mutex_ |
| clear(), line 1302 | read | Preliminary read occurs before taking execution_state_mutex_ |
| executeThread(), line 1317 | read | No state lock at the read; thread creation ordering covers the initial false write, but concurrent stop requires separate analysis |
| executeThread(), line 1337 | read | No state lock |
| executeThread(), line 1348 | read | Under execution_state_mutex_ |
| executeThread(), line 1358 | write true | Under execution_state_mutex_ |
| executePart(), line 1379 | read | No state lock |
| executePart(), line 1385 | read | Under execution_state_mutex_ |
| executePart(), line 1542 | read | No state lock |
| executePart(), line 1563 | read | No state lock |

The same field therefore has a mixture of locked and unlocked accesses. The reproduced stopExecution missed-join branch is real, and the outer unlocked read removed by the candidate is one part of the concern; however, it is not sufficient to claim every access is race-free. A complete correction must either make the state flag atomic with a reviewed memory-order/state protocol, or consistently guard every concurrent access with the same mutex while avoiding holding that mutex across controller waits or thread join. Review condition-variable wakeup, active_handles_, last_execution_status_, time_index_, clear(), and callback ordering together.

The pointer execution_thread_ also needs a complete ownership/lock audit: creation/assignment in execute() at line 1282 is outside execution_thread_mutex_, while join/reset paths use that mutex. The test path observes the pointer after the execution thread has been created, but it does not prove every possible concurrent creation/stop ordering.

### 11.2 MoveGroup preempt_requested_

In Jazzy move_action_capability:
- the header declares preempt_requested_ as a plain bool (header line 74);
- preemptMoveCallback() writes true (cpp line 283);
- executeMoveCallbackPlanAndExecute() reads it (line 176);
- executeMoveCallbackPlanOnly() reads it (line 198);
- MoveGroup action completion resets it to false (line 127).

The cancel callback and goal execution work can run in separate execution contexts. This field needs its own lock/atomic policy and tests; do not assume the TEM always-join change fixes it. It may be a separate race and is not established as a cause of the stock DSO Waitable SIGSEGV.

### 11.3 Next validation sequence

1. Finish Run #43682618698 and confirm the CI-only candidate asserts join_performed=1, execution_thread_joinable=0, active_handles=0 in all five natural-completion-before-state-lock repetitions.
2. Review all execution_thread_ creation, read, join and reset sites under one coherent ownership rule.
3. Resolve execution_complete_ access semantics consistently and run TSAN or an equivalent race-detection harness across natural completion, cancel, timeout, clear and action teardown.
4. Resolve preempt_requested_ separately and test plan-only and plan-and-execute cancel paths.
5. Only then prepare a versioned MoveIt upstream patch proposal, with no direct upstream modifications until separately authorized.

The current candidate remains a CI-only overlay. No upstream MoveIt/rclcpp or Stäubli product source was changed.

## 12. Candidate always-join Run #43682618698 injection-template failure and correction

Candidate workflow commit `065f2385f9519777db2af89924ad2520cd94a402` failed in the CI-only barrier injection step before compiling or running the candidate. The job log shows:

`SyntaxError: unterminated triple-quoted string literal`

The generated Python heredoc assigned a C++ function body to `stop_function = """...` but the workflow template omitted the closing triple quote before the next Python statement. The failure therefore belongs to the test/source-overlay generator, not the candidate C++ algorithm, MoveIt compilation, Stäubli driver, or product source.

A workflow-only correction has been committed on the same isolated branch:
- branch: `experiment/move-group-stop-execution-join-fix`
- latest commit: `42392ccf20644541e9e2394ae1cdb18ba6f8cc83`
- correction: close the Python triple-quoted function template after the C++ function closing brace; candidate semantics and required post-stop assertions are unchanged.

The branch file was fetched after the update and confirms the closing quote, arm-marker barrier, and `join_performed=1` / `execution_thread_joinable=0` assertions are present. A fresh run for commit `42392ccf...` has not yet been observed at the time of this record. No product source or upstream repository was changed.
