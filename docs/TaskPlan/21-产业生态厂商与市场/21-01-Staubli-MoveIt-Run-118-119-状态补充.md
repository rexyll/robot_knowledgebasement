# 21-01｜Stäubli MoveIt teardown 生命周期状态补充（2026-11-16）

> 本文件是第21章 TaskPlan 的 Stäubli 专项状态补充，配合本目录的主 TaskPlan 使用。它不替代主 TaskPlan 的节点状态，也不改变根 TaskPlan 的全局优先级。所有结论限于 MoveIt Jazzy / ROS 2 Jazzy / Stäubli mock CI。

## 当前状态

**21-01：正在进行中。** 当前仍不具备 upstream 修复验收、CS9、HIL、SAT 或实机验收证据。

### 最新实验状态

| Run | 实验 | 结果 | 解释 |
|---|---|---|---|
| #107 | 主作用域 owner 提前释放 + TEM 显式 cleanup（A+B） | 5/5 PASS | 当前组合候选的 mock 正向对照 |
| #113 | TEM stopExecution 自然完成/取消交错的确定性回归 | 5/5 PASS（按审计记录） | 覆盖特定 missed-join 交错，不证明所有字段无数据竞争 |
| #117 | always-join CI-only 候选 | 5/5 PASS | 五轮均 join_performed=1、execution_thread_joinable=0、active_handles=0 |
| #118 | main-owner-only（A=ON、B=OFF） | **5/5 FAIL** | 每轮 mock action 完成后，在 move_group teardown 的 shared_ptr 释放路径 SIGSEGV |
| #119 | TEM-cleanup-only（A=OFF、B=ON） | **5/5 FAIL** | 每轮 TEM subscription/group/manager/node reset 记录完成后，仍在 shared_ptr 释放路径 SIGSEGV |
| #121 | K-only（A=OFF、B=OFF） | **5/5 FAIL** | 五轮 action 均 SUCCEEDED；五轮 DSO unload 后在 controller-manager NodeBase/CallbackGroup Waitable weak-list teardown SIGSEGV |

详细 GDB、lifecycle marker、DSO unload 顺序及 artifact 入口见：

- `docs/audits/2026-11-16-staubli-moveit-teardown-factorial-runs-118-119.md`
- `docs/audits/MoveIt-TEM-teardown-lifecycle-audit-2026-11-15.md`

## 本轮新增结论

1. 两个单因子实验的 rclcpp overlay、patched MoveIt 和 Stäubli mock workspace 均成功构建；失败都发生在最后的 mock 执行/teardown 回归，不是编译失败。
2. Run #118 中，主作用域 owner 提前释放与 Executor/MoveGroupExe 顺序调整单独启用，仍未阻止 controller-manager plugin DSO 与残余 Waitable/shared_ptr 生命周期冲突。
3. Run #119 中，TEM 内部显式清理按日志执行，且观测到 execution thread 不再 joinable、active handles 为 0，但缺少主作用域提前释放时仍然 SIGSEGV。
4. 对当前实验因子划分，A 或 B 单独启用均不足；保持 A+B 组合继续验证，不合并任何单因子候选。不要把该实验结论外推为已确认全部 shared_ptr 的动态类型或唯一根因。

## 后续未完成任务

- [ ] 在 A+B 组合下保留 Run #107 的 5/5 正向对照；确认测试输入、controller lifecycle 和 teardown marker 未发生非预期漂移。
- [ ] 进一步拆分 A：核实 MoveGroupContext、MoveItCpp、PSM、node 外部 shared owners 的最后释放时机，证明 capability plugin loader reset 前 TEM 析构已完成。
- [ ] 进一步拆分 B：核实 private executor / WaitSet、event subscription、callback group、controller-manager instance、controller node 与 controller-manager loader 的严格析构顺序。
- [ ] 对 active_handles_、trajectories_ 未执行/auto_clear=false/异常早退/多 controller 路径增加 teardown 断言。
- [ ] 完成 execution_complete_、last_execution_status_、execution_thread_、preempt_requested_ 的完整访问域和锁策略审查，并增加 TSAN 或等价数据竞争检测。
- [ ] 仅在明确授权范围内评估正式上游修复；当前不修改 MoveIt/rclcpp upstream、不修改 Stäubli 产品源码、不解锁 PR #1、不做真实硬件动作。

## 约束

- 当前所有通过均为 CI-only temporary overlay + mock，不是用户可部署修复。
- 不将 pal_statistics 在 Context invalid 后的 sleep 异常与 MoveGroup shared_ptr SIGSEGV 混为一谈。
- 任何单一 workflow 成功都不能替代 stock ROS Jazzy、目标机械臂、CS9、HIL 或现场安全验证。


## 2026-11-16 补充｜共同基线与实验完整性修正

重新逐 commit 核对 Run #107/#118/#119 的 workflow 后，修正此前“2×2 因子实验”的命名：

