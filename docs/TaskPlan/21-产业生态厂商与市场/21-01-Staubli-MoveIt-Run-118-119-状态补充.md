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
| #132 | stock rclcpp 无插桩 A+K+B-core（10轮） | **10/10 PASS** | 每轮一次mock plan-and-execute成功、7项launch assertions通过、B-core顺序与进程退出码均通过；CI-only正向基线 |
| #134 | A-PSM-retained + K + B-core（10轮） | **10/10 SIGSEGV** | PSM弱引用探针每轮use_count=1；MoveGroupExe capability/context/plugin loader清理完成后，保留的main() PSM owner才释放，随后PSM/Node teardown段错误。每轮执行次数统计显示2是colcon test-result verbose重复采集误报，原始测试流实际每轮仅一次mock执行成功 |
| #135 | PSM析构阶段marker + 显式reset边界 + 独立test-result日志（10轮） | **10/10 SIGSEGV** | 每轮mock execution成功；PSM析构函数体到BODY-END，末尾node_use=2/pnode_use=1，PSM reset END无运行时marker；GDB栈定位到隐式pnode_ shared_ptr释放→Node→NodeBase→CallbackGroup→weak_ptr<ServiceBase> _M_destroy。尚未证明control block manager/vtable归属已卸载DSO |
| #136 | PSM teardown链Node/NodeBase/CallbackGroup + GDB DSO/memory-map诊断（Node身份待定） | **10/10 SIGSEGV；Node身份未确认** | 10轮均在CallbackGroup析构weak_ptr<ServiceBase>时SIGSEGV；fault PC位于仍映射的librclcpp，间接调用所用vptr不在进程映射中；librclcpp、libmoveit_planning_scene_monitor及MoveGroup capability相关DSO仍映射。尚不能区分已卸载的其他DSO与control block/vptr内存破坏；另修正test-result汇总解析路径 |
| #137 | weak ServiceBase control block/vptr与DSO unload逐项诊断 | **10/10 SIGSEGV；GDB脚本第22行中断** | mock构建成功；10轮均复现teardown SIGSEGV。每轮Summary 7 tests、0 errors、2 failures。GDB对未映射$rax执行x/8gx后中止，未运行service_ptrs_ size/逐项weak检查；不能据此识别服务或Node |
| #138 | GDB安全取证与Node/service/group身份关联 | **环境阶段失败，不计代码结果** | ROS setup成功；第4步rosdep update请求rosdistro/base.yaml时Connection reset by peer；后续构建/测试全部跳过 |
| #139 | Run137 GDB修复 + TypeDescription Node归属核验 + rosdep retry | **执行中** | rosdep update添加5次有限重试（每次间隔8秒，最终fail-closed）；当前容器初始化/ROS setup尚未完成 |
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

Run #127（[Actions](https://github.com/rexyll/staubli_driver_ros2_from_org/actions/runs/43798751700)）已完成有效测试：工作区/package preflight通过，五轮mock plan-and-execute全部SUCCEEDED；CallbackGroup expired Waitable pruning每轮在原始日志中出现18条（`colcon test-result --verbose`重复打印同一输出），去重后每轮9条不同记录、五轮45条，但五轮均在TEM private Executor的WaitSet/DynamicStorage::WeakWaitableEntry弱引用释放阶段SIGSEGV（exit -11）。但group=%p尚未与MoveIt内部controller_mgr_node_的NodeBase/default CallbackGroup建立映射，因此不能断言目标组pruning已经命中，更不能把它作为目标组pruning的有效失败反证。

关键源码区分：CallbackGroup::waitable_ptrs_与Executor DynamicStorage::waitables_是独立weak-reference容器；后者的WeakWaitableEntry还同时持有`weak_ptr<Waitable>`与`weak_ptr<void> associated_entity`。Run #127只改前者，而栈在WaitSet/DynamicStorage析构的`std::weak_ptr::_M_weak_release/_M_destroy`中崩溃；具体是associated entity还是Waitable的弱引用最后释放触发无效访问仍待分辨。

下一项不再使用CallbackGroup pruning作为功能处理，而在原隔离分支固定A=ON、K=ON，单独打开B-core：join executor thread、remove controller node、reset private Executor/WaitSet、reset controller manager、reset controller node、最后reset loader；暂不reset event subscription、parameter callback或event callback group。临时overlay为WaitSet WeakWaitableEntry的两条weak reference分别增加析构/释放marker。

- [x] Run #127每轮真实执行、五轮plan-and-execute成功、五轮teardown fail的证据归档。
- [x] callback group和waitset各自weak-reference vector的职责边界已补充说明。
- [x] 追加检查#127 group=%p：marker来自多个move_group组和ros2_control组，尚未通过NodeWaitables的node-name/NodeBase地址映射到controller_mgr_node_，目标组覆盖未知。
- [x] #128/#129均因MoveIt patch step中的Python字符串SyntaxError退出，未进入功能测试，不计入B-core结果。
- [ ] Run #130（commit `9d9f33b8281fdf7d412153100666318470d0b9af`）已修正TEM日志字符串转义并重新运行；核验A+K+B-core五轮mock action及WaitSet析构日志；若仍需判断CallbackGroup pruning，另加NodeWaitables node-FQN/NodeBase/group/Waitable地址映射。
- [ ] 如B-core通过，继续独立拆分event subscription/callback/parameter callback及A的PSM/MoveItCpp/main Node owner；如失败，按具体weak release marker继续定位。

所有结论限CI temporary overlay/mock；不修改upstream/产品源码，不连接CS9、不发送真实运动指令、不宣称HIL/SAT/实机验收。全局主优先级仍为00-01。


### Run #127地址映射核查更正

pruning marker每轮原始日志出现18条，但其中有9条是`colcon test-result --verbose`重复打印；去重后每轮9条不同记录。marker不只来自一个CallbackGroup。原始日志显示`move_group`进程存在多个不同group地址，`ros2_control_node`进程的某一组地址可与其NodeBase default group对应；现有NodeBase析构marker没有覆盖MoveIt内部的`controller_mgr_node_`，因为它在TEM private executor/WaitSet崩溃前尚未析构。因此Run #127不能确认目标controller-manager group是否实际被pruning，目标组覆盖状态更正为**未证实**。如需重新做该单点反证，必须给`NodeWaitables::add_waitable/remove_waitable`增加CI-only node FQN、NodeBase、group和Waitable指针关联marker。


### Run #128/#129 workflow脚本问题

#128在rclcpp overlay build后，MoveIt patch step的Python `tem_replacement`字符串因双重转义导致`SyntaxError: '(' was never closed`；#129只改了旧日志文字，未修复转义，故重复失败。两轮都未运行MoveIt build或Stäubli mock test，不计功能结果。#130已把C++日志字面量改为Python单层转义，并更新step名称，当前执行中。


### Run #127 pruning marker重复输出去重

Run #127每轮exit summary报告`expired_entries_pruned=18`，但workflow先将`colcon test`的完整输出写入日志，随后`colcon test-result --verbose`又打印同一份launch-test output。逐轮按process/group/target/remaining去重后，18条日志出现对应9条不同marker；五轮共45条不同记录，而非90次实际清理。原始workflow汇总数是日志行数，后续不得按实际pruning操作次数引用。


## 2026-11-16 补充｜Run #130 A+K+B-core 5/5 正向候选

