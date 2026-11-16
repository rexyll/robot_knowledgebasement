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
| #122 | A+B lifecycle-marker 正向诊断 | **5/5 PASS** | 五轮 mock execution 成功；controller node NodeBase/default CallbackGroup expired weak Waitables 清理后才卸载 controller-manager DSO；未取得 control-block vtable 地址归属 |

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

## 2026-11-16 补充｜rclcpp_action expired Waitable weak entry 根因链

源码进一步确认 moveit_simple_controller_manager 的 FollowJointTrajectory handle 在 action_based_controller_handle.hpp L84–89 调用 rclcpp_action::create_client<T>(node, action_name)，不显式传 callback group；ClientBase 是 rclcpp::Waitable。rclcpp_action/create_client.hpp 为其配置自定义 shared_ptr deleter：最后一个强引用释放时，deleter 先构造 no-op fake_shared_ptr，再调用 NodeWaitablesInterface::remove_waitable，然后 delete Client。

NodeWaitables::add_waitable 在 group=null 时选择 NodeBase default callback group，并将 Waitable weak_ptr 加入 group。销毁时原 action_client strong count 已经归零，CallbackGroup::remove_waitable 对存储的原 weak_ptr 调用 lock() 会失败；该函数只有在 lock 成功且 raw pointer 相等时才 erase，没有清理 expired entry 的分支。因此 plugin Client 的 deleter 会留下 expired weak_ptr。注意 add_waitable() 会在后续添加新的 Waitable 时顺便删除当时已过期的条目；但 TEM 的这些 action clients 在初始化阶段创建、在 teardown 阶段集中销毁，销毁阶段不再新增 Waitable，所以最终 expired entries 会留到 controller node 的 default CallbackGroup 清理 waitable_ptrs_ 时才释放最后 weak count。

源码链接：
- https://github.com/moveit/moveit2/blob/jazzy/moveit_plugins/moveit_simple_controller_manager/include/moveit_simple_controller_manager/action_based_controller_handle.hpp#L84-L90
- https://github.com/ros2/rclcpp/blob/35b821a9fb1f937bfbd9c741b7e3353e101d9593/rclcpp_action/include/rclcpp_action/create_client.hpp#L53-L92
- https://github.com/ros2/rclcpp/blob/35b821a9fb1f937bfbd9c741b7e3353e101d9593/rclcpp/src/rclcpp/node_interfaces/node_waitables.cpp#L29-L65
- https://github.com/ros2/rclcpp/blob/35b821a9fb1f937bfbd9c741b7e3353e101d9593/rclcpp/src/rclcpp/callback_group.cpp#L218-L228

expired weak entry 留存机制已由源码调用顺序确认；其 shared control block 的析构/释放函数是否位于 libmoveit_simple_controller_manager.so，仍须等 Run #122 GDB 打印 control-block vtable 地址并对照映射验证。

## 2026-11-16 补充｜plugin manager handle 析构与 expired weak entry 连接

MoveItSimpleControllerManager 的析构函数是 defaulted；其 node_ 成员在源文件 L328，controllers_ map 在 L329，因此 controllers_ map 先析构。map 中的 FollowJointTrajectory handle 持有 Action Client，handle 的 node_ 在 action_based_controller_handle.hpp L189，controller_action_client_ 在 L270；Action Client 在 L88 用 rclcpp_action::create_client 创建。

所以 controller manager plugin dtor 会先销毁 handle 和 Action Client。此时 TEM 自己仍持有 controller_mgr_node_，deleter 的 weak_node.lock() 成功，继而尝试 remove_waitable；但原 Waitable weak_ptr 已因 strong count 归零而 lock 失败，expired entry 留在默认 CallbackGroup。随后 controller_manager_ owner 释放、ClassLoader unload DSO；TEM 更后面才释放 controller_mgr_node_，触发 CallbackGroup 最后的 weak release。

这把 plugin dtor → action client custom deleter → expired weak entry → TEM loader unload → NodeBase/CallbackGroup cleanup 连接成一条连贯生命周期链。剩余确认项是 Run #122 中 control-block vtable / destroy 地址的实际映射归属。

## 2026-11-16 补充｜Run #122 完成与 K-only pruning 反证运行