- 三项运行都保留共同背景 K：PSM scene publisher 在 Context shutdown 前停止；MoveGroupExe 声明在 MultiThreadedExecutor 之前，使 executor/WaitSet 先析构；stock signal handling 不改。
- A=ON 的精确定义是：将 main() 局部 `planning_scene_monitor`、`moveit_cpp`、`nh` 三个 shared owner 改为可 reset，并在 `rclcpp::shutdown()` 后按 PSM → MoveItCpp → Node 的顺序提前 reset。
- B=ON 的精确定义是：TEM 显式 reset event subscription、parameter callback、event callback group、private executor、controller-manager instance 和 controller-manager node，确保它们在 controller-manager loader 自动析构/卸载前释放。
- #118 = K+A（B gate OFF），5/5 FAIL；#119 = K+B（A resets OFF），5/5 FAIL；#107 = K+A+B，5/5 PASS。

历史 Run #73 不包含与这三项相同的 K 背景，因此不能作为严格的 K+A=OFF+B=OFF 对照。当前证据应称为**共同基线下的三组单因子消融/组合对照**，而不是完整 2×2。尚缺 K-only（A=OFF/B=OFF）对照。

### 更新后的下一步

- [ ] 先补齐 K-only mock CI 对照，保持 PSM stop、MoveGroupExe/executor 作用域顺序和测试输入不变，关闭 A、B 两组 reset。
- [ ] K-only 完成后，再固定 B=ON，分别隔离 A 中 PSM、MoveItCpp、Node 三个 reset 的必要性。
- [ ] 随后固定 A=ON，逐项隔离 B 中 callback group / subscription、controller-manager node / instance、private executor / WaitSet 的释放边界。
- [ ] 每轮固定 Stäubli source pin、mock plan-and-execute 输入、重复次数、GDB/LD_DEBUG 和 strict process exit assertion；保留 Run #107 A+B 5/5 正向对照。

**详细更正与实验设计：** `docs/audits/2026-11-16-staubli-moveit-teardown-factorial-runs-118-119.md`。本补充只更新知识库审计与计划，不触发 driver workflow，不创建实验分支，不修改上游或产品源码。


## 2026-11-16 补充｜K-only 对照已触发，结果待验

为补齐共同背景 K 下 A=OFF/B=OFF 的对照，已复用已有分支 `experiment/moveit-main-owner-lifetime-only`，只修改临时 CI workflow 文件，不新建分支、不改 driver main、不触碰 MoveIt/rclcpp/Stäubli 产品源码。