Run #130（[Actions](https://github.com/rexyll/staubli_driver_ros2_from_org/actions/runs/43803660660)，commit `9d9f33b8281fdf7d412153100666318470d0b9af`）的rclcpp overlay、patched MoveIt和Stäubli mock workspace均构建成功；test package preflight通过。A=ON、K固定、B-core=ON五轮均完成mock plan-and-execute（5/5 SUCCEEDED），每轮launch test汇总7 tests、0 errors、0 failures、0 skipped，teardown/顺序检查均exit 0，五轮无SIGSEGV。

B-core日志顺序为private executor reset BEGIN → remove controller node → private executor reset END → controller manager reset → controller node reset（开始前use_count=1）→ controller-manager loader reset。每轮private executor reset窗口中出现8次WaitSet WeakWaitableEntry析构入口及8组associated_entity/waitable释放END marker；每轮Waitable为5个expired/use_count=0及3个live entries，associated_entity均expired/use_count=0。

Artifact ID `14198705205`，SHA-256 `de8eea001b5b3718e5bfd39bb5d94439faa2a7a43bf10815a6c6aef89d8a5be7`。该结果是A+K+B-core正向候选，但由于本轮临时rclcpp overlay插入了析构探针，仍需排除探针时序效应。

### 下一步：无插桩10轮复核

- [x] 原隔离分支已提交`4154ebdd00d04c98d510aedb3fd1e15ed3e18823`，rclcpp源树恢复stock，构建前执行git diff与marker扫描；A+K+B-core处理不变。
- [ ] Run #131做10轮真实mock execution/launch test，核对每轮TEM清理顺序及exit code。
- [ ] 若无插桩10/10通过，再固定B-core，按单变量拆分A中的PSM owner、MoveItCpp owner、main Node owner，并进一步确认event/parameter callback资源无需额外reset的条件。

结论仍限CI temporary MoveIt patch与Stäubli mock，不等同upstream修复、产品验证、HIL/SAT或实机验收；全局优先级仍为00-01。


### A 因子 shared-owner 链边界

源码复核发现，A中的`planning_scene_monitor.reset()`、`moveit_cpp.reset()`和`nh.reset()`只释放main()局部shared owner，不能直接视为对应对象在该行析构。MoveGroupExe持有MoveGroupContext；MoveGroupContext又持有MoveItCpp、PSM及TEM；MoveItCpp还持有Node、PSM及TEM。最终析构要沿MoveGroupExe capabilities/context → MoveGroupContext → MoveItCpp成员逆序销毁链追踪。

后续拆分A必须使用use_count/weak_ptr expiration及真实dtor marker确认干预了哪个对象的最后strong owner；若只删除某一条main-local reset但内部owner仍存在，则不构成对应对象析构路径的有效单变量实验。


### Run #130诊断插桩语义风险

给`DynamicStorage::WeakWaitableEntry`添加用户声明析构函数会抑制隐式move constructor；copy仍可用时，`std::vector`重分配可能改变WeakWaitableEntry的move/copy选择，影响weak reference control block的计数和释放时序。虽然探针显式按associated entity再Waitable顺序reset，与成员默认逆序析构一致，仍不能排除该特殊成员函数副作用。Run #131已恢复stock rclcpp source并做10轮复核，以判断Run #130的5/5是否独立于插桩。



## 2026-11-16补充｜Run #131/#132 无插桩复核与 A-PSM-retained 单变量实验

### Run #131 workflow校验失败（不计功能结果）

