# MoveIt Jazzy 执行状态与取消路径线程安全静态审计

- 审计日期：2026-11-16
- 审计范围：MoveIt 2 Jazzy 的 TrajectoryExecutionManager（TEM）执行状态与线程对象，以及 MoveGroupMoveAction 的 action cancel/preempt 路径
- 源码基线：MoveIt 2 Jazzy branch，审计快照 commit `f11204b8a9b98e4ba28e564721d24a7077f5f969`（2026-10-28）
- 结论状态：静态访问路径审查完成；ThreadSanitizer / 动态竞态复现未执行；不等同于已获得TSAN报告或实机故障复现
- 变更边界：本轮仅读取公开上游源码并形成审计记录；没有修改 MoveIt upstream、Stäubli 产品源码或控制器配置

## 1. 摘要

静态审查发现四组需要继续处理的并发状态：

1. **MoveGroupMoveAction::preempt_requested_：高置信度未同步跨线程访问。** 字段是普通 bool；action cancel callback 调用 preemptMoveCallback() 写入 true；accepted callback 则创建 detached worker thread 执行 executeMoveCallback()；该worker在规划/执行前读取该字段，并在处理结束时写回 false。代码中未见 mutex 或 atomic 保护。
2. **TEM::execution_complete_：Jazzy 分支仍为普通 bool，锁保护不一致。** stopExecution() 在 execution_state_mutex_ 之外先读取该字段，再进入锁内二次读取并写入；executionThread/executePart路径又存在未持同一 mutex 的读取；这为执行线程与外部停止路径重叠时的数据竞争提供了直接条件。
3. **TEM::last_execution_status_：普通状态成员的读写保护不一致。** stopExecution() 在状态锁内写 PREEMPTED；执行线程也在多个未持锁位置写 SUCCEEDED、ABORTED、TIMED_OUT等状态；getLastExecutionStatus()直接返回，不获取状态锁。并发cancel/自然结束/状态查询时需要TSAN验证。
4. **TEM::execution_thread_：unique_ptr访问存在锁域缺口。** join/reset路径使用 execution_thread_mutex_，但 execute() 创建并赋值线程时未持该锁；stopExecution() 还有一次在加锁前读取 execution_thread_ 的分支判断。并发 execute/stop 调用时存在访问竞争可能，需先确认公共API的调用序列约束，再用TSAN验证。

以上为源码级风险识别，不应被写成“已在实机复现”。其中 action cancel 与 detached worker 路径存在明确的线程分离，风险证据最直接；TEM的状态变量也需按实际调用重叠用TSAN确认。

## 2. 源码基线与引用

### 2.1 MoveGroupMoveAction 的取消路径