- workflow commit：`739afbbe2722ebd494326272ec298d896ab193c4`
- Actions：[Run #43789238751](https://github.com/rexyll/staubli_driver_ros2_from_org/actions/runs/43789238751)
- 实验配置：K=ON、A=OFF、B=OFF。
- 已静态检查 workflow 内容：A 的三个外部 owner reset 全部不存在；B 的 TEM cleanup gate 关闭；共同的 PSM publisher stop 与 MoveGroupExe-before-executor 声明顺序保留。

首次状态查询时 job 处于运行中、容器初始化尚未结束，尚无可下载的 job logs/artifact。**该运行暂不记 PASS/FAIL，也不改变 A+B 当前是唯一已通过候选的判断。**

后续根据同一 mock 输入和 strict teardown 的结果更新本节点；在 Run #43789238751 完成前，不进一步宣称完整 2×2 结论。


## 2026-11-16 补充｜rclcpp callback group 实际 owner 语义

对照 ROS 2 rclcpp Jazzy commit `35b821a9fb1f937bfbd9c741b7e3353e101d9593` 后，确认：

- `NodeBase` 对 default callback group 持有强引用 `default_callback_group_`；对其余 callback groups 只在 `callback_groups_` 中保存 WeakPtr。
- `CallbackGroup` 的 `waitable_ptrs_` 同样是 WeakPtr 列表；`remove_waitable()` 先 lock weak_ptr，expired 条目不能通过当前匹配分支移除；CallbackGroup 析构时还会触发 notify guard condition。
- 因而 TEM 的非默认 event callback group 必须由明确的强 owner 持有，并在 plugin loader 卸载前释放；controller-manager Node 的 default group 则需要在 controller-manager node reset 时随 NodeBase 一起析构。

来源：
- [rclcpp node_base.hpp](https://github.com/ros2/rclcpp/blob/35b821a9fb1f937bfbd9c741b7e3353e101d9593/rclcpp/include/rclcpp/node_interfaces/node_base.hpp#L154-L160)
- [rclcpp callback_group.hpp](https://github.com/ros2/rclcpp/blob/35b821a9fb1f937bfbd9c741b7e3353e101d9593/rclcpp/include/rclcpp/callback_group.hpp#L297-L312)
- [rclcpp callback_group.cpp](https://github.com/ros2/rclcpp/blob/35b821a9fb1f937bfbd9c741b7e3353e101d9593/rclcpp/src/rclcpp/callback_group.cpp#L204-L226)

后续需要在 CI-only overlay 中加入 CallbackGroup、NodeBase、private executor/WaitSet 和 DSO unload 的析构 marker。只记录 `reset()` 调用不够，必须确认对象的最后一个 shared owner 已释放、真实析构完成。


## 2026-11-16 补充｜K-only 完成：完整 2×2 矩阵与 DSO 析构顺序

K-only [Actions Run #121 / ID #43789238751](https://github.com/rexyll/staubli_driver_ros2_from_org/actions/runs/43789238751) 已完成，workflow commit `739afbbe2722ebd494326272ec298d896ab193c4`，artifact ID `14191994262`。构建成功；五轮 mock controller 都报告 `Goal reached, success!`，TEM 都报告 `Completed trajectory execution with status SUCCEEDED`；五轮均在 teardown SIGSEGV，`failures=5/5`。

完整矩阵（共同背景 K 固定）现在为：

| Run | A | B | 结果 |
|---|---:|---:|---|
| #121 K-only | OFF | OFF | **5/5 FAIL** |
| #118 K+A | ON | OFF | **5/5 FAIL** |
| #119 K+B | OFF | ON | **5/5 FAIL** |
| #107 K+A+B | ON | ON | **5/5 PASS** |

当前四格在固定输入下表明 A/B 任一单独处理都不充分，只有联合处理通过；不据五轮确定性重复估计统计学主效应或置信区间。

### 根因链收窄

K-only 五轮均先卸载 `/opt/ros/jazzy/lib/libmoveit_simple_controller_manager.so`（LD_DEBUG `calling fini` / `destroying link map`），随后才发生 private executor 清理；最后在 `CallbackGroup::~CallbackGroup()` 析构 `vector<weak_ptr<rclcpp::Waitable>>` 时触发 SIGSEGV。GDB 调用栈经过 `NodeBase::~NodeBase()`、`rclcpp::Node::~Node()`、`TrajectoryExecutionManager::~TrajectoryExecutionManager()` 和 `MoveItCpp::~MoveItCpp()`。

MoveIt Jazzy `trajectory_execution_manager.hpp` 的成员声明顺序把 `controller_mgr_node_` / `private_executor_` 放在 `controller_manager_loader_` 之前，而 `controller_manager_` 放在 loader 后面；逆序析构先销毁 manager instance，再卸载 loader/DSO，最后才销毁 earlier-declared executor、subscription 和 controller node。因此源码顺序与日志中“插件 DSO 先卸载、NodeBase/CallbackGroup 后析构”的顺序一致。**最强根因判断是 TEM stock member teardown 次序允许 controller-manager DSO 早于其 NodeBase/CallbackGroup/Waitable 弱引用清理而卸载。** 具体 Waitable 动态类型/控制块 destroy 回调所属 DSO仍未 RTTI 级确认。

### 下一步

- [ ] 在 A+B 正向对照增加真实 destructor marker：manager instance、private executor/WaitSet、controller node / NodeBase / default callback group、loader reset/DSO unload；记录最后 owner `use_count`。
- [ ] 固定 A=ON，先验证 B 中“停止/join executor → remove node → executor/WaitSet 释放 → manager instance 释放 → controller node/NodeBase 释放 → loader unload”的核心顺序是否是最小充分集合。
- [ ] 再单项隔离 event subscription、parameter callback、event callback group。
- [ ] 固定 B=ON 后逐一隔离 A 的 PSM、MoveItCpp、main Node reset。
- [ ] execution state 字段的锁域与 TSAN 仍未完成；不修改 upstream/产品源码，不连接 CS9、不做真实机器人动作，不宣称 HIL/SAT/实机验收。

全局最高优先级仍是根 TaskPlan 00-01；第21章 21-01 仍为进行中。


## 2026-11-16 补充｜A+B 实际析构诊断已触发（Run #122）

MoveIt Jazzy TEM initialize() 的实际构造顺序已核实：先创建 controller-manager ClassLoader（trajectory_execution_manager.cpp L114–117），再创建 controller_mgr_node_（L164–171），通过 createUniqueInstance() 装载 plugin 并调用 plugin initialize(controller_mgr_node_)（L177–178），随后创建 private_executor_、add_node(controller_mgr_node_) 并启动 spin thread（L179–183）。这证明 plugin manager 的 callback/waitable 资源依附 controller node 的 NodeBase/default callback group，且由 private executor 驱动。

为直接验证 K-only 的 DSO/NodeBase 析构顺序，已在 A+B 正向候选追加 CI-only 诊断：NodeBase dtor 入口/主体结束标记；CallbackGroup 中每条 Waitable weak_ptr 的槽位、expired、use_count 与释放前后标记；controller_mgr_node_ reset 前 use_count；以及 node reset 后显式释放 controller_manager_loader_。

- workflow commit：c81546100ed5a91110e57ca56488f7d6911fa31f
- [Actions Run #122](https://github.com/rexyll/staubli_driver_ros2_from_org/actions/runs/43791758924)
- 当前状态：容器初始化已完成，ROS Jazzy setup 仍在执行；rclcpp 编译、MoveIt 构建、mock teardown 尚未开始。
- 逐项 weak_ptr reset 属 CI-only 诊断插桩，可能轻微改变 destructor 内部时序；必须与原始 A+B Run #107 5/5 PASS 对照解释。

尚未确认具体 Waitable 动态类型或 control-block destroy/deallocate 函数归属；本轮不作超出日志证据的推断。