Run #122（[Actions](https://github.com/rexyll/staubli_driver_ros2_from_org/actions/runs/43791758924)，commit `c81546100ed5a91110e57ca56488f7d6911fa31f`）已完成：

- 5/5 mock plan-and-execute 均成功，5/5 teardown 均通过；workflow test summary 为 7 tests、0 errors、0 failures。
- 五轮日志均显示：TEM 执行 `controller_mgr_node_.reset()` 后，目标 NodeBase 的 default CallbackGroup 均有 `waitables=5`；每轮这五条 weak Waitable 均为 `expired=1, use_count=0`，并逐项释放完成后才触发 `controller_manager_loader_.reset()` 与 `libmoveit_simple_controller_manager.so` 的 `fini` / link-map destruction。
- 这验证 A+B 候选把 controller node/group 清理移动到 plugin DSO unload 之前；但 Run #122 没有输出 control-block vtable、`_M_destroy` 或 deallocate 地址，不能据此断言最终释放函数位于该 DSO。

### 当前反证实验

K-only + expired-entry pruning 已在原有隔离分支 `experiment/moveit-main-owner-lifetime-only` 上启动，未创建新分支：

| Run | commit | 状态 | 说明 |
|---|---|---|---|
| #123 | `d86c0078c06ed2029f7581a3087f4b476dc8da9a` | 配置无效，不计结果 | 内嵌 Python 补丁字符串 SyntaxError，未进入编译或 mock 测试 |
| #124 | `e982788ac7446a8ad5f8bf6ebb2a4e814b2a7763` | 配置失败，不计反证 | rclcpp overlay build 成功；MoveIt step 因跨 Actions step 的 callback_group_source 未定义触发 NameError，未进入 MoveIt build/mock test |
| #125 | `3f85d2a9063083e895a3dee2f67f7c353a09f840` | 配置失败，不计反证 | 同一跨步骤 NameError；归档日志但未进入 MoveIt build/mock test |
| #126 | `7d0aa0d6b571323d85a181d5ec7d24371288fed9` | 无效空跑，不计反证 | rclcpp/MoveIt/mock workspace build 均成功；test step 未进入 `/tmp/staubli_ws`，五轮均 0 packages/0 tests/0 pruning |
| #127 | `2c578fa670b0d5c9bf845c53591cbc334f952438` | 运行中 | 增加 `cd /tmp/staubli_ws`、`ros2 pkg prefix` 与 `colcon list` 预检后重跑 K-only pruning |

核心处理只发生在临时 rclcpp overlay 的 `CallbackGroup::remove_waitable()`：当遍历到的 weak Waitable 无法 `lock()` 时，erase 该 expired entry，再继续遍历并按原逻辑比较 live target。每轮必须观测到 pruning marker；未命中该路径不视为有效反证。

### 下一步判定

- [x] #124/#125 由于 workflow 跨 step Python 局部变量 NameError 在 MoveIt patch step 退出，未进入 mock test，不计功能性结果。
- [x] #126 的 MoveIt 与 mock workspace build 成功，但测试 step 未进入 `/tmp/staubli_ws`，五轮均 0 tests/0 pruning，判定 no-op，不计反证。
- [ ] 对 #127 检查 workspace/package preflight、5轮 action 结果、teardown 结果、每轮 pruning marker，以及 group=%p 是否匹配目标 NodeBase default group。
- [ ] 若有效 pruning 下 K-only 5/5 通过，追加更高重复数并验证 live Waitable 条目未误删；结论限 mock CI。
- [ ] 若仍 5/5 失败，拒绝把 pruning 单点当作充分修复，回到 control-block/DSO/WaitSet 生命周期定位。
- [ ] 单独追踪 control-block destroy/deallocate 地址映射；该问题尚未完成。


## 2026-11-16 补充｜Run #126 工作目录空跑与 #127 修正

Run #126 的 rclcpp overlay、patched MoveIt build（7 packages）和 Stäubli mock workspace build（5 packages）均成功；其中 package `staubli_moveit_config` 已在 build 日志中成功完成。但 GitHub Actions 每个 step 使用独立 shell，test step 未重新执行 `cd /tmp/staubli_ws`，所以 colcon 从默认 runner 目录扫描不到 package。五轮均为 `0 packages / 0 tests / 0 pruning`，属于 no-op，不是 teardown 成败证据。

