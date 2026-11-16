# Stäubli MoveIt teardown 生命周期 A/B 完整 2×2 因子实验与析构根因定位（Run #107 / #118 / #119 / #121）

**记录日期：** 2026-11-16  
**目标仓库：** `rexyll/robot_knowledgebasement`  
**被测工程：** `rexyll/staubli_driver_ros2_from_org`  
**状态：** K=ON 背景下的完整 A/B 2×2 矩阵已补齐：K-only、K+A、K+B 均 5/5 teardown FAIL；K+A+B 5/5 PASS。失败都发生在 mock 轨迹执行成功之后的 move_group teardown。K-only 的 LD_DEBUG 与 GDB 日志进一步证明 controller-manager DSO 卸载先于残余 executor/WaitSet、NodeBase/CallbackGroup 清理；MoveIt Jazzy TEM 成员声明顺序构成高度吻合的生命周期缺陷链。具体失效 Waitable 动态类型及控制块析构回调仍待直接观测。  
**边界：** 所有源码改动均通过 GitHub Actions 在临时 MoveIt/rclcpp overlay 中注入；不是 MoveIt、rclcpp 或 Stäubli 产品源码修复，也不构成 CS9、HIL、SAT 或真实机器人验收。

## 1. 实验矩阵与同基线约束

历史 Run #73 没有采用与当前实验相同的 PSM publisher stop 与 MoveGroupExe/executor 作用域顺序，不能作为严格的 0/0 单元格。本轮新增 K-only Run #121，复用同一实验分支及 workflow，仅关闭 A、B 两组处理，补齐同一 K 背景下的四个单元格。因此，**Run #107/#118/#119/#121 组成完整的 K 固定背景下 A/B 2×2 矩阵**；Run #73 只作为较早的崩溃历史，不纳入矩阵统计。

## 2. 共同背景 K：三个实验都保留的处理

Run #118、#119 与 #107 的 workflow 都对 MoveGroup 主作用域做了以下相同处理：

1. executor.spin() 返回后，先调用 `planning_scene_monitor->stopPublishingPlanningScene()`，再执行 `rclcpp::shutdown()`，让 PlanningSceneMonitor 的 scene publisher 线程先停止并 join。
2. 将 `MoveGroupExe mge` 声明在 `MultiThreadedExecutor executor` 之前。C++ 逆序析构因此先销毁 executor / WaitSet，再销毁 MoveGroupExe，避免 capability plugin 实例/DSO 先于 executor WaitSet 清理。
3. 保留 MoveGroupExe 原有析构函数体顺序 `capabilities_.clear()` → `context_.reset()` → `capability_plugin_loader_.reset()`；只增加 CI 生命周期日志。
4. 保持 ROS Jazzy stock signal handling；没有注入自定义 sigwait 或 signal-handler 改写。

这意味着 #118/#119 的单因子结果是在 K 已启用的背景下测得；不能把 K 当作已由本轮单独证明必要或充分的因素。

## 3. A 与 B 的精确定义

### A｜主函数外部 shared-owner 提前释放

A=ON 时，workflow 将局部变量声明从 `const auto` 调整为可 reset 的 `auto`，并在 `rclcpp::shutdown()` 后、`MoveGroupExe` 离开作用域前，依次执行：

1. `planning_scene_monitor.reset()`
2. `moveit_cpp.reset()`
3. `nh.reset()`

这三项是同一个实验因子；本轮没有分别证明其中任意一项单独充分或必要。其目标是让 MoveGroupExe 后续执行 `context_.reset()` 时，MoveItCpp / TEM / PSM / Node 的析构不再被 main() 中遗留的额外 shared owner 推迟到 capability plugin loader 卸载之后。

A=OFF 时保留 stock main() 局部 owner 生命周期，不提前 reset 这三个 shared pointer。

### B｜TEM 内部 controller-manager / callback owner 显式清理

B=ON 时，workflow 在 TEM 中把 event callback group 从局部变量提升为成员，并在析构函数体中执行：

1. `stopExecution(true)`、cancel private executor，并 join private executor thread；
2. reset `event_topic_subscriber_`；
3. reset parameter callback handle `callback_handler_`；
4. reset `event_callback_group_`；
5. 从 private executor 移除 `controller_mgr_node_`；
6. reset `private_executor_`，先销毁其 WaitSet / collector owner；
7. reset `controller_manager_` plugin instance；
8. reset `controller_mgr_node_`；
9. 之后再由 TEM 自动成员析构到达 `controller_manager_loader_` 的释放阶段。

B=OFF 时不执行该 TEM cleanup 注入；TEM 保持 Jazzy 原始析构函数，只执行 stock stop/cancel/private-executor join。

注意：B 的这组 cleanup 不等于已解决 TEM 全部同步问题。自然完成与取消竞争中的 `execution_thread_` missed-join 是独立缺陷；Run #117 的 always-join CI-only barrier candidate 单独覆盖该窗口，不证明 `execution_complete_`、`last_execution_status_`、`preempt_requested_` 等其他访问都无数据竞争。

## 4. K 固定背景下完整 A/B 2×2 结果

| Run | 共同背景 K | A：主作用域 owner reset | B：TEM 显式 cleanup | teardown 结果 |
|---|---|---:|---:|---|
| #121 K-only | ON | OFF | OFF | **5/5 FAIL** |
| #118 main-owner-only | ON | ON | OFF | **5/5 FAIL** |
| #119 TEM-cleanup-only | ON | OFF | ON | **5/5 FAIL** |
| #107 combined | ON | ON | ON | **5/5 PASS** |