[Run #131](https://github.com/rexyll/staubli_driver_ros2_from_org/actions/runs/43808189052) 的 stock rclcpp clone/build 和无插桩检查成功，但第6步最终静态校验错误要求 stock dynamic_storage.hpp 含有Run #130诊断overlay专用的 WaitSet WeakWaitableEntry dtor BEGIN marker；MoveIt构建、mock工作区构建和10轮测试步骤均跳过。因此#131是workflow校验配置失败，不计功能PASS/FAIL。

### Run #132 stock rclcpp 无插桩 10/10 通过

[Run #132](https://github.com/rexyll/staubli_driver_ros2_from_org/actions/runs/43812432706)，workflow commit 4d58b7e6d3b83363d6e595400a1bb1a5e1ea6a72：

- stock ROS 2 Jazzy rclcpp overlay构建成功；git diff --exit-code通过，诊断marker扫描确认无Executor、CallbackGroup、NodeBase、DynamicStorage插桩。
- patched MoveIt、Stäubli mock workspace构建和package preflight全部通过。
- 固定A=ON、K背景、B-core=ON；10/10轮均执行真实mock plan-and-execute，日志为 Completed trajectory execution with status SUCCEEDED。
- 每轮launch test均运行1个test runner，summary为7 tests、0 errors、0 failures、0 skipped。
- 每轮B-core清理顺序均为private executor thread join → remove controller node → private executor/WaitSet reset → controller manager reset → controller node reset（reset BEGIN前use_count=1）→ loader reset。
- 每轮colcon_test=0、test_result=0、lifecycle_order=0；总计failures=0/10，无SIGSEGV。
- Artifact 14201681819，SHA-256 1bd5c27cbf3803dc8565d24b73c06b7b9b99edda64874b57dc42db0c3664cb0e。

**结论：** A+K+B-core的正向结果不依赖Run #130的rclcpp析构探针，已达到无插桩mock CI 10/10候选通过。仅代表临时MoveIt patch + stock rclcpp + Stäubli mock测试，不代表upstream合并、产品验证或HIL/SAT/实机验收。

### Run #133 workflow YAML 配置失败（不计功能结果）

[Run #133](https://github.com/rexyll/staubli_driver_ros2_from_org/actions/runs/43816146303) 触发后立即失败且GitHub Actions返回0个job。检查workflow发现新加的多行Python字符串有几行缩进越过YAML run块边界，导致workflow定义无法正常解析；不是C++编译或teardown失败。另发现weak-probe生成字符串中的换行转义多了一层反斜杠。

### Run #134 修复后重跑：A-PSM-retained

已在原实验分支 experiment/moveit-main-owner-lifetime-only 修复上述问题，commit 5abf808424049dec78e2dc6247f453af59be0e29：

- Python探针改为每个物理行满足YAML缩进要求的相邻字符串拼接。
- 修正psm_anchor插入弱引用声明时的换行转义。
- 功能处理固定K和B-core，只改变A中的一项：不调用main()局部的 planning_scene_monitor.reset()，保留 moveit_cpp.reset() 与 nh.reset()。
- planning_scene_monitor保持const shared_ptr；额外创建的weak_ptr不增加strong owner，并在MoveGroupExe/executor内层作用域结束后检查expired()与use_count()。每轮必须出现恰好一个“PSM retained after MoveGroupExe/executor scope” marker。
- 10轮仍逐轮执行真实mock动作、7项launch assertions、B-core清理顺序和进程退出码核验。

- [Run #134](https://github.com/rexyll/staubli_driver_ros2_from_org/actions/runs/43816245159) 已完成容器初始化、ROS Jazzy环境准备、stock rclcpp无插桩构建、MoveIt patch静态校验和MoveIt依赖安装；最新步骤为 patched move_group 构建中。Stäubli mock工作区构建和10轮测试尚未开始。

**下一验收门：** 若10/10均通过，说明在MoveGroupExe/executor作用域退出前保留main()的PSM强引用不会破坏当前mock teardown，并且可由weak probe证明PSM在该作用域后仍存活；若失败，区分失败发生在mock动作还是进程退出阶段，再判断该main-local owner提前释放是否必要。随后再单独测试MoveItCpp与main Node owner，不一次改变多个变量。

所有结果仍限CI临时MoveIt patch + stock rclcpp + Stäubli mock；不修改上游或产品源码、不连接CS9、不发送真实运动命令、不宣称HIL/SAT/实机验收。


## 2026-11-16补充｜MoveIt Jazzy 执行状态与 action cancel 并发静态审计

新增审计报告：[MoveIt Jazzy 执行状态与取消路径线程安全静态审计](../../audits/2026-11-16-moveit-jazzy-execution-state-thread-safety-audit.md)。本轮固定源码基线为 MoveIt Jazzy `f11204b8a9b98e4ba28e564721d24a7077f5f969`，同时只读比较 MoveIt `main` 快照 `5815c90b36ba028a42f49aa7f2364067093b21c0`。

静态发现：

- `MoveGroupMoveAction::preempt_requested_` 在 Jazzy 中是普通 `bool`；action cancel callback写入，独立 detached worker读取/清零，未见共享mutex或atomic保护。这是本轮最明确的并发风险候选。
- `TrajectoryExecutionManager::execution_complete_` 在Jazzy仍是普通bool；`stopExecution()`的外层读取未持锁，worker与executePart也有不在同一锁域内的访问。
- `last_execution_status_` 是普通成员；stop路径有锁内写入，但执行线程其他状态写入和公开getter不统一使用同一锁。
- `execution_thread_` 是unique_ptr；join/reset有mutex保护，但execute()分配赋值未使用同一mutex，且stop路径有加锁前的指针判断，需验证API并发调用约束。
- MoveIt main已将 `execution_complete_` 改为 `std::atomic<bool>`；但last status、thread owner及Action preempt bool仍保留，因此不能把main分支局部改动套用到Jazzy，也不能认为整体线程安全已关闭。

**证据边界：** 这是固定源码版本的静态访问路径审计，不是TSAN报告或运行时复现；本轮没有修改MoveIt upstream/Jazzy或Stäubli产品源码。后续需在mock CI中增加TSAN，并对cancel与自然完成竞争、worker启动前取消、planning阶段取消、execute阶段取消、连续goal、异常早退与auto_clear分支做确定性测试。审计状态保持“静态审查完成，动态验证未执行”。

### Run #134 状态

[Run #134](https://github.com/rexyll/staubli_driver_ros2_from_org/actions/runs/43816245159) 已通过 stock rclcpp 无插桩构建及MoveIt patch静态校验；最新一次核验处于 MoveIt 源码依赖安装步骤。MoveIt build、Stäubli mock build、PSM weak-owner marker及10轮测试尚未执行，不能提前登记结果。


### 2026-11-16补充｜MoveGroupMoveAction detached worker 生命周期风险

静态审计报告 §2.4 新增一项高优先级 shutdown 风险：`MoveGroupMoveAction::initialize()` 的 accepted callback 启动捕获裸 `this` 的 detached worker；`MoveGroupExe::~MoveGroupExe()` 随后执行 `capabilities_.clear()`、`context_.reset()`、`capability_plugin_loader_.reset()`，目前未发现该 capability 对 worker 建立可join的线程句柄、活动计数或 completion barrier。若活动 goal 与 shutdown 重叠，worker可能继续访问已销毁的 capability/context，甚至在 plugin DSO卸载后继续执行其代码。此为静态生命周期风险，不是已复现的use-after-free或崩溃。

新增确定性测试门禁：barrier固定 worker处于plan-only/planning/execution阶段，在worker仍存活时触发shutdown；记录worker start/finish/join与capability/context/loader析构时序；验证先停止新goal接纳、请求worker退出并drain/join，再清除capability/reset context/unload loader。TSAN检查数据竞争；ASan单独辅助检查use-after-free，不与TSAN混用。本轮未修改上游或产品源码，未执行动态复现。


### 多goal共享状态补充

MoveGroup action的goal callback逐个返回ACCEPT_AND_EXECUTE，并逐goal启动detached worker；但Action capability类中只有单份 `goal_`、`move_state_`、`preempt_requested_` 成员。两个goal若重叠accepted，可能产生goal状态/feedback/result串扰和共享成员竞态；当前源码未显示single-active-goal门禁。将双goal并发、分别cancel/natural completion、结果UUID与feedback归属验证加入后续mock测试，具体风险级别以目标rclcpp_action实际执行和TSAN结果为准。

## 2026-11-16 补充｜Run #134 PSM-retained 失败定位与 Run #135 析构边界实验

### Run #134 最终结果

[Run #134](https://github.com/rexyll/staubli_driver_ros2_from_org/actions/runs/43816245159) 使用 commit `5abf808424049dec78e2dc6247f453af59be0e29`，固定 K 与 B-core，只取消 main() 中提前释放 PSM shared owner 的步骤，MoveItCpp 与 main Node owner 仍按原方案 reset。步骤1–9（stock rclcpp无插桩构建、MoveIt静态校验/依赖/构建、Stäubli mock工作区构建）均通过；第10步10轮回归10/10失败，均在move_group shutdown/teardown出现SIGSEGV（exit -11）。

- [x] 10/10 轮 weak_ptr 探针均显示 `use_count=1`：MoveGroupExe/executor作用域退出后，PSM仅剩main()保留的强引用。
- [x] 10/10 轮均在MoveGroupExe析构完成capabilities_.clear()、context_.reset()和capability_plugin_loader_.reset()之后，才进入保留PSM的最终析构路径；日志到达 `Stopping world geometry monitor` 后段错误。当前仅能将“PSM析构被延迟到MoveGroup capability plugin loader卸载之后”列为高优先级生命周期风险候选，尚未由析构逐阶段marker确认具体崩溃指令/成员。
- [x] 更正workflow统计误报：失败日志中的mock execution成功行被 `colcon test-result --verbose` 追加重复打印，故计数2不是两次真实动作；从单独的 `colcon test` 主输出流核对，每轮只有一次mock plan-and-execute成功。这个计数误报不改变10/10 SIGSEGV的真实失败结论。
- [ ] 不得据此宣布“PSM owner保留后一定导致NodeBase/UAF”或认定已找到唯一根因；还需区分PSM析构函数体、其隐式成员析构和Node/CallbackGroup析构阶段。

### Run #135 正在执行

[Run #135](https://github.com/rexyll/staubli_driver_ros2_from_org/actions/runs/43823418805)，workflow commit `ac87221956b3d946d93fb1732fb12ea4e59e8094`，仍使用既有分支 `experiment/moveit-main-owner-lifetime-only`，只改CI workflow中的临时MoveIt overlay：

1. 使main() PSM local owner可显式reset，在MoveGroupExe/executor作用域结束、weak_ptr use_count记录完成后，记录reset BEGIN/END。
2. 在临时 `planning_scene_monitor.cpp` 对析构各阶段加marker：停止publisher/state/world/scene monitor、private executor取消与join、PSM内部scene/model/loader reset、析构函数体结束。marker不更改原有清理调用顺序。
3. 将 `colcon test-result --verbose` 输出写到独立artifact日志，避免重复计数动作成功marker。
4. 继续10轮mock回归；以完整构建、每轮action、launch assertions、teardown顺序及进程退出为联合验收，不以单个marker判断通过。

### 当前判定与约束

- Run #132 stock rclcpp无插桩A+K+B-core 10/10 PASS仍是可靠正向基线；Run #134说明A-PSM-retained不是安全替代顺序。
- 优先比较Run #132的PSM生命周期与Run #134的差异：前者在MoveGroupExe teardown前释放main() PSM alias，使PSM最后owner在context仍持有期间释放；后者将最后owner延迟到plugin loader已reset后。此顺序相关性尚需Run #135析构marker验证，不能只凭相关性推断loader是直接原因。
- 若Run #135确认崩溃发生在PSM析构函数体之外，则下一步拆分PSM的 `node_` / `pnode_` 与其拥有的subscription、timer、private executor成员释放关系；如崩溃发生在函数体内，则依据最后一个marker再拆分相应资源。一次仍只改变一个生命周期因素。
- 所有结果限CI temporary MoveIt overlay + stock rclcpp + Stäubli mock；不改MoveIt/rclcpp upstream或Stäubli产品源码，不连接CS9，不发送真实运动，不宣称HIL/SAT或实机验收。全局最高优先级仍为根TaskPlan 00-01；MotionControlAlgorithms合并继续DEFERRED。


### PSM → Node → NodeBase → CallbackGroup 的潜在延迟释放链（源码静态核验）

为进一步解释 Run #134 的 CallbackGroup/weak ServiceBase 栈，固定核对 MoveIt Jazzy 与 ROS 2 rclcpp Jazzy 对应源码：

- `PlanningSceneMonitor` 持有 `std::shared_ptr<rclcpp::Node> node_` 与 `pnode_`；其析构函数体显式停止 monitor/线程并 reset scene、current-state monitor 与 robot-model loader，但不会在函数体末尾显式 reset 这两个 Node shared owners。它们随 PSM 成员在析构函数体之后按声明逆序释放。
- ROS 2 Jazzy `Node::~Node()` 先释放 `node_waitables_`、`node_services_` 等子接口；`node_base_` 则在 Node 成员析构阶段继续释放。`NodeBase` 持有 `default_callback_group_` 和 `std::vector<CallbackGroup::WeakPtr> callback_groups_`。
- `CallbackGroup` 自身保存多组弱引用容器，其中包含 `std::vector<ServiceBase::WeakPtr> service_ptrs_`；`CallbackGroup::~CallbackGroup()` 函数体只触发通知，成员弱引用容器在函数体之后销毁。因此 action/service strong owner 已消失后，其弱 control block 仍可留在 callback group，直至 group 本身销毁。
- `MoveGroupExe` 的顺序是 `capabilities_.clear()` → `context_.reset()` → `capability_plugin_loader_.reset()`。Run #134 刻意保留 PSM main-local owner，导致 PSM 及其 main Node 的最终释放被推迟到 capability plugin loader reset 之后；Run #132 则在 context teardown 前放弃 main-local PSM alias，使 PSM 随 context 在 loader reset 前销毁。

**待证机制（不是已确认根因）：** 若 capability plugin 创建的 action/service waitable 在销毁后，其 `weak_ptr<ServiceBase>` control block 仍保留于 NodeBase 的 CallbackGroup，而该 control block 的管理函数/虚表确实位于 capability plugin DSO，则 plugin loader 先卸载、CallbackGroup 后销毁会形成对已卸载代码的释放调用。Run #134 的崩溃栈与此路径相符，但还没有取得 control-block manager/vtable 地址到 DSO 映射证据；不能把相关性写成确定因果。

**Run #135 判定方法：**

- 若出现 `[PSM-DTOR] BODY-END` 而缺少 `[OWNER] PSM explicit reset END`，故障位于 PSM 析构函数体后的隐式成员销毁阶段；结合 CallbackGroup/ServiceBase 栈，优先怀疑 `node_`/`pnode_` 所持 Node 的 NodeBase/CallbackGroup 清理，但还需区分具体 Node。
- 若没有 `BODY-END`，则以最后一条 `[PSM-DTOR]` marker 缩小至对应显式停止/重置步骤，不提前进入 weak-control-block / DSO 假设。
- 若出现 `PSM explicit reset END`，说明完整 PSM 析构返回；应继续检查 main return 后的其他全局/静态对象，而不是把故障归给 PSM 的 Node。
- 下一次诊断若必须区分 `node_` 与 `pnode_`，应先记录两者的 FQN、use_count 与析构先后，再按单一 owner 做对照；除非有证据，不同时更改 PSM、MoveItCpp 和 main Node 生命周期。

**源码入口（MoveIt Jazzy / ROS 2 rclcpp Jazzy）：**

- [PlanningSceneMonitor header](https://github.com/moveit/moveit2/blob/jazzy/moveit_ros/planning/planning_scene_monitor/include/moveit/planning_scene_monitor/planning_scene_monitor.hpp) 与 [destructor](https://github.com/moveit/moveit2/blob/jazzy/moveit_ros/planning/planning_scene_monitor/src/planning_scene_monitor.cpp)。
- [MoveGroupContext destructor](https://github.com/moveit/moveit2/blob/jazzy/moveit_ros/move_group/src/move_group_context.cpp) 与 [MoveGroupExe destructor](https://github.com/moveit/moveit2/blob/jazzy/moveit_ros/move_group/src/move_group.cpp)。
- [rclcpp Node destructor](https://github.com/ros2/rclcpp/blob/jazzy/rclcpp/src/rclcpp/node.cpp)、[NodeBase callback-group owners](https://github.com/ros2/rclcpp/blob/jazzy/rclcpp/include/rclcpp/node_interfaces/node_base.hpp)、[CallbackGroup weak waitable containers/destructor](https://github.com/ros2/rclcpp/blob/jazzy/rclcpp/src/rclcpp/callback_group.cpp)。

以上仅为源码静态对象链审查；不等同 vtable/DSO 归属证明、动态 UAF/ABI 崩溃根因确认或上游缺陷定论。Run #135 仍在执行，结果待日志确认。


## 2026-11-16 补充｜Run #135 最终结果：崩溃发生在PSM析构后的Node链，Node身份待定

[Run #135](https://github.com/rexyll/staubli_driver_ros2_from_org/actions/runs/43823418805)，workflow commit `ac87221956b3d946d93fb1732fb12ea4e59e8094`，步骤1–9（stock rclcpp无插桩构建、MoveIt静态补丁/依赖/构建、Stäubli mock工作区构建）全部通过；第10步10轮回归10/10失败。

- [x] 每轮唯一mock plan-and-execute成功；失败不是规划或执行动作本身。
- [x] 10/10轮均出现 `[PSM-DTOR] BODY-END`，说明PSM析构函数体内的monitor stop、private executor cancel/join/reset、scene/state/model/loader显式释放均已执行。
- [x] 10/10轮BODY-END记录 `node_use=2 pnode_use=1`。PSM构造函数创建`pnode_`为独立private Node，加入PSM private executor；析构中先join线程并reset private executor后，pnode_剩余唯一强引用即PSM成员本身。
- [x] 10/10轮main()的 `PSM explicit reset END`没有运行时输出；崩溃发生在 `planning_scene_monitor.reset()`内部、PSM析构函数体结束之后的隐式成员释放阶段。
- [x] GDB调用链：`PlanningSceneMonitor`隐式`shared_ptr`成员析构 → `rclcpp::Node::~Node()`（node.cpp）→ `NodeBase::~NodeBase()`（node_base.cpp）→ `CallbackGroup::~CallbackGroup()`（callback_group.cpp）→ `vector<weak_ptr<ServiceBase>>`销毁 → `weak_ptr::_M_weak_release()` → virtual `_M_destroy()`，SIGSEGV。
- [x] Run #135据pnode_ use_count=1与成员声明顺序，曾推断故障落在pnode_最后释放；但GDB调用栈只显示PSM析构链中的Node/NodeBase/CallbackGroup，并未输出Node指针与pnode_成员的匹配。Run #136后来显示vector析构范围仅1个weak_ptr，与pnode_默认组静态预期6个参数服务+1个GetPlanningScene服务不符，因此撤回“已锁定pnode_”结论。
- [ ] 尚未证明control-block `_M_destroy()` 的manager/vtable地址属于已卸载MoveGroup capability plugin DSO。也可能是其他control-block生命周期/内存损坏机制；必须取故障PC和共享库映射后再归因。

## 2026-11-16 补充｜Run #136 GDB 地址与 DSO 映射取证（执行中）

[Run #136](https://github.com/rexyll/staubli_driver_ros2_from_org/actions/runs/43832589348)，workflow commit `337bf6c6f40b4982629e690d1a5748f94d914053`。仍在同一实验分支与同一PSM-retained mock处理下运行，只把`move_group`临时包装为batch GDB；捕获`bt full`、`info sharedlibrary`、`info proc mappings`、`info registers`及`x/8i $pc`。不改变PSM/Node/CallbackGroup清理顺序，也不修改MoveIt/rclcpp upstream或Stäubli产品源码。诊断结果待定。

**下一步判定：** 若实际PC/目标地址落在未加载的插件DSO范围，进一步将control-block dynamic type/vtable或manager函数关联到具体DSO，建立卸载顺序因果；若PC在仍加载的libstdc++/rclcpp/MoveIt库，转向检查control block对象地址、weak_count及其分配/释放配对，不能继续沿“插件卸载”单一路径推进。


### Run #135 pnode_ CallbackGroup 的静态 ServiceBase 候选（未与Run #136单元素vector关联）

进一步将 pnode_ 的 `ServiceBase::WeakPtr` 清理链映射到 MoveIt Jazzy 的具体 service 创建路径：

1. `MoveGroupGetPlanningSceneService::initialize()` 调用 `context_->planning_scene_monitor_->providePlanningSceneService(GET_PLANNING_SCENE_SERVICE_NAME)`。
2. `PlanningSceneMonitor::providePlanningSceneService()` 在 `pnode_` 上调用 `create_service<moveit_msgs::srv::GetPlanningScene>()`，并把返回的强引用保存在 PSM 成员 `get_scene_service_`；service callback 捕获 PSM `this` 并调用 `getPlanningSceneServiceCallback()`。
3. ROS 2 Jazzy `Node::create_service()` 的 `group` 默认参数是 `nullptr`；`NodeServices::add_service()` 在group为空时取 `node_base_->get_default_callback_group()`，随后调用 `group->add_service(service_base_ptr)`。
4. `CallbackGroup::add_service()` 将 `ServiceBase::SharedPtr` 转成弱引用记录在 `service_ptrs_`。它会清理“此前已expired”的entry，但没有对应的remove_service API；service strong owner消失后，该weak entry可继续留在callback group，直到CallbackGroup本身销毁。
5. PSM持有的 `get_scene_service_` 是强引用；其声明位置早于 `pnode_`。PSM析构函数体结束后按成员逆序析构时，`get_scene_service_`会在更早阶段释放，pnode_及其NodeBase/default CallbackGroup则较晚释放。因此它是pnode_ default CallbackGroup的有效静态候选，但Run #136的vector析构区间仅覆盖一个weak_ptr，且Node身份未确认；不能把它认定为Run #135/136/137实际崩溃的entry。

**历史候选解释，已被后续单元素证据降级：** `get_scene_service_`强引用消失 → pnode_ default CallbackGroup留下expired weak ServiceBase entry的源码路径成立，但pnode_默认组静态预期至少7个service，而Run #136的析构区间仅1项，且Run #136/137没有证明故障Node就是pnode_。当前优先候选改为PSM先销毁的tf_listener_内部Node及其唯一`~/get_type_description` service；详情见本文件后续TypeDescription生命周期链。无论是哪条服务路径，control-block vptr失效的直接原因仍需由Run #139运行时vptr/DSO证据确定。

**关键源码：**

- [MoveGroupGetPlanningSceneService::initialize](https://github.com/moveit/moveit2/blob/jazzy/moveit_ros/move_group/src/default_capabilities/get_planning_scene_service_capability.cpp)
- [PlanningSceneMonitor::providePlanningSceneService / get_scene_service_](https://github.com/moveit/moveit2/blob/jazzy/moveit_ros/planning/planning_scene_monitor/src/planning_scene_monitor.cpp)
- [PSM get_scene_service_ member declaration](https://github.com/moveit/moveit2/blob/jazzy/moveit_ros/planning/planning_scene_monitor/include/moveit/planning_scene_monitor/planning_scene_monitor.hpp)
- [rclcpp create_service default group](https://github.com/ros2/rclcpp/blob/jazzy/rclcpp/include/rclcpp/node.hpp)
- [NodeServices::add_service](https://github.com/ros2/rclcpp/blob/jazzy/rclcpp/src/rclcpp/node_interfaces/node_services.cpp) 与 [CallbackGroup::add_service](https://github.com/ros2/rclcpp/blob/jazzy/rclcpp/src/rclcpp/callback_group.cpp)

以上是源码路径与Run #135 GDB对象链的对应关系；尚未从GDB直接读取`pnode_` CallbackGroup的service_ptrs_元素地址/控制块类型，也未完成control-block manager/vtable到DSO地址映射。


### Run #135 运行时日志确认 GetPlanningScene capability 已加载

对Run #135原始job log按10轮去重后，10/10轮均出现 `Loading 'move_group/MoveGroupGetPlanningSceneService'...`，并在capability清单中出现`get_planning_scene_service`。因此，前述源码路径不只是死代码：当前mock move_group每轮确实加载该capability，执行其initialize()后会调用PSM `providePlanningSceneService()`，从而在private pnode_创建`GetPlanningScene` service并写入`get_scene_service_`。

这将候选ServiceBase记录提升为**静态源码 + 运行时capability加载日志**的双源候选，但还没有运行时观测到pnode_ `service_ptrs_`中的具体weak_ptr地址/数量；更没有确认control-block `_M_destroy()`的代码地址归属。Run #136需要继续提供 fault PC、DSO加载列表和proc mappings，再判断是否是插件卸载后调用了失效manager/vtable。


### pnode_ default CallbackGroup 中 ServiceBase 候选不止 GetPlanningScene

继续核对ROS 2 Jazzy NodeOptions/NodeParameters/ParameterService后，修正上一节“候选ServiceBase可能为PSM get_scene_service_”的范围：

- `NodeOptions::start_parameter_services_` 默认值是 `true`；PSM创建`pnode_`时使用 `rclcpp::NodeOptions().arguments(new_args)`，没有关闭该默认值。
- `NodeParameters`构造函数在参数服务开启时创建`ParameterService`。其构造函数依次创建6个服务：`GetParameters`、`GetParameterTypes`、`SetParameters`、`SetParametersAtomically`、`DescribeParameters`、`ListParameters`；六次`create_service()`都传入`group=nullptr`。
- `pnode_`另有一个由PSM `get_scene_service_`成员持有的`GetPlanningScene` service；Run #135原始日志10/10轮都确认`MoveGroupGetPlanningSceneService` capability实际加载。
- `NodeServices::add_service()`对nullptr group使用`NodeBase::get_default_callback_group()`，因此上述6个ParameterService endpoints和1个GetPlanningScene endpoint都会登记为同一个pnode_ default CallbackGroup中的`ServiceBase::WeakPtr`。
- PSM析构后，`get_scene_service_`随PSM成员销毁；pnode_ Node析构时先reset `node_parameters_`，其`ParameterService`及6个strong service owners随后释放；NodeBase/default CallbackGroup在后续阶段才销毁，若该路径实际运行则会留下多个expired control blocks；但Run #136观测只有1项，未证实此路径就是故障vector。

**范围更正：** Run #135的GDB栈只能确认崩溃发生在`vector<weak_ptr<ServiceBase>>`销毁期间，尚不能确认是哪一个service entry触发故障。当前按源码可预期至少7个ServiceBase weak entries（6个参数服务 + 1个GetPlanningScene），具体实际数量和逐项control-block地址需要Run #136 GDB在CallbackGroup析构现场检查。不能把`get_scene_service_`唯一化，也不能把control-block DSO归属写成已确认。

**Run #136下一步GDB现场检查：** 在`CallbackGroup::~CallbackGroup()`的崩溃现场读取`this`、`service_ptrs_.size()`、每个`weak_ptr`的`_M_pi`地址，以及故障时的PC/共享库映射。再将vector条目地址和控制块manager/vtable代码地址与加载/未加载的DSO区间比较；如需确认具体service名称，可在后续单独CI-only NodeServices::add_service日志中记录node FQN、group地址和service地址，不改变rclcpp特殊成员函数/析构语义。

**源码入口：** [NodeOptions default parameter services](https://github.com/ros2/rclcpp/blob/jazzy/rclcpp/include/rclcpp/node_options.hpp)、[NodeParameters creates ParameterService](https://github.com/ros2/rclcpp/blob/jazzy/rclcpp/src/rclcpp/node_interfaces/node_parameters.cpp)、[ParameterService six endpoints](https://github.com/ros2/rclcpp/blob/jazzy/rclcpp/src/rclcpp/parameter_service.cpp)、[NodeServices::add_service](https://github.com/ros2/rclcpp/blob/jazzy/rclcpp/src/rclcpp/node_interfaces/node_services.cpp)、[PSM GetPlanningScene service](https://github.com/moveit/moveit2/blob/jazzy/moveit_ros/planning/planning_scene_monitor/src/planning_scene_monitor.cpp)。


### DSO归属边界更正：ServiceBase 创建点与 MoveIt 链接关系

不能因为MoveGroup capability plugin loader在PSM pnode_最终销毁前reset，就直接推断`ServiceBase` weak control block的`_M_destroy()`代码位于该capability plugin DSO。进一步核对固定MoveIt Jazzy / ROS 2 Jazzy源码：

- 六个参数服务由`rclcpp/src/rclcpp/parameter_service.cpp`中的`ParameterService`构造创建，模板实例化/调用点属于rclcpp代码。
- `GetPlanningScene` service由`moveit_ros/planning/planning_scene_monitor/src/planning_scene_monitor.cpp`中的`PlanningSceneMonitor::providePlanningSceneService()`创建。
- `moveit_planning_scene_monitor`目标是`SHARED` library；`moveit_cpp` CMake target明确`target_link_libraries(moveit_cpp moveit_planning_scene_monitor ...)`；`moveit_ros_move_group` package对`moveit_ros_planning`有直接依赖，后者导出planning相关library targets。

因此目前有理由预期这些ServiceBase control-block管理函数分别在rclcpp与moveit_planning_scene_monitor的代码/数据段中，而这两者属于move_group的依赖链；至少不能假定它们与`moveit_move_group_default_capabilities`插件DSO相同。实际运行进程中这些DSO是否在故障时仍映射、control block vtable/manager具体落在哪个地址，仍以Run #136的`info sharedlibrary`、`info proc mappings`、PC和反汇编为准。若这些库仍驻留，插件卸载假设就应降级，转而检查具体weak_ptr控制块地址、weak_count、对象生命周期和内存破坏。

源码入口：

- [moveit_ros/planning CMake](https://github.com/moveit/moveit2/blob/jazzy/moveit_ros/planning/CMakeLists.txt) 与 [moveit_cpp target link](https://github.com/moveit/moveit2/blob/jazzy/moveit_ros/planning/moveit_cpp/CMakeLists.txt)
- [moveit_ros_move_group CMake](https://github.com/moveit/moveit2/blob/jazzy/moveit_ros/move_group/CMakeLists.txt)
- [rclcpp ParameterService construction](https://github.com/ros2/rclcpp/blob/jazzy/rclcpp/src/rclcpp/parameter_service.cpp)、[create_service template](https://github.com/ros2/rclcpp/blob/jazzy/rclcpp/include/rclcpp/create_service.hpp)
- [PSM GetPlanningScene service creation](https://github.com/moveit/moveit2/blob/jazzy/moveit_ros/planning/planning_scene_monitor/src/planning_scene_monitor.cpp)



### Run #136｜weak control block fault vptr 映射结果与验收脚本修正

Run #136（[Actions #43832589348](https://github.com/rexyll/staubli_driver_ros2_from_org/actions/runs/43832589348)，workflow commit `337bf6c6f40b4982629e690d1a5748f94d914053`）的构建阶段全部通过：stock rclcpp无插桩overlay、临时MoveIt `move_group`、Stäubli mock workspace均完成构建。10次mock launch均完成规划执行，且每轮launch测试汇总实际为7 tests、0 errors、0 failures、0 skipped；但10/10轮move_group进程在PSM析构路径发生真实SIGSEGV。

首轮GDB现场关键寄存器/指令：

- `rip=0x7ba20a70b8f1`，符号为 `rclcpp::CallbackGroup::~CallbackGroup()+449`；该PC处于仍映射的 `librclcpp.so`。
- 故障指令为 `call *0x18(%rax)`；`rax=0x7ba1cccb62e0`，作为间接调用读取虚表目标的基址，但该地址不落在当时任何有效进程映射内。
- `rdi=0x5b24da5d8260`，对应 `std::_Sp_counted_base::_M_release_last_use(this=...)` 的control block对象。
- 栈为 `CallbackGroup::~CallbackGroup()` → `vector<weak_ptr<ServiceBase>>`元素析构 → `weak_ptr::_M_weak_release()` → `_M_release_last_use()`；上层依次为 `NodeBase::~NodeBase()`、`Node::~Node()`、`PlanningSceneMonitor::~PlanningSceneMonitor()`，与Run #135所确定的PSM private `pnode_`最终释放边界一致。
- 故障时 `librclcpp.so`、`libmoveit_planning_scene_monitor.so`、`libmoveit_cpp.so`、`libmoveit_move_group_capabilities_base.so` 与 `libmoveit_move_group_default_capabilities.so`均仍在共享库列表/进程映射中。故当前证据不支持这些关键DSO已先卸载；vptr未映射仍可能是其他DSO unload留下的悬空指针，也可能是control block/vptr内存被覆盖或破坏。

**Run #136并未读取到 `service_ptrs_.size()` 和每个weak entry的vptr。** 寄存器 `r9=7`与静态源码预期的6个ParameterService + 1个GetPlanningScene service数量相同，但这只是寄存器巧合/线索，不能作为vector运行时size证据。当前不能断言具体是七个entry中的哪一个触发故障，也不能认定plugin unload为唯一根因。

另一个独立修正：workflow将 `colcon test-result --verbose` 输出写入 `.result.log`，但原验收Python脚本误从主测试日志查找7项汇总，因此每轮 `lifecycle_order=1`。真实 `colcon test` 与 `test_result` 命令均返回0，且result log实际包含完整7项通过汇总。Run #137已将解析器改为同时读取两份日志，并加入GDB捕获SIGSEGV的显式判定，避免GDB包装进程退出0掩盖子进程崩溃。

- Run #136 artifact：ID `14209759591`，SHA-256 `92532aa834b356f441ce6dc8b845c1f0a0325fda9b5bf0afcf4b1b033bca2ea9`，大小 2,627,594 bytes。
- [artifact下载入口](https://github.com/rexyll/staubli_driver_ros2_from_org/actions/runs/43832589348/artifacts/14209759591)。

### Run #137｜逐项读取weak control block与DSO卸载事件（执行中）

- workflow commit：`4aa4539a9adfd5efe0adea52753ba1847abf8a53`；复用原分支 `experiment/moveit-main-owner-lifetime-only`，没有创建新分支。
- [Actions Run #43836147761](https://github.com/rexyll/staubli_driver_ros2_from_org/actions/runs/43836147761)。
- GDB新增 `catch unload` 事件输出；SIGSEGV处输出 `$rax` / `$rdi`内存、切至CallbackGroup析构栈帧读取 `service_ptrs_.size()`，逐项打印weak object、control-block地址、control-block首字（vptr）及符号归属。
- 验收解析器改为读取 `.result.log`中的7项汇总，并直接检查GDB是否出现 `received signal SIGSEGV`。
- 当前状态：workflow job处于运行中，第5步stock rclcpp uninstrumented overlay build正在执行；MoveIt、Stäubli mock build和10轮GDB回归尚未开始，结果未定。

### 下一步判定规则

1. 若某个weak control block首字/vptr落在某次 `catch unload`记录中明确卸载的DSO地址范围，且卸载先于最后weak release，才把该DSO列为直接悬空vptr候选；需进一步用符号/链接/构造调用点确认对象类别。
2. 若所有weak control block的vptr均指向仍映射的DSO，但 `_M_destroy()`仍跳向未映射地址，则重点检查control block首字是否被覆盖、对象布局/ABI是否一致，以及weak_count/control block是否被提前释放。
3. 如果GDB不能可靠打印私有成员，不改rclcpp特殊成员函数；改用CI-only `NodeServices::add_service()`创建时关联记录，按node FQN、callback group地址、service地址和control-block地址做对应。
4. Run #137结果继续严格限制为临时MoveIt overlay + stock rclcpp + Stäubli mock CI，不视为upstream/产品修复或CS9/HIL/SAT/实机验收。


### Run #136 GDB vector长度与服务集合预期冲突（补充复核）

对Run #136首轮GDB原始栈重新提取，std::vector<std::weak_ptr<ServiceBase>>的迭代范围为：

- __first=0x5b24d96db600
- __last=0x5b24d96db610

在该运行时ABI下单个std::weak_ptr占16字节，因此该次vector析构实际覆盖1个元素。调用栈frame #10为rclcpp::CallbackGroup::~CallbackGroup()，frame #16/#24/#30依次包含NodeBase、Node和PlanningSceneMonitor析构；但Run #136没有打印CallbackGroup对象地址、Node成员身份或service_ptrs_.size()，不能仅凭此栈将这个单元素vector指定为某个具体service，也不能把它等同于源码预期的7项完整集合。

静态源码预期的7项仍有依据：PSM创建pnode_时只覆盖NodeOptions arguments，Jazzy NodeOptions默认start_parameter_services=true；NodeParameters创建6个ParameterService service；PSM另通过providePlanningSceneService()创建GetPlanningScene service。这是构造路径的静态预期，不是Run #136故障时的运行时vector size。还需考虑实际group归属、弱引用是否在此前被清理、以及vector元数据是否受损等可能性。

**Run #137的首要判定项：** 直接读取this->service_ptrs_.size()、CallbackGroup this地址、所属Node地址/名字（可由栈中PSM成员指针辅助关联）、每项weak object/control block/vptr和符号归属。若GDB私有成员数据与vector析构区间再次不一致，应将vector元数据完整性列为独立调查项；不得继续把“7项”写成已观测事实。

### Run #137 当前进度更正

Run #137（[Actions #43836147761](https://github.com/rexyll/staubli_driver_ros2_from_org/actions/runs/43836147761)，commit 4aa4539a9adfd5efe0adea52753ba1847abf8a53）当前job第1–7步成功，第8步Build patched MoveIt move_group正在执行；第9步Stäubli mock workspace build、第10步10轮GDB teardown regression尚未开始。尚无Run #137 PASS/FAIL结论。实验仍限于CI temporary MoveIt overlay + stock rclcpp + Stäubli mock；不触碰上游/产品源码，不连接CS9，不做真实运动、HIL或SAT。


### Run #137最终结果更正：底层崩溃复现，GDB取证脚本中断

Run #137（[Actions #43836147761](https://github.com/rexyll/staubli_driver_ros2_from_org/actions/runs/43836147761)，commit 4aa4539a9adfd5efe0adea52753ba1847abf8a53）已完成：

- [x] MoveIt patched move_group构建成功（step 8）。
- [x] Stäubli mock workspace构建成功（step 9）。
- [x] 10/10轮均复现move_group teardown SIGSEGV，故障栈仍位于CallbackGroup析构的weak_ptr<ServiceBase> control-block weak-count release。
- [x] 10轮测试汇总均为`Summary: 7 tests, 0 errors, 2 failures, 0 skipped`；严格进程退出测试失败，不能计PASS。
- [x] 日志归档和容器清理成功（step 11及cleanup）。

**诊断工具自身的失败：** GDB脚本第22行执行`x/8gx $rax`，但$rax指向未映射地址（例如`0x75fa818a12e0`），并返回`Cannot access memory`，使GDB sourced command file中止。因中断发生在`frame 10`和`service_ptrs_.size()`之前，Run #137没有实际输出group size、weak entry、control block vptr或所属Node；日志中的`[GDB-WEAK]`仅是脚本源代码行，不是运行时entry输出。应区分“10/10真实teardown崩溃”与“诊断脚本无法继续”，不能将后者描述为功能测试通过。

### 单元素CallbackGroup的新候选：TransformListener内部Node的Type Description服务

ROS 2 Jazzy源码复核发现：

- `rclcpp::NodeTypeDescriptions`默认启用参数`start_type_description_service=true`，并在启用时创建`~/get_type_description`，通过`NodeServices::add_service(..., nullptr)`注册到节点默认CallbackGroup。
- Jazzy `tf2_ros::TransformListener`创建`optional_default_node_`时显式关闭`start_parameter_services`和`start_parameter_event_publisher`，但没有关闭`start_type_description_service`。
- MoveIt PSM持有`tf_listener_`，且该成员在析构顺序中先于`pnode_`销毁。TransformListener内部Node因此可能在PSM析构链中先被释放；其默认CallbackGroup可能恰有一个Type Description Service弱引用。

这条路径与Run #136/137观察到的单元素vector数量吻合，是当前优先核验候选，不是已证实根因。必须通过NodeBase地址、CallbackGroup地址、服务名和PSM成员指针在同一轮GDB日志中关联确认；不能仅凭数量认定为`get_type_description`。

### Run #138｜修复GDB取证并绑定服务/Node/CallbackGroup身份（执行中）

- workflow commit：`8680810cfe15152ce5b9cd6ed21cbc196e2baaad`，仍复用`experiment/moveit-main-owner-lifetime-only`，没有新建分支。
- [Actions Run #43839729557](https://github.com/rexyll/staubli_driver_ros2_from_org/actions/runs/43839729557)。
- 移除对无效`$rax`目标的内存解引用；保留faulting PC、$rax值和$ rdi control-block地址，并从control block读取vptr。
- 增加`gdb.events.free_objfile`事件输出，直接记录正在从GDB移除的objfile路径；避免Run #137每次unload仅重复输出全库列表而无法识别具体DSO。
- 在`NodeServices::add_service`和`CallbackGroup::add_service`设置CI-only GDB断点，分别记录NodeBase/service地址与CallbackGroup/service地址/服务名，通过service地址关联所有者、组和名称。
- 崩溃现场读取CallbackGroup实际size和每个weak object/control block/vptr；再将析构Node与PSM的`node_`、`pnode_`、`tf_listener_`及TransformListener的内部Node地址进行比对。
- 当前状态：Actions第1–2步成功，第3步ROS Jazzy环境setup运行中；MoveIt build、mock workspace build和10轮回归尚未开始。

**约束：** 仅CI临时MoveIt overlay、stock rclcpp与Stäubli mock；不修改MoveIt/rclcpp upstream、不修改Stäubli产品源码、不连接CS9、不发送真实运动命令、不做HIL/SAT/实机验收。


### Run #138前静态生命周期链进一步收敛（ROS 2 Jazzy精确分支）

已从ROS 2 Jazzy源码而非Rolling分支复核以下路径：

1. MoveIt Jazzy PSM成员中`tf_listener_`声明在`pnode_`之后；C++成员按声明逆序销毁，因此PSM释放`tf_listener_`早于`pnode_`。
2. Jazzy TransformListener在没有外部Node接口时创建`optional_default_node_`；仅调用`start_parameter_event_publisher(false)`和`start_parameter_services(false)`，没有设置type-description service关闭选项。
3. Jazzy NodeTypeDescriptions将`start_type_description_service`声明为默认true；启用时创建`~/get_type_description`，通过`node_services->add_service(..., nullptr)`加入default CallbackGroup。
4. Jazzy `Node::~Node()`函数体依次reset node_waitables、node_time_source、node_parameters、node_clock、node_services、node_topics、node_timers、node_logging、node_graph；没有显式reset node_type_descriptions_。该成员在`node.hpp`中声明于node_base_之后，隐式成员逆序析构时先于node_base_销毁。
5. 因此NodeTypeDescriptions所持Service强引用先释放，而NodeBase/default CallbackGroup仍存活并保留一个weak_ptr；随后NodeBase析构销毁CallbackGroup，恰好释放该单一weak entry。这与Run #136/#137的一个16字节weak_ptr范围及weak_ptr析构栈高度吻合。

这构成当前最强的**静态生命周期解释**，但仍不能单靠源码确定Run #136/#137现场的Node确实是TransformListener的`optional_default_node_`。Run #138需用`NodeServices::add_service`的NodeBase/service name、`CallbackGroup::add_service`的group/service address，以及PSM的`node_`/`pnode_`/`tf_listener_`/TF internal Node指针作同一进程关联。

此外，当前可解释“为什么恰有一个weak entry”，但尚未解释control-block vptr为何落到未映射地址；若运行时确认服务为`~/get_type_description`且vptr在librclcpp/其编译单元地址范围，则需进一步检查control-block内存损坏、ABI/对象布局、弱计数生命周期和实际vptr归属。不可仅凭本静态链把DSO unload宣布为根因。


### Run #138环境阶段失败及Run #139重试

- Run #138（[Actions #43839729557](https://github.com/rexyll/staubli_driver_ros2_from_org/actions/runs/43839729557)，commit `8680810cfe15152ce5b9cd6ed21cbc196e2baaad`）完成ROS Jazzy setup，但step 4 `rosdep update --rosdistro jazzy`在请求`https://raw.githubusercontent.com/ros/rosdistro/master/rosdep/base.yaml`时出现`Connection reset by peer`，随后报告not all sources updated并exit 1。
- MoveIt/rclcpp构建、Stäubli mock build和GDB 10轮均被跳过。该失败属于外部依赖索引网络中断，不是代码编译错误，也没有新的teardown结论。
- 已在同一workflow加入5次有限重试，每次间隔8秒；五次仍失败则明确exit 1，不忽略rosdep错误。
- Run #139（[Actions #43840240632](https://github.com/rexyll/staubli_driver_ros2_from_org/actions/runs/43840240632)，commit `5332c79ead53d811bc7b5820d10e269eeaddff66`）已触发，当前容器初始化中；待确认重试步骤以及后续诊断是否能真正运行。


### 历史判断纠正｜撤回“Run #135/136已锁定pnode_”

Run #135的`node_use=2 pnode_use=1`、PSM成员声明顺序，以及Run #135的PSM析构调用链，曾把故障Node推断为pnode_。这一判断属于当时的候选收窄，但不等于运行时地址身份确认。Run #136后续的GDB迭代区间`0x5b24d96db600–0x5b24d96db610`按16字节/weak_ptr仅覆盖1项；pnode_默认组按源码应包含6个ParameterService和1个GetPlanningScene服务，数量不匹配。Run #136/137又未输出故障Node指针或service name。因此根因定位必须回退为“PSM析构链中的Node/NodeBase/CallbackGroup”，具体Node待确认。

pnode_的GetPlanningScene + 6个ParameterService静态登记路径保留为该节点的真实候选，不删除历史证据；但它与Run #136/137的单元素vector目前没有直接关联。当前更强的单元素候选是tf_listener_内部Node的唯一TypeDescription service，需Run #139在同一现场通过NodeBase、group、service name及PSM成员地址核验。


### MoveIt PSM 实际调用 TF TransformListener 简化构造重载（确认）

对MoveIt Jazzy `planning_scene_monitor.cpp`第112–121行重新核对：

- PSM首先构造独立`pnode_`；
- 随后明确执行`tf_listener_ = std::make_shared<tf2_ros::TransformListener>(*tf_buffer_);`；
- 这匹配geometry2 Jazzy `TransformListener(tf2::BufferCore &, bool spin_thread = true)`简化构造重载；文档明确该重载会在内部创建ROS 2 Node；
- 实际进入TransformListener简化构造函数后，会创建`optional_default_node_`，然后用该Node的base/logging/parameters/topics interfaces初始化TF subscriptions；
- 因而Type Description唯一Service路径并非根据“可能选择某个重载”作出的猜测，而是MoveIt PSM当前源码确实采用的重载。

结合已核验的成员/Node析构顺序，静态路径可完整解释一个weak ServiceBase entry为何留到CallbackGroup析构时最后释放。Run #139仍须用运行时日志把崩溃NodeBase/CallbackGroup/service name与`tf_listener_->optional_default_node_`地址对应，不能把静态源链升级为运行时根因定论。
