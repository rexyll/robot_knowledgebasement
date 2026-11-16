# Stäubli MoveIt teardown 生命周期 A/B 单因子消融与组合对照（Run #107 / #118 / #119）

**记录日期：** 2026-11-16  
**目标仓库：** `rexyll/robot_knowledgebasement`  
**被测工程：** `rexyll/staubli_driver_ros2_from_org`  
**状态：** 在共同实验背景 K 下，A-only 与 B-only 两项消融各 5/5 teardown 失败，A+B 组合 Run #107 5/5 通过。当前证据支持继续保留 A+B 组合候选，但尚缺 K+A=OFF+B=OFF 的同基线对照，因此这不是完整 2×2 因子实验。  
**边界：** 所有源码改动均通过 GitHub Actions 在临时 MoveIt/rclcpp overlay 中注入；不是 MoveIt、rclcpp 或 Stäubli 产品源码修复，也不构成 CS9、HIL、SAT 或真实机器人验收。

## 1. 先纠正实验矩阵的命名

上一版把历史 Run #73 与 Run #118/#119/#107 合并写成“2×2 因子实验”。进一步核对三个 workflow commit 后，需要收窄这一表述：

- Run #118、#119、#107 都启用了相同的共同背景 K；
- 三次运行分别覆盖 K+A、K+B、K+A+B；
- 历史 Run #73 没有采用相同的 PSM publisher stop 与 MoveGroupExe/executor 作用域顺序，不能作为严格同基线的 K+A=OFF+B=OFF 单元格。

因此，本报告将结果称为**共同基线下的三组单因子消融/组合对照（partial factorial ablation）**。历史 Run #73 只作为较早的崩溃基线，不用于填补缺失的 K-only 对照。

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

## 4. 当前有效的三组结果

| Run | 共同背景 K | A：主作用域 owner reset | B：TEM 显式 cleanup | 结果 |
|---|---|---:|---:|---|
| #118 main-owner-only | ON | ON | OFF | **5/5 FAIL** |
| #119 TEM-cleanup-only | ON | OFF | ON | **5/5 FAIL** |
| #107 combined | ON | ON | ON | **5/5 PASS** |

- [Run #118](https://github.com/rexyll/staubli_driver_ros2_from_org/actions/runs/43684020993)：workflow commit `0420f0259d652ca01b3d2e26cce26a3d45dfe73e`，artifact ID `14149678145`。
- [Run #119](https://github.com/rexyll/staubli_driver_ros2_from_org/actions/runs/43684023847)：workflow commit `8218084250c9c45fe275f7729ae98f59792a422b`，artifact ID `14149932259`。
- [Run #107](https://github.com/rexyll/staubli_driver_ros2_from_org/actions/runs/43677374898)：workflow commit `18fea00298ee542c304cbf73d652cd540262712e`，A+B 组合下正常 mock 轨迹执行及 teardown 5/5 通过。
- [Run #117](https://github.com/rexyll/staubli_driver_ros2_from_org/actions/runs/43683012297)：A+B 组合背景下，always-join CI-only candidate 的自然完成/取消 barrier 回归 5/5 通过。

三项 workflow 的 source overlay、patched MoveIt move_group 和 Stäubli mock workspace 均完成构建。#118/#119 失败发生于最后的 mock 执行及 teardown 回归，不是编译失败。

## 5. 失败和通过的日志证据

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

## 6. 2×2 因果解释的边界

现有证据允许作出以下有限判断：

- K+A+B 能通过当前 5 轮 mock execution + teardown；
- K+A（B=OFF）失败；
- K+B（A=OFF）失败；
- 因此在当前固定测试输入下，A 与 B 两组处理都对组合通过有贡献，不能把任一单因子方案作为可接受修复。

但缺少同一 K 背景下的 `K + A=OFF + B=OFF` 对照，因此：

- 不应将 #73 直接写成完整因子矩阵的 0/0 单元格；
- 暂不估计 A/B 的独立主效应或交互效应；
- 不声称已证明 PSM publisher stop 或 executor/MGE 声明顺序各自必要；
- 不声称 A 内部三个 reset 的每一个都已被单独证明必要；
- 不把 `shared_ptr::_M_release_last_use` 的顶层栈帧等同于已经确认某个具体 Waitable/control-block 动态类型。

## 7. 下一步实验设计（不触碰产品源码）

按最低改动、最高信息增益推进：

### 7.1 先补齐共同背景 K 的 0/0 对照

新增一个仅在临时 CI overlay 执行的 K-only case：保留 PSM publisher stop、MoveGroupExe-before-executor 作用域顺序与现有 diagnostic markers；关闭 A 的三个 external-owner reset，也关闭 B 的 TEM 显式 cleanup。使用与 #107/#118/#119 相同的 Stäubli source pin、mock trajectory execution test、重复次数、GDB/LD_DEBUG 参数和 strict process-exit assertion。

该组结果决定 K-only 是否本身已足够或会复现崩溃；完成后才有完整的 2×2 数据。

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


## 10. K-only 对照已触发（Run #43789238751，结果待验）

为补齐 K+A=OFF+B=OFF 单元格，已复用既有隔离工作分支 `experiment/moveit-main-owner-lifetime-only`，没有新建分支，也没有修改 Stäubli driver main。仅修改该分支的 GitHub Actions workflow 文件：

- commit：`739afbbe2722ebd494326272ec298d896ab193c4`
- [Run #43789238751](https://github.com/rexyll/staubli_driver_ros2_from_org/actions/runs/43789238751)
- 配置：K=ON、A=OFF、B=OFF。
- A 关闭核验：workflow 中不再有 `planning_scene_monitor.reset()`、`moveit_cpp.reset()`、`nh.reset()`，恢复 stock main() 局部 shared-owner 生命周期。
- B 关闭核验：TEM cleanup 注入 gate 为 `if False`，不改 TEM 析构函数。
- K 保留核验：仍在 Context shutdown 前停止 PSM scene publisher；仍将 MoveGroupExe 声明在 MultiThreadedExecutor 之前；仍保留 stock signal handling 检查和相同 mock plan/execute + strict teardown workflow。

**最新状态：** Run #43789238751 已由 push 事件创建，job `source-overlay-regression` 处于运行中；首次查询时容器初始化步骤尚在进行，尚未进入 ROS Jazzy / rclcpp / MoveIt 构建阶段。GitHub 尚未提供可下载 job log/artifact，因此当前没有 K-only 编译或测试结果，不能标记 PASS/FAIL。

这项运行只验证共同背景 K 是否能单独通过；其结果将决定后续 A/B 因子矩阵如何解释。不得在运行完成前把它计入成功或失败样本。


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

### 11.4 下一步新增运行时观测点

K-only 运行之后，再在 A+B 候选中加入 CI-only markers（不改产品源码）：

- event callback group 析构时间；
- controller-manager node default group 析构时间；
- controller-manager instance 析构完成点；
- private executor destructor body END 与 WaitSet 成员销毁之后的标记；
- controller-manager DSO `LD_DEBUG` unload 时间；
- main NodeBase / default callback group 析构时间。

验收要求是这些 group/node/WaitSet 的实际析构均发生在对应 plugin DSO 卸载之前。单纯观察 `reset()` 调用日志不足以证明对象真的在该行完成最后释放（可能存在其他 shared owners）。