- action server创建、cancel callback、accepted callback：[`move_action_capability.cpp` L64-L83](https://github.com/moveit/moveit2/blob/f11204b8a9b98e4ba28e564721d24a7077f5f969/moveit_ros/move_group/src/default_capabilities/move_action_capability.cpp#L64-L83)
- accepted callback启动 `std::thread{...}.detach()`：同上 L79-L82；执行worker随后进入 `executeMoveCallback()`。
- worker执行结束时将 `preempt_requested_ = false`：[`move_action_capability.cpp` L123-L129](https://github.com/moveit/moveit2/blob/f11204b8a9b98e4ba28e564721d24a7077f5f969/moveit_ros/move_group/src/default_capabilities/move_action_capability.cpp#L123-L129)
- worker读取该字段：[`move_action_capability.cpp` L175-L203](https://github.com/moveit/moveit2/blob/f11204b8a9b98e4ba28e564721d24a7077f5f969/moveit_ros/move_group/src/default_capabilities/move_action_capability.cpp#L175-L203)
- cancel callback调用的 `preemptMoveCallback()` 写入 true：[`move_action_capability.cpp` L281-L285](https://github.com/moveit/moveit2/blob/f11204b8a9b98e4ba28e564721d24a7077f5f969/moveit_ros/move_group/src/default_capabilities/move_action_capability.cpp#L281-L285)
- 字段声明为普通 bool：[`move_action_capability.hpp` L68-L76](https://github.com/moveit/moveit2/blob/f11204b8a9b98e4ba28e564721d24a7077f5f969/moveit_ros/move_group/src/default_capabilities/move_action_capability.hpp#L68-L76)

**静态判断：** accepted callback 只启动并脱离一个独立工作线程；cancel callback仍由ROS action server callback路径执行。两条路径分别写/读同一普通bool，未发现共享mutex或atomic。计划执行器自己的 preempt_ 另有 atomic<bool>，但它不自动保护 MoveGroupMoveAction 的这个独立字段。

### 2.2 TrajectoryExecutionManager 状态变量

- 字段声明：[`trajectory_execution_manager.hpp` L313-L332](https://github.com/moveit/moveit2/blob/f11204b8a9b98e4ba28e564721d24a7077f5f969/moveit_ros/planning/trajectory_execution_manager/include/moveit/trajectory_execution_manager/trajectory_execution_manager.hpp#L313-L332)
  - execution_thread_：unique_ptr<std::thread>
  - execution_state_mutex_、execution_thread_mutex_
  - last_execution_status_：普通 ExecutionStatus 成员
  - execution_complete_：普通 bool
- stopExecution() 外层未加锁读取与锁内二次检查/写入：[`trajectory_execution_manager.cpp` L1209-L1252](https://github.com/moveit/moveit2/blob/f11204b8a9b98e4ba28e564721d24a7077f5f969/moveit_ros/planning/trajectory_execution_manager/src/trajectory_execution_manager.cpp#L1209-L1252)
- execute()调用stopExecution后写 execution_complete_=false 并分配执行线程：[`trajectory_execution_manager.cpp` L1254-L1284](https://github.com/moveit/moveit2/blob/f11204b8a9b98e4ba28e564721d24a7077f5f969/moveit_ros/planning/trajectory_execution_manager/src/trajectory_execution_manager.cpp#L1254-L1284)
- waitForExecution()在状态锁内等待完成，但之后通过 stopExecution join：[`trajectory_execution_manager.cpp` L1286-L1298](https://github.com/moveit/moveit2/blob/f11204b8a9b98e4ba28e564721d24a7077f5f969/moveit_ros/planning/trajectory_execution_manager/src/trajectory_execution_manager.cpp#L1286-L1298)
- executeThread()读取/写入完成标志与状态、完成通知：[`trajectory_execution_manager.cpp` L1313-L1369](https://github.com/moveit/moveit2/blob/f11204b8a9b98e4ba28e564721d24a7077f5f969/moveit_ros/planning/trajectory_execution_manager/src/trajectory_execution_manager.cpp#L1313-L1369)
- executePart()中完成标志、active handles和last status访问：[`trajectory_execution_manager.cpp` L1371-L1596](https://github.com/moveit/moveit2/blob/f11204b8a9b98e4ba28e564721d24a7077f5f969/moveit_ros/planning/trajectory_execution_manager/src/trajectory_execution_manager.cpp#L1371-L1596)
- getLastExecutionStatus()直接返回成员：[`trajectory_execution_manager.cpp` L1679-L1682](https://github.com/moveit/moveit2/blob/f11204b8a9b98e4ba28e564721d24a7077f5f969/moveit_ros/planning/trajectory_execution_manager/src/trajectory_execution_manager.cpp#L1679-L1682)

**静态判断：** execution_state_mutex_ 对部分路径提供保护，但读取/写入该状态变量并非全部在同一锁域内。不能仅凭condition_variable等待使用了mutex，就把所有execution_complete_访问推断为同步安全。execution_thread_mutex_也未覆盖线程对象的所有读写点；最明显的缺口是execute()中的unique_ptr赋值与stopExecution()的无锁预检查。

### 2.3 PlanExecution 的内部 preempt 标志

[`plan_execution.hpp` L160-L180](https://github.com/moveit/moveit2/blob/f11204b8a9b98e4ba28e564721d24a7077f5f969/moveit_ros/planning/plan_execution/include/moveit/plan_execution/plan_execution.hpp#L160-L180) 的 Preemptable 内部标志使用 `std::atomic<bool>`，PlanExecution::stop() 调用 request()（[`plan_execution.cpp` L113-L116](https://github.com/moveit/moveit2/blob/f11204b8a9b98e4ba28e564721d24a7077f5f969/moveit_ros/planning/plan_execution/src/plan_execution.cpp#L113-L116)）。这证明取消链中有一个线程安全的原子标志，但它与 MoveGroupMoveAction::preempt_requested_ 是不同对象，不能消除后者的数据竞争。

## 3. Jazzy 与 MoveIt 当前主线差异

审计时 MoveIt 默认 main 分支快照为 commit `5815c90b36ba028a42f49aa7f2364067093b21c0`（2026-11-16），其 TEM header 已将 `execution_complete_` 从 Jazzy 的普通 bool 改为 `std::atomic<bool>`（[main header L321-L328](https://github.com/moveit/moveit2/blob/5815c90b36ba028a42f49aa7f2364067093b21c0/moveit_ros/planning/trajectory_execution_manager/include/moveit/trajectory_execution_manager/trajectory_execution_manager.hpp#L321-L328)）。

但 main 分支该快照中的：
- `last_execution_status_` 仍为普通成员；
- `execution_thread_` 仍为 unique_ptr，执行线程赋值/读取仍需完整审查；
- MoveGroupMoveAction::preempt_requested_ 仍为普通bool，accepted callback仍启动 detached thread。

因此主线对 execution_complete_ 的原子化属于局部强化，不代表四组状态的整体同步问题已关闭；更不能将main分支当前实现当作Jazzy二进制的实际代码。

## 4. 风险与影响

- action取消与规划/执行worker重叠时，preempt_requested_存在数据竞争，可能产生未定义行为；PlanExecution内部atomic preempt仍可能停止底层规划/执行，但不能让独立bool的访问自动变得安全。
- TEM完成标志的无锁读取可能与外部停止路径的写入并发，影响停止/结束判断的一致性。
- last_execution_status_可能在取消线程、执行线程和状态读取者之间发生未同步读写，造成返回状态与实际结束原因不一致或触发未定义行为。
- execution_thread_ 的锁保护不完整，在 execute 与 stop 并发调用时存在unique_ptr访问竞争可能；需结合API调用约束和TSAN进一步确认。

## 5. 建议的下一步验证与修复门禁

1. 在CI临时overlay中对MoveIt Jazzy与Stäubli mock workspace使用ThreadSanitizer构建；TSAN与ASan不应混在同一测试二进制中。记录编译器、依赖、运行参数、原始报告与commit。
2. 扩展mock测试：在worker启动前、plan中、进入execute前、controller执行中和自然完成临界点分别发送cancel；增加cancel与自然完成竞争、连续goal、异常早退、auto_clear true/false及stop/execute并发场景。
3. 对TEM状态建立明确单一同步协议：execution_complete_ 与 condition_variable使用一致的mutex谓词；last_execution_status_由同一状态锁保护或在API边界返回锁内快照；execution_thread_的分配、检查、join与reset统一由execution_thread_mutex_保护，并审查锁顺序。
4. 对MoveGroupMoveAction，优先验证是否可删除重复的preempt_requested_并复用PlanExecution::Preemptable；若保留，则应改为atomic或锁保护，并为多目标/取消/自然结束定义状态机。
5. 完成TSAN与确定性回归前，不得将“mock teardown 10/10通过”扩大解释为action取消线程安全、数据竞争已清除或实机可靠性已通过。

## 6. 本轮执行边界

本轮只完成固定源码版本的静态审查和证据归档；未修改MoveIt main/Jazzy、Stäubli driver产品源码或CS9配置，未发送真实运动命令，未运行TSAN、HIL、SAT或实机测试。后续所有源代码处理须继续遵守既有授权/分支约束。