[Run #127](https://github.com/rexyll/staubli_driver_ros2_from_org/actions/runs/43798751700) 已在原有实验分支重跑。测试步骤现在先切换到 `/tmp/staubli_ws`，再通过 `ros2 pkg prefix staubli_moveit_config` 与 `colcon list --base-paths src` 确认目标包可见；任一预检失败则停止测试而不是空跑。

- [ ] 核验 #127 package preflight 与五轮真实测试结果。
- [ ] 逐轮核对 mock action、teardown exit status、pruning marker 数量和 group 地址。
- [ ] 即使 K-only pruning 通过，也仅形成 mock CI 单点证据；继续核验 live Waitables 未误删及 control-block destroy/deallocate 地址归属。


## 2026-11-16 补充｜Run #127 pruning 单点反证与 A+K+B-core 继续验证

Run #127（[Actions](https://github.com/rexyll/staubli_driver_ros2_from_org/actions/runs/43798751700)）已完成有效测试：工作区/package preflight通过，五轮mock plan-and-execute全部SUCCEEDED；CallbackGroup expired Waitable pruning每轮18次、总计90次，但五轮均在TEM private Executor的WaitSet/DynamicStorage::WeakWaitableEntry弱引用释放阶段SIGSEGV（exit -11）。但group=%p尚未与MoveIt内部controller_mgr_node_的NodeBase/default CallbackGroup建立映射，因此不能断言目标组pruning已经命中，更不能把它作为目标组pruning的有效失败反证。

关键源码区分：CallbackGroup::waitable_ptrs_与Executor DynamicStorage::waitables_是独立weak-reference容器；后者的WeakWaitableEntry还同时持有`weak_ptr<Waitable>`与`weak_ptr<void> associated_entity`。Run #127只改前者，而栈在WaitSet/DynamicStorage析构的`std::weak_ptr::_M_weak_release/_M_destroy`中崩溃；具体是associated entity还是Waitable的弱引用最后释放触发无效访问仍待分辨。

下一项不再使用CallbackGroup pruning作为功能处理，而在原隔离分支固定A=ON、K=ON，单独打开B-core：join executor thread、remove controller node、reset private Executor/WaitSet、reset controller manager、reset controller node、最后reset loader；暂不reset event subscription、parameter callback或event callback group。临时overlay为WaitSet WeakWaitableEntry的两条weak reference分别增加析构/释放marker。

- [x] Run #127每轮真实执行、五轮plan-and-execute成功、五轮teardown fail的证据归档。
- [x] callback group和waitset各自weak-reference vector的职责边界已补充说明。
- [x] 追加检查#127 group=%p：marker来自多个move_group组和ros2_control组，尚未通过NodeWaitables的node-name/NodeBase地址映射到controller_mgr_node_，目标组覆盖未知。
- [ ] Run #128/#129验证A+K+B-core的五轮mock action及WaitSet析构日志；若仍需判断CallbackGroup pruning，另加NodeWaitables node-FQN/NodeBase/group/Waitable地址映射。
- [ ] 如B-core通过，继续独立拆分event subscription/callback/parameter callback及A的PSM/MoveItCpp/main Node owner；如失败，按具体weak release marker继续定位。

所有结论限CI temporary overlay/mock；不修改upstream/产品源码，不连接CS9、不发送真实运动指令、不宣称HIL/SAT/实机验收。全局主优先级仍为00-01。


### Run #127地址映射核查更正

pruning marker每轮18条，但marker不只来自一个CallbackGroup。原始日志显示`move_group`进程存在多个不同group地址，`ros2_control_node`进程的某一组地址可与其NodeBase default group对应；现有NodeBase析构marker没有覆盖MoveIt内部的`controller_mgr_node_`，因为它在TEM private executor/WaitSet崩溃前尚未析构。因此Run #127不能确认目标controller-manager group是否实际被pruning，目标组覆盖状态更正为**未证实**。如需重新做该单点反证，必须给`NodeWaitables::add_waitable/remove_waitable`增加CI-only node FQN、NodeBase、group和Waitable指针关联marker。