- [Run #121 / Actions ID #43789238751](https://github.com/rexyll/staubli_driver_ros2_from_org/actions/runs/43789238751)：workflow commit `739afbbe2722ebd494326272ec298d896ab193c4`，artifact ID `14191994262`，日志包 SHA-256 `f6017a6b71eaf73e13893d2f2f645ca2138b72cfac97a4cb9fb70f06f44d9182`。
- [Run #118](https://github.com/rexyll/staubli_driver_ros2_from_org/actions/runs/43684020993)：workflow commit `0420f0259d652ca01b3d2e26cce26a3d45dfe73e`，artifact ID `14149678145`。
- [Run #119](https://github.com/rexyll/staubli_driver_ros2_from_org/actions/runs/43684023847)：workflow commit `8218084250c9c45fe275f7729ae98f59792a422b`，artifact ID `14149932259`。
- [Run #107](https://github.com/rexyll/staubli_driver_ros2_from_org/actions/runs/43677374898)：workflow commit `18fea00298ee542c304cbf73d652cd540262712e`，A+B 组合下 mock 轨迹执行及 teardown 5/5 通过。
- [Run #117](https://github.com/rexyll/staubli_driver_ros2_from_org/actions/runs/43683012297)：A+B 背景下，always-join CI-only candidate 的自然完成/取消 barrier 回归 5/5 通过。

四格运行的 source overlay、patched MoveIt move_group 和 Stäubli mock workspace 均成功构建；三个失败格均在 mock action 成功后 teardown 失败，不是编译失败。

## 5. 失败和通过的日志证据

### Run #121｜K-only，A=OFF/B=OFF

- 五轮控制器均报告 `Goal reached, success!`，TEM 均报告 `Completed trajectory execution with status SUCCEEDED`。
- 五轮均在 `move_group` teardown 阶段收到 `SIGSEGV`，workflow 汇总 `failures=5/5`；strict process assertion 将 `gdb` 子进程 exit code 255 判为失败。
- 每轮 LD_DEBUG 都先报告 `calling fini` / `destroying link map`：`/opt/ros/jazzy/lib/libmoveit_simple_controller_manager.so` 被卸载；随后 private executor 析构日志出现，之后 GDB 在 `CallbackGroup::~CallbackGroup()` 析构 `std::vector<std::weak_ptr<rclcpp::Waitable>>` 时崩溃。
- GDB 栈从 `weak_ptr<Waitable>` 的 `_M_weak_release` / `_M_release_last_use`，进入 `CallbackGroup::~CallbackGroup()`、`NodeBase::~NodeBase()`、`rclcpp::Node::~Node()`、`TrajectoryExecutionManager::~TrajectoryExecutionManager()`，再回到 `MoveItCpp::~MoveItCpp()`。
- 五轮均出现相同的 DSO unload → CallbackGroup weak-entry teardown → SIGSEGV 顺序，说明 K 本身不足以修复，且故障可稳定复现。

### Run #118｜K+A，B=OFF

- 每轮控制器均报告 `Goal reached, success!`，TEM 报告 `Completed trajectory execution with status SUCCEEDED`。
- 每轮 move_group 在 teardown 阶段收到 `SIGSEGV`，GDB 栈顶落在 `std::_Sp_counted_base::_M_release_last_use`（`shared_ptr_base.h:172`）。
- launch shutdown 断言报告 GDB 子进程退出码 255；workflow 汇总 `failures=5/5`。
- 该结果说明 A 在 K 已启用、但没有 B cleanup 时不足以通过当前 mock teardown。

### Run #119｜K+B，A=OFF

- 各轮 TEM cleanup 日志显示 `execution_thread_joinable=0`、`active_handles_after_stop=0`，event subscription、callback group、controller-manager instance 和 controller node reset 路径执行。
- 每轮控制器均报告 `Goal reached, success!`，TEM 报告 `SUCCEEDED`；失败仍发生在 move_group teardown，GDB 栈顶为 shared_ptr release，最终 `failures=5/5`。
- 生命周期顺序日志显示 MoveGroupExe 的 capability plugin loader reset 先于随后被延迟释放的 MoveItCpp/TEM owner。单独的 TEM 内部清理不能替代 main() 外部 shared owner 的释放时机治理。

### Run #107｜K+A+B

- 五轮 mock FollowJointTrajectory 均完成；
- TEM 执行状态为 SUCCEEDED；
- 五轮均无 MoveGroup SIGSEGV；
- strict post-shutdown process checks 通过。

这说明 A+B 在本 workflow 的测试输入与 mock 环境下构成有效组合候选；仍不能作为 stock ROS Jazzy、上游已修复或真实硬件通过的证明。

## 6. 2×2 结果能支持的因果判断及边界

四个单元格均采用 K=ON、固定 Stäubli source pin、相同 mock plan-and-execute 输入、五轮重复与 strict teardown assertion：

- A=OFF/B=OFF：5/5 FAIL；
- A=ON/B=OFF：5/5 FAIL；
- A=OFF/B=ON：5/5 FAIL；
- A=ON/B=ON：5/5 PASS。

因此，在当前 CI/mock 场景与固定输入下，A、B 任一单独启用都不足以通过；只有 A+B 联合启用的单元格通过。这表明组合处理存在不可忽略的互补/交互关系，不能选择 A-only 或 B-only 作为修复。每格五轮是确定性重复回归，并非独立随机样本；不据此估计统计学主效应或置信区间。

K-only 的日志进一步提供了直接的 teardown 顺序证据：controller-manager plugin DSO 已 `destroying link map` 后，TEM 私有 executor 开始析构，随后 controller-manager NodeBase 的 CallbackGroup 才析构其 Waitable weak_ptr 列表并崩溃。MoveIt Jazzy TEM 头文件中，`controller_mgr_node_` / `private_executor_` 声明在 `controller_manager_loader_` 之前，而 `controller_manager_` 声明在 loader 之后；C++ 成员逆序析构会先销毁 instance，再销毁 loader（卸载 DSO），之后才销毁更早声明的 executor、订阅及 node。这与运行时次序高度吻合。

但仍需保留以下边界：

- 尚未 RTTI/符号化识别造成崩溃的具体 Waitable 动态类型，也未直接打印控制块的 destroy/deallocate 函数归属；因此“控制块回调代码属于已卸载 DSO”是强假设，不是已完成的动态类型证明。
- 尚未拆分 A 内部 PSM、MoveItCpp、Node 三个 reset 的单项必要性；也尚未拆分 B 中 executor/WaitSet、instance、node、event group/subscription 各自的最小充分集合。
- K 中 PSM publisher stop 与 executor/MGE 声明顺序在当前四格中保持不变；本轮不能单独证明 K 中每一项处理是否必要。
- 不将 `shared_ptr::_M_release_last_use` 的顶层栈帧本身当作具体类或具体 shared owner 的证明。

## 7. 下一步实验设计（不触碰产品源码）

按最低改动、最高信息增益推进：

### 7.1 K-only 已完成；下一步先验证 DSO/Node 析构顺序

K-only Run #121 已补齐 0/0 单元格并 5/5 复现 teardown SIGSEGV。下一步不立即大范围拆分全部因子，而是在 A+B 正向候选中保留最小诊断改动，加入 CI-only 实际析构 marker：controller-manager instance dtor 完成、private executor/WaitSet 完全释放、controller-manager NodeBase/default callback group/Waitable weak-list 释放完成、controller-manager DSO unload。再与 K-only 失败格逐项对照，确认 A+B 是否确实把 Node/WaitSet/group 的最终析构移动到 DSO unload 之前。不得仅以 reset() 日志代替真实析构完成证据。

### 7.2 再拆 A 的三个 owner reset（B=ON 固定）

只有在 K-only 对照完成后，才分别进行单项保留/移除实验：

- A-PSM：只改变 `planning_scene_monitor.reset()`；
- A-MoveItCpp：只改变 `moveit_cpp.reset()`；
- A-Node：只改变 `nh.reset()`。

所有 A 子实验固定 B=ON，并保持 K、测试输入和执行轨迹不变。不能通过某次单独 PASS 就直接删掉该 reset；至少需要重复回归、owner 生命周期 marker 和 DSO unload 顺序共同支持。

### 7.3 再拆 B 内部释放边界

先保持 A 完整启用，逐步隔离：
- main-node event subscription / callback group；
- controller-manager node / plugin instance；
- private executor / WaitSet；
- controller-manager loader 的最后卸载点。

每次只改变一个所有权步骤，并保留 #107 的 A+B 5/5 正向对照。

### 7.4 数据竞争与线程任务独立继续

- 完成 `execution_complete_` 全访问点同步域审计；
- 完成 `last_execution_status_` 读写互斥域；
- 完成 `execution_thread_` 创建/赋值/读/Join/reset 的统一所有权规则；
- 单独审查 `preempt_requested_` 的取消回调与 goal thread 访问；
- 使用 barrier-controlled tests 和 TSAN 或等价 race detector 覆盖自然完成、cancel、timeout、clear、callback reentrancy 与 action teardown。

## 8. 源码与 workflow 锚点

- MoveGroup main local owners：[`move_group.cpp`](https://github.com/moveit/moveit2/blob/jazzy/moveit_ros/move_group/src/move_group.cpp)，尤其 `nh`、`moveit_cpp`、`planning_scene_monitor` 创建及 shutdown 顺序。
- MoveGroupContext shared ownership：[`move_group_context.cpp`](https://github.com/moveit/moveit2/blob/jazzy/moveit_ros/move_group/src/move_group_context.cpp) 与 [header](https://github.com/moveit/moveit2/blob/jazzy/moveit_ros/move_group/include/moveit/move_group/move_group_context.hpp)。
- MoveItCpp 持有 node / PSM / TEM：[`moveit_cpp.cpp`](https://github.com/moveit/moveit2/blob/jazzy/moveit_ros/planning/moveit_cpp/src/moveit_cpp.cpp) 与 [header](https://github.com/moveit/moveit2/blob/jazzy/moveit_ros/planning/moveit_cpp/include/moveit/moveit_cpp/moveit_cpp.hpp)。
- TEM 成员逆序析构边界：[`trajectory_execution_manager.hpp`](https://github.com/moveit/moveit2/blob/jazzy/moveit_ros/planning/trajectory_execution_manager/include/moveit/trajectory_execution_manager/trajectory_execution_manager.hpp) 与 [析构函数](https://github.com/moveit/moveit2/blob/jazzy/moveit_ros/planning/trajectory_execution_manager/src/trajectory_execution_manager.cpp)。
- Run #118 workflow gate：[`0420f025...`](https://github.com/rexyll/staubli_driver_ros2_from_org/blob/0420f0259d652ca01b3d2e26cce26a3d45dfe73e/.github/workflows/experiment-moveit-shutdown-order.yml)。
- Run #119 workflow gate：[`82180842...`](https://github.com/rexyll/staubli_driver_ros2_from_org/blob/8218084250c9c45fe275f7729ae98f59792a422b/.github/workflows/experiment-moveit-shutdown-order.yml)。
- Run #107 combined workflow：[`18fea002...`](https://github.com/rexyll/staubli_driver_ros2_from_org/blob/18fea00298ee542c304cbf73d652cd540262712e/.github/workflows/experiment-moveit-shutdown-order.yml)。

## 9. 安全与修改边界

- 当前只保留 A+B 为唯一已验证的 CI-only 组合候选；不将 #118/#119 单因子候选作为通过方案。
- 新增 K-only 与 A/B 子步骤实验应限制为临时 mock CI overlay，不提交 MoveIt/rclcpp upstream，不修改 Stäubli 产品源码或 PR #1。
- 若后续需要在 Stäubli driver 工程新增实验 workflow commit，应使用经授权的隔离实验工作流，不直接修改其 main；本知识库的记录和 TaskPlan 变更仍只提交到 `robot_knowledgebasement/main`。
- 不连接 CS9、不发送真实运动命令、不声称 HIL、SAT、实机或安全验收通过。


## 10. K-only 对照完成（Run #121 / Actions ID #43789238751）

为补齐 K+A=OFF+B=OFF 单元格，复用既有隔离工作分支 `experiment/moveit-main-owner-lifetime-only`，未新建分支、未修改 Stäubli driver main；仅修改临时 workflow 文件。

- workflow commit：`739afbbe2722ebd494326272ec298d896ab193c4`
- [Actions Run #121](https://github.com/rexyll/staubli_driver_ros2_from_org/actions/runs/43789238751)
- 配置：K=ON、A=OFF、B=OFF。
- 结果：build 成功；mock planning/trajectory execution 五轮成功；teardown 五轮 SIGSEGV，`failures=5/5`。
- Artifact：`14191994262`；日志 ZIP SHA-256：`f6017a6b71eaf73e13893d2f2f645ca2138b72cfac97a4cb9fb70f06f44d9182`。
- A 关闭：三个外部 owner reset 均不存在；B 关闭：TEM cleanup gate 为 `if False`；K 处理保留。

Run #121 补齐矩阵后，Run #107/#118/#119/#121 可按同一 K 背景形成完整 2×2 对照。每轮均可见 controller-manager DSO unload 先于 CallbackGroup/NodeBase 弱引用列表清理，后者崩溃。该结论不把具体 Waitable 动态类型或控制块回调归属写成已证明事实。


## 11. rclcpp callback-group / NodeBase 实际所有权补充（Jazzy 固定源码）

本轮进一步对照 ROS 2 rclcpp Jazzy 源码，确认 B 中必须分别治理 callback group 的强 owner、NodeBase 登记表和 Waitable 弱引用容器：

### 11.1 NodeBase 对 callback group 的持有方式

在 rclcpp Jazzy commit `35b821a9fb1f937bfbd9c741b7e3353e101d9593`：

- `NodeBase` 有一个强引用成员 `default_callback_group_`；
- 其他 callback groups 存入 `std::vector<CallbackGroup::WeakPtr> callback_groups_`，NodeBase 的登记向量本身不延长这些非默认 group 的生命周期；
- `create_callback_group()` 创建 shared_ptr 后将其推入 `callback_groups_`，再由调用方/相关组件维持真正的强引用。

证据：
- [node_base.hpp blob 6173a08](https://github.com/ros2/rclcpp/blob/35b821a9fb1f937bfbd9c741b7e3353e101d9593/rclcpp/include/rclcpp/node_interfaces/node_base.hpp#L154-L160)
- [node_base.cpp blob 5648290](https://github.com/ros2/rclcpp/blob/35b821a9fb1f937bfbd9c741b7e3353e101d9593/rclcpp/src/rclcpp/node_interfaces/node_base.cpp#L221-L226)

因此，TEM 为 event subscription 创建的非默认 callback group 必须由稳定 owner 持有，不能只依赖 NodeBase 的弱登记项。CI-only B treatment 把局部 `callback_group` 提升为 `event_callback_group_` 成员，正是为了让它能在明确安全的析构阶段释放。

### 11.2 CallbackGroup 对 Waitable 只保存 weak_ptr

同一 Jazzy commit 的 `CallbackGroup`：

- `waitable_ptrs_` 类型为 `std::vector<rclcpp::Waitable::WeakPtr>`；
- `add_waitable()` 仅保存 weak_ptr，并会清理当时已经 expired 的条目；
- `remove_waitable()` 遍历条目并先执行 `weak_ptr.lock()`，只有 lock 成功且指针相同才 erase；若对象已进入 expired 状态，该函数不能靠当前分支删除该条目；
- `CallbackGroup::~CallbackGroup()` 会触发 notify guard condition。

证据：
- [callback_group.hpp blob d8c529d](https://github.com/ros2/rclcpp/blob/35b821a9fb1f937bfbd9c741b7e3353e101d9593/rclcpp/include/rclcpp/callback_group.hpp#L297-L312)
- [callback_group.cpp blob 73cd458](https://github.com/ros2/rclcpp/blob/35b821a9fb1f937bfbd9c741b7e3353e101d9593/rclcpp/src/rclcpp/callback_group.cpp#L42-L45)
- [add_waitable / remove_waitable](https://github.com/ros2/rclcpp/blob/35b821a9fb1f937bfbd9c741b7e3353e101d9593/rclcpp/src/rclcpp/callback_group.cpp#L204-L226)

这为“Waitable 最后一个 strong owner 先释放、CallbackGroup 仍保留 expired weak control block、后续 group 析构释放 weak control block”的风险链提供了源码依据。它与历史 GDB 栈的 shared_ptr release / CallbackGroup teardown 现象吻合，但仍不能单凭此处源码锁定实际崩溃的唯一 Waitable 动态类型。

### 11.3 对 A+B 清理次序的精细解释

由以上源码可将生命周期约束拆为三个不同对象：

1. **Main MoveGroup Node / default group：** `NodeBase::default_callback_group_` 是强引用。A 的 `nh.reset()` 让 NodeBase 最终析构可跟随 MoveItCpp/TEM owner 收尾，而不是延迟到 MoveGroup capability loader 已 reset 之后。
2. **TEM event callback group：** 它是 main Node 的非默认 group，NodeBase 只弱登记；B 的 `event_callback_group_` 成员是明确强 owner，必须在 safe point 显式 reset。
3. **Controller-manager Node / default group：** 插件 instance 的 action clients / waitables 由 controller-manager node 的 callback-group / executor 关系管理。B 先停并销毁 private executor/WaitSet，再 reset plugin instance，最后 reset controller node；controller-manager loader 仍活着，直到 TEM 成员析构阶段。

### 11.4 已取得的 DSO / CallbackGroup runtime 顺序证据

Run #121 五轮 GDB/LD_DEBUG 日志均有如下顺序：

1. `calling fini: /opt/ros/jazzy/lib/libmoveit_simple_controller_manager.so`；
2. `destroying link map`，插件库已卸载；
3. private executor 析构日志出现；
4. `CallbackGroup::~CallbackGroup()` 清理 `std::vector<std::weak_ptr<rclcpp::Waitable>>`；
5. 在 `_M_weak_release` / `_M_release_last_use` 处 SIGSEGV，调用栈继续经过 `NodeBase::~NodeBase()`、`rclcpp::Node::~Node()`、TEM dtor 与 MoveItCpp dtor。

五轮中这一顺序一致。它证明了 DSO 卸载先于有关 Node/CallbackGroup 弱引用容器清理，并将失败位置从笼统 shared_ptr crash 缩小到 `controller_mgr_node_` 的默认 callback group/Waitable weak-entry 析构路径。它尚未证明是哪一个 Waitable 或哪个控制块虚函数触发无效跳转。

## 12. MoveIt Jazzy TEM 成员逆序析构：源码缺陷链

构造路径补充（Jazzy源码 trajectory_execution_manager.cpp L111–183）：initialize() 先创建 controller_manager_loader_（L114–117），然后创建独立 controller_mgr_node_（L164–171），通过 createUniqueInstance() 装载 plugin 并将该 node 传入 plugin initialize()（L177–178），之后创建 private_executor_、add_node(controller_mgr_node_) 并启动独立 spin thread（L179–183）。这确认 plugin manager 的 callback/waitable 资源与 controller node 的 NodeBase/default callback group 绑定，private executor 则持有该 node 的执行上下文。

### 12.1 rclcpp_action 的 Waitable removal 语义：expired weak entry 的确定性来源

进一步核对 ROS 2 rclcpp Jazzy commit 35b821a9fb1f937bfbd9c741b7e3353e101d9593 后，已能从源码串起具体 Waitable 生命周期：

1. moveit_simple_controller_manager 的 FollowJointTrajectory controller handle 在 action_based_controller_handle.hpp L84–89 调用 rclcpp_action::create_client<T>(node, action_name)，没有指定 callback group；ClientBase 在 rclcpp_action/client.hpp L62 继承 rclcpp::Waitable。
2. rclcpp_action/create_client.hpp L53–80 创建自定义 shared_ptr deleter；deleter 持有 weak_node，在 client 最后一个 strong owner 释放时先 weak_node.lock()，然后构造一个指向同一 raw pointer、但使用 no-op deleter 的 fake_shared_ptr，再调用 node_waitables_interface->remove_waitable(fake_shared_ptr, nullptr)，最后 delete ptr。L82–92 创建 action_client shared_ptr 并立即 add_waitable。
3. rclcpp/node_interfaces/node_waitables.cpp L29–41 在 add_waitable 的 group 参数为空时，将其替换为 node_base_->get_default_callback_group()，然后调用 group->add_waitable(waitable_ptr)。因此该 Action Client 的 control block 被记录在 controller_mgr_node_ 的默认 CallbackGroup weak list 中。
4. deleter 调用 remove_waitable 时，原 shared_ptr 的 strong count 已经到 0，原 weak entry 的 lock() 不能再返回对象。node_waitables.cpp L54–65 将 null group 路由回默认组；callback_group.cpp L218–228 对每个 entry 执行 weak_ptr.lock()，只有 lock 成功且 raw pointer 相等才 erase；没有处理 expired entry 的 erase 分支。fake_shared_ptr 虽然 raw pointer 相同，但有独立 control block，无法让原 weak entry.lock() 成功。
5. 因此该 Action Client 的 deleter 执行时会留下 expired weak_ptr entry。add_waitable() 会在后续新增 Waitable 时顺便清理当时已过期的 entries；但在 controller-manager teardown 中，这些 Action Client 是初始化阶段创建、退出阶段集中释放，之后不再新增 Waitable，所以最终释放的条目没有后续 add_waitable() 帮忙清理，会一直保留到 CallbackGroup 的 waitable_ptrs_ vector 析构/显式清空时才触发最后 weak release。

关键源码：
- [FollowJointTrajectory handle create_client 调用](https://github.com/moveit/moveit2/blob/jazzy/moveit_plugins/moveit_simple_controller_manager/include/moveit_simple_controller_manager/action_based_controller_handle.hpp#L84-L90)
- [ClientBase 继承 Waitable](https://github.com/ros2/rclcpp/blob/35b821a9fb1f937bfbd9c741b7e3353e101d9593/rclcpp_action/include/rclcpp_action/client.hpp#L62-L66)
- [rclcpp_action custom deleter 与 add_waitable](https://github.com/ros2/rclcpp/blob/35b821a9fb1f937bfbd9c741b7e3353e101d9593/rclcpp_action/include/rclcpp_action/create_client.hpp#L53-L92)
- [NodeWaitables 默认 callback group 路由](https://github.com/ros2/rclcpp/blob/35b821a9fb1f937bfbd9c741b7e3353e101d9593/rclcpp/src/rclcpp/node_interfaces/node_waitables.cpp#L29-L65)
- [CallbackGroup remove_waitable 仅在 weak lock 成功时 erase](https://github.com/ros2/rclcpp/blob/35b821a9fb1f937bfbd9c741b7e3353e101d9593/rclcpp/src/rclcpp/callback_group.cpp#L218-L228)

**结论边界：** expired weak entry 留存在默认 CallbackGroup 的机制已由源码确定；这解释了为何 plugin instance 已经释放后，control block 仍可能在 NodeBase/CallbackGroup 析构时才释放。该 control block 的虚表/销毁函数是否来自 libmoveit_simple_controller_manager.so，仍由 Run #122 的 GDB 控制块地址与进程映射来验证，暂不写成已证实。

### 12.2 plugin manager 与 handle 的真实析构顺序

MoveIt Jazzy moveit_simple_controller_manager 源码进一步确认：MoveItSimpleControllerManager 的析构函数是 defaulted（moveit_simple_controller_manager.cpp L95–100）；其成员 node_ 位于 L328，controllers_ map 位于 L329。按 C++ 成员逆序析构，controllers_ map 先销毁，plugin manager 自己持有的 node_ 最后销毁。controllers_ 中的每个 handle 都持有 Action Client；ActionBasedControllerHandle 的 node_ 成员在 L189，controller_action_client_ 成员在 L270，Action Client 本身在 L88 通过 rclcpp_action::create_client 创建。

因此实际运行顺序是：plugin manager 析构开始 → controllers_ map 销毁各 FollowJointTrajectory handle → Action Client 最后强引用归零并运行 custom deleter → deleter 尝试从仍存活的 controller_mgr_node_ 默认 CallbackGroup 移除 Waitable（但原 weak_ptr.lock() 已失败）→ control block 留在 CallbackGroup weak list → handle/plugin manager 完成析构 → TEM 的 controller_manager_ owner 释放 → ClassLoader unload plugin DSO → TEM 更晚才销毁 controller_mgr_node_ / NodeBase / default CallbackGroup 并释放 retained weak control block。

该顺序把 rclcpp_action 的 expired weak-entry 缺口与 MoveIt TEM 的 plugin loader/node member-order 冲突直接连接起来。当前唯一尚未由源码本身确认的是原 shared_ptr control block 的 _M_destroy / vtable 运行地址是否确实落在 libmoveit_simple_controller_manager.so；Run #122 GDB 对具体 weak slot 的 crash frame 和内存映射将完成这最后一环。

- [MoveItSimpleControllerManager default destructor 与 controllers_ 成员](https://github.com/moveit/moveit2/blob/jazzy/moveit_plugins/moveit_simple_controller_manager/src/moveit_simple_controller_manager.cpp#L95-L104)
- [controller manager 的 node_ / controllers_ 成员声明](https://github.com/moveit/moveit2/blob/jazzy/moveit_plugins/moveit_simple_controller_manager/src/moveit_simple_controller_manager.cpp#L324-L335)
- [ActionBasedControllerHandle 的 node_ 与 Action Client 成员](https://github.com/moveit/moveit2/blob/jazzy/moveit_plugins/moveit_simple_controller_manager/include/moveit_simple_controller_manager/action_based_controller_handle.hpp#L184-L197)
- [Action Client member](https://github.com/moveit/moveit2/blob/jazzy/moveit_plugins/moveit_simple_controller_manager/include/moveit_simple_controller_manager/action_based_controller_handle.hpp#L263-L272)

读取 MoveIt `jazzy` 源码：

- [`trajectory_execution_manager.hpp`](https://github.com/moveit/moveit2/blob/jazzy/moveit_ros/planning/trajectory_execution_manager/include/moveit/trajectory_execution_manager/trajectory_execution_manager.hpp) 声明顺序为：`node_`（约第302行）、`controller_mgr_node_`（304）、`private_executor_`（305）、`event_topic_subscriber_`（309）、`controller_manager_loader_`（331）、`controller_manager_`（332），`callback_handler_` 位于更后部。
- [`trajectory_execution_manager.cpp`](https://github.com/moveit/moveit2/blob/jazzy/moveit_ros/planning/trajectory_execution_manager/src/trajectory_execution_manager.cpp) 的 `~TrajectoryExecutionManager()`（约第86–93行）只执行 `stopExecution(true)`、cancel private executor、join private executor thread；没有在析构函数体内提前 reset node 或 loader。

C++ 类成员按声明的逆序析构。因此 stock TEM 在析构函数体之后会先销毁 `controller_manager_`，然后销毁 `controller_manager_loader_`（卸载 `libmoveit_simple_controller_manager.so`），之后才销毁更早声明的 subscription、private executor/WaitSet、`controller_mgr_node_` 和 `node_`。这与 Run #121 五轮实际观测到的 DSO `fini` / link-map destruction 早于 executor、NodeBase/CallbackGroup weak-list teardown 的顺序直接吻合。

`CallbackGroup::waitable_ptrs_` 是 `WeakPtr` 列表。若某些 Waitable 的 shared control block 需调用插件 DSO 中的 destroy/deallocate 代码，则在 DSO 卸载后才释放最后 weak reference 会造成无效代码指针；这是一条与当前 SIGSEGV 完全吻合的机制解释，但仍需对具体 control block / Waitable 动态类型做运行时归属验证。

**当前最强根因判断：** TEM 原始成员声明顺序允许 controller-manager DSO 在其 NodeBase/default callback group/WaitSet 相关对象完成析构之前卸载；外层 MoveGroup owner 生命周期（A）又决定 TEM/MoveItCpp 最终析构是否推迟到 capability loader teardown 之后。A 与 B 分别治理外层 owner 时机和 TEM 内部资源顺序，二者组合才在当前 mock CI 下通过。

## 13. A+B 实际析构诊断（Run #122）

在 A+B 正向候选中新增 CI-only rclcpp 诊断：NodeBase destructor 入口/主体结束标记；CallbackGroup destructor 对 waitable_ptrs_ 中每个 weak_ptr 逐项打印槽位、expired 状态和 use_count，并分别输出释放前/后的标记；TEM cleanup 在 controller_mgr_node_.reset() 前打印 use_count，并在 node reset 返回后显式 reset controller_manager_loader_。此运行旨在验证 NodeBase/default callback group/Waitable weak entries 是否真正先于 plugin DSO unload 释放；若发生崩溃，可从最后一个 BEGIN 而没有 END 的槽位确定具体 weak entry。

- [Actions Run #122](https://github.com/rexyll/staubli_driver_ros2_from_org/actions/runs/43791758924)
- workflow commit：c81546100ed5a91110e57ca56488f7d6911fa31f
- 最终结果：构建成功；5/5 mock plan-and-execute 均 SUCCEEDED，5/5 teardown 均 PASS；test summary 为 7 tests、0 errors、0 failures。五轮均观测到 controller node NodeBase/default CallbackGroup 的 expired weak Waitables 逐项释放后，才 reset loader 并由 LD_DEBUG 记录 plugin DSO fini/link-map destruction。
- 该逐项 weak_ptr reset 仅用于 CI 观测，可能轻微改变 destructor 内部时序；必须与未插桩 A+B Run #107 的 5/5 正向结果共同解释。

若 Run #122 证明最后 weak release 与 controller-manager DSO 卸载有关，下一项反证实验将固定 K-only（A=OFF/B=OFF），只在临时 rclcpp overlay 的 CallbackGroup::remove_waitable() 中增加 expired weak_ptr pruning：对 weak_ptr.lock() 失败的条目执行 erase，再按原逻辑匹配 live target。该修改只清理已经失去 strong owner 的 Waitable 记录，目标是让其 control block 在 plugin custom deleter 返回前释放，从而测试此单点是否足以消除 K-only teardown SIGSEGV；不提交上游，不修改产品源码。

## 14. 下一步最小变量实验

1. 先在 A+B 正向候选加 CI-only destructor markers，记录 `controller_manager_` instance dtor、private executor/WaitSet 完成、`controller_mgr_node_`/NodeBase/default callback group 完成、`controller_manager_loader_` reset/DSO unload 的真实顺序。对最后一个强 owner 释放使用 `use_count` 和 destructor marker 双重检查。
2. 固定 A=ON、K=ON，先验证 B 中 controller-manager 核心生命周期链的最小集合：停止并 join private executor、从 executor 移除 node、销毁 executor/WaitSet、销毁 controller-manager instance、销毁 controller-manager node，确保所有上述步骤在 loader unload 前完成；保留 event subscription/callback group 清理为独立变量，不一次性全部捆绑。
3. 再单项隔离 B 的 event subscription、parameter callback、event callback group，并保持 controller-manager node 核心清理不变。
4. 最后固定 B=ON，依次隔离 A 的 PSM、MoveItCpp、main Node reset；每次只变一个变量。
5. 对 `execution_complete_`、`last_execution_status_`、`execution_thread_`、`preempt_requested_` 的同步审计及 TSAN 独立推进；Run #117 的 always-join 只覆盖 missed-join 窗口。

任何实验仍限 CI temporary overlay/mock；不修改 upstream 或产品源码，不连接 CS9、不发送真实运动命令、不宣称 HIL/SAT/实机验收。


## 15. Run #122 A+B 实际析构顺序结果与 K-only pruning 反证

### 15.1 Run #122 最终结果

[Actions Run #122](https://github.com/rexyll/staubli_driver_ros2_from_org/actions/runs/43791758924)（workflow commit `c81546100ed5a91110e57ca56488f7d6911fa31f`）最终完成成功：

- rclcpp Jazzy lifecycle-marker overlay、MoveIt Jazzy candidate、Stäubli mock workspace 均构建成功。
- 5/5 次 mock plan-and-execute 均报告 `Completed trajectory execution with status SUCCEEDED`。
- 5/5 teardown 均完成，汇总 `failures=0/5`；workflow test summary 为 7 tests、0 errors、0 failures。
- Artifact ID：`14192853671`；SHA-256：`6958f483320fff3c93b3d432d0ca61f5d2f8d19030f28f8c6055a76cef5e5266`。

五轮诊断的共同顺序为：

1. TEM 等待 execution thread 退出，`active_handles_after_stop=0`。
2. 显式释放 event subscription / callback group / private executor。
3. `controller_mgr_node_.use_count()==1` 后调用 `controller_mgr_node_.reset()`。
4. controller node 的 NodeBase destructor 进入；五轮目标默认 CallbackGroup 均记录 `waitables=5`，每轮五条 weak Waitable 都是 `expired=1, use_count=0`，并逐项完成 reset/erase。
5. TEM 随后才调用 `controller_manager_loader_.reset()`；LD_DEBUG 随后记录 `libmoveit_simple_controller_manager.so` 的 `calling fini` 与 `destroying link map`。

这直接验证了 A+B 候选中 controller node/default CallbackGroup cleanup 先于该 controller-manager DSO unload。它没有直接证明 stock K-only 一定崩溃就是某个 DSO 内的 control-block destructor 被调用，也没有确认 Waitable 的具体动态类型。

### 15.2 尚未关闭的证据缺口

Run #122 日志未包含 control-block vtable、`_M_destroy` 或 deallocate 函数地址与进程映射的对应信息。进程在正常完成 teardown 后，GDB 的 `No stack` / `No registers` 输出属于退出后的查询，不可误记为 crash frame。因此“控制块释放函数来自 `libmoveit_simple_controller_manager.so`”仍是未证实假设，必须单独测量。

### 15.3 K-only + expired-entry pruning 单点反证

在原有实验分支 `experiment/moveit-main-owner-lifetime-only` 启动 K-only 反证；A=OFF、B=OFF，保留既定 K 背景（PSM publisher stop/join 与 MoveGroupExe/executor scope ordering）。唯一功能性处理是在临时 rclcpp overlay 的 `CallbackGroup::remove_waitable()` 中：

- `weak_ptr.lock()` 失败时，erase 该 expired weak Waitable entry；
- 对仍能 lock 的 live entry，继续原有 raw pointer 比较和删除逻辑；
- 每次 pruning 打印 marker，并以每轮至少出现一次 marker 作为有效覆盖条件。

正确配置运行：

- [Run #124](https://github.com/rexyll/staubli_driver_ros2_from_org/actions/runs/43794205250)，commit `e982788ac7446a8ad5f8bf6ebb2a4e814b2a7763`：rclcpp overlay build 成功；MoveIt step 因跨 Actions step 引用未持久化的 Python 局部变量 callback_group_source 触发 NameError，未进入 MoveIt build/mock test；artifact 14193264720。
- [Run #125](https://github.com/rexyll/staubli_driver_ros2_from_org/actions/runs/43794278705)，commit `3f85d2a9063083e895a3dee2f67f7c353a09f840`：同一跨步骤 NameError，未进入 MoveIt build/mock test；artifact 14193518313。
- [Run #126](https://github.com/rexyll/staubli_driver_ros2_from_org/actions/runs/43794655028)，commit `7d0aa0d6b571323d85a181d5ec7d24371288fed9`：rclcpp overlay、patched MoveIt（7 packages）、Stäubli mock workspace（5 packages）均构建成功；但 test step 未切换到 `/tmp/staubli_ws`，五轮均报 unknown package、0 packages/0 tests/0 pruning，属 no-op；artifact 14193853443。
- [Run #127](https://github.com/rexyll/staubli_driver_ros2_from_org/actions/runs/43798751700)，commit `2c578fa670b0d5c9bf845c53591cbc334f952438`：已在 test step 加 `cd /tmp/staubli_ws`、`ros2 pkg prefix` 与 `colcon list` 预检，正在执行。

Run #123–#125 为 workflow 配置错误；Run #126 为测试工作目录错误导致的 no-op；均不产生有效 teardown 反证数据。不得将其计入功能性通过/失败统计。

### 15.4 判定规则

- 若实际触发 pruning 的 K-only 5/5 teardown 通过，说明该单点在当前 mock CI 条件下足以消除本复现；仍需重复、核验 live Waitables 不被误删，并继续确认 control-block destroy/deallocate 归属。
- 若有效 pruning 仍 5/5 失败，则 expired-entry pruning 不是充分解释/修复，回到 plugin DSO、control block allocator、executor WaitSet 与 TEM member order 的交互定位。
- 若某轮没有 pruning marker，该轮没有覆盖目标处理路径，不能作为有效反证。
- 不把 CI temporary overlay 视为 upstream patch；不修改 upstream MoveIt/rclcpp 或 Stäubli 产品源码，不连接 CS9，不发送真实运动命令，不宣称 HIL/SAT/实机验收。


## 16. Run #126 no-op 归因与 #127 工作目录预检

### 16.1 Run #126 构建结果

Run #126（[Actions](https://github.com/rexyll/staubli_driver_ros2_from_org/actions/runs/43794655028)，commit `7d0aa0d6b571323d85a181d5ec7d24371288fed9) 前半程全部成功：

- rclcpp overlay build 成功；
- K-only MoveIt patch 与 static validation 成功；
- patched MoveIt build 成功，7 packages finished；
- Stäubli mock workspace build 成功，5 packages finished，其中日志明确记录 `Starting >>> staubli_moveit_config` 和 `Finished <<< staubli_moveit_config`。

### 16.2 test step no-op 根因

GitHub Actions 的每个 step 都是独立 shell。Run #126 test step 虽 source 了 ROS/rclcpp/MoveIt/Stäubli overlays，却没有重新执行 `cd /tmp/staubli_ws`。因此 `colcon test --packages-select staubli_moveit_config` 从 runner 默认目录扫描 package，五轮均出现：

- `ignoring unknown package 'staubli_moveit_config'`；
- `Summary: 0 packages finished`；
- `Summary: 0 tests, 0 errors, 0 failures`；
- `expired_entries_pruned=0`。

脚本因总 pruning 数为 0 正确以 exit code 1 退出。该失败是 test-step 工作目录漏切换造成的 no-op，不是 C++ 编译或 runtime teardown 失败，也不是有效 pruning 治理下的反证结果。Artifact ID `14193853443`，SHA-256 `6e6e709b1e3fc0a4a247e0a21214a07cda9354944a906fd81c69bc8c8ceca72d`。

### 16.3 Run #127 修正

在同一既有实验分支（未创建新分支）对 workflow 增加 test-step workspace preflight：

1. `cd /tmp/staubli_ws`；
2. `ros2 pkg prefix staubli_moveit_config`，并确认返回 prefix 目录存在；
3. `colcon list --base-paths src | awk '{print $1}' | grep -Fx staubli_moveit_config`；
4. 任一预检失败则停止测试；只有目标 package 可见时才进入五轮循环。

修正 commit：`2c578fa670b0d5c9bf845c53591cbc334f952438`；[Run #127](https://github.com/rexyll/staubli_driver_ros2_from_org/actions/runs/43798751700) 已触发。

### 16.4 有效反证判据

每轮必须真实发现并执行 `staubli_moveit_config` launch test；不得接受 `0 packages` 或 `0 tests`。每轮须记录 action `SUCCEEDED`、teardown exit status、至少一个 pruning marker，并核查 pruning 的 group address 是否对应目标 NodeBase default CallbackGroup。缺少任一证据则该轮不是有效反证。K-only pruning 成功也仅限当前 mock CI，不等同 upstream/产品修复。
