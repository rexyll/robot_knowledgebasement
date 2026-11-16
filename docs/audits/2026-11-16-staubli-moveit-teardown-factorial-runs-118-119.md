# Stäubli MoveIt teardown 生命周期 2×2 隔离实验结果（Run #118 / #119）

**记录日期：** 2026-11-16  
**目标仓库：** `rexyll/robot_knowledgebasement`  
**被测工程：** `rexyll/staubli_driver_ros2_from_org`  
**状态：** 两个单因子实验均已完成并各自 5/5 失败；组合 A+B 的既有 Run #107 5/5 通过。当前结论为：在本次 MoveIt Jazzy + ROS 2 Jazzy + Stäubli mock CI 场景中，两层 owner 生命周期处理必须组合，单独启用其中一层不足以消除 teardown SIGSEGV。  
**边界：** 全部修改均为 GitHub Actions 临时源码 overlay / 测试诊断，不是 MoveIt、rclcpp 或 Stäubli 产品源码修复；不构成 CS9、HIL、SAT 或真实机器人验收。

## 1. 实验矩阵与结论

| Run | 主作用域提前释放 MoveItCpp / PSM / node（A） | TEM 显式清理 controller-manager owner（B） | 结果 |
|---|---:|---:|---|
| #73 baseline | OFF | OFF | 既有 teardown SIGSEGV 基线 |
| #118 main-owner-only | ON | OFF | **5/5 FAIL** |
| #119 TEM-cleanup-only | OFF | ON | **5/5 FAIL** |
| #107 combined | ON | ON | **5/5 PASS**，mock 执行与退出清理通过 |

- [Run #118](https://github.com/rexyll/staubli_driver_ros2_from_org/actions/runs/43684020993)：workflow commit `0420f0259d652ca01b3d2e26cce26a3d45dfe73e`，分支 `experiment/moveit-main-owner-lifetime-only`，artifact ID `14149678145`。
- [Run #119](https://github.com/rexyll/staubli_driver_ros2_from_org/actions/runs/43684023847)：workflow commit `8218084250c9c45fe275f7729ae98f59792a422b`，分支 `experiment/moveit-tem-cleanup-only`，artifact ID `14149932259`。
- [Run #107](https://github.com/rexyll/staubli_driver_ros2_from_org/actions/runs/43677374898)：A+B 同时启用的既有 5/5 正常 mock trajectory execution + teardown 证据。另有 [Run #117](https://github.com/rexyll/staubli_driver_ros2_from_org/actions/runs/43683012297) 对 CI-only always-join 候选做了 5/5 barrier-controlled mock 回归。

两项隔离实验的构建路径均成功：ROS Jazzy / rclcpp overlay、patched MoveIt move_group、Stäubli mock workspace 均完成构建。失败发生在最后的 mock planning / trajectory execution / teardown 回归阶段，而非编译阶段。

## 2. 两项失败的共同表现

日志逐轮显示：

- 两项实验均完成 5 次 mock trajectory execution；每个重复中控制器报告 `Goal reached, success!`，TEM 报告 `Completed trajectory execution with status SUCCEEDED`。
- 五轮均在 move_group 退出清理时触发 `SIGSEGV`，GDB 栈顶位于 `std::_Sp_counted_base::_M_release_last_use`（`shared_ptr_base.h:172`）。
- launch shutdown 断言随后观察到 GDB 子进程退出码 255；最终两项 workflow 均报告 `failures=5/5`。
- 因而本轮失败不属于轨迹 action 执行失败，也不能用控制器 Goal 成功抵消进程 teardown 失败。验收结果仍为 FAIL。

## 3. Run #118：只启用主作用域 owner 提前释放

**配置：** A=ON、B=OFF。

首轮日志中的关键顺序：

1. PlanningSceneMonitor scene publisher 停止并 join；
2. Executor 析构函数体结束；
3. MoveGroupExe 析构开始，随后执行 `capabilities_.clear()`；
4. `MoveItCpp` 开始析构；
5. `libmoveit_simple_controller_manager.so` 开始 fini / 卸载；
6. 后续 Executor / WaitSet owner 清理期间出现 `shared_ptr::_M_release_last_use` SIGSEGV。

五轮均复现相同的 teardown 失败族。该结果说明：即使主作用域提前释放 MoveItCpp / PSM / node 并调整外层 owner 作用域，仅此一项仍不足以保证 TEM 内部 controller-manager action-client / CallbackGroup / Waitable 生命周期在插件 DSO 卸载前结束。

**解释边界：** 日志将崩溃定位在 shared_ptr control-block 释放路径，并显示 controller-manager DSO 卸载时序；没有完成 control-block 动态类型的完整 RTTI / 符号归属确认，故不把具体残留对象名称写成已证实事实。

## 4. Run #119：只启用 TEM 内部显式清理

**配置：** A=OFF、B=ON。

TEM teardown instrumentation 在各轮记录到：

- `execution_thread_joinable=0`；
- `active_handles_after_stop=0`；
- event subscription 已 reset；
- callback group 已 reset；
- controller-manager instance 已 reset；
- controller node 已 reset。

但本配置不提前释放主作用域中的 MoveItCpp / PSM / node 外部 shared owners。首轮日志显示 MoveGroupExe 的 capability/context 清理及 capability plugin loader reset 先于随后发生的 MoveItCpp / TEM 最后释放；在 TEM 完成 controller node reset、`libmoveit_simple_controller_manager.so` 开始卸载以及剩余 Executor / WaitSet 清理之后，move_group 仍在 shared_ptr 释放路径 SIGSEGV。五轮均失败。

该结果说明：TEM 内部清理即使按候选顺序执行，并确认线程不再 joinable、active handles 为空，也不足以替代主作用域对 MoveItCpp / TEM 最后释放时机的约束。外层 capability loader 的生命周期与 TEM 内层 controller-manager loader 生命周期是两个不同 owner 边界，不能只治理其中一个。

## 5. 2×2 结果解释

在本次固定测试输入和当前两个 factor 定义下：

- A 单独启用（#118）不够；
- B 单独启用（#119）不够；
- A+B 组合（#107）在相同 mock 集成测试族上通过 5/5；
- 因此当前采用 A+B 组合候选继续做后续验证，不接受任一单因子作为可合并修复。

这构成“两个层级的 owner 生命周期处理需要组合”的实验性证据；不等于已经识别所有残留 shared_ptr 的精确动态类型，也不排除 A 或 B 内部还有更小的必要子步骤。若后续要缩小改动，应在保留失败基线和 A+B 正向对照的前提下，对 A、B 内部子步骤继续做单变量实验。

## 6. 下一步任务与门禁

1. **保留 A+B 组合为唯一当前有效的 CI-only teardown 候选。** 不将 #118 或 #119 单因子分支/补丁作为通过方案，不将 mock PASS 宣称为 upstream 已修复。
2. 对 A 边界建立 owner 释放断言：MoveGroupExe capability loader reset 前，确认其 context reset 已导致 MoveItCpp / TEM 最后 owner 按预期释放；并对 executor / WaitSet 真实析构时间线打点。
3. 对 B 边界保留 TEM 顺序：停止并 join private executor；reset event subscription / callback group；移除并销毁 private executor；reset controller-manager instance；reset controller node；controller-manager loader 最后卸载。对 active handles 和未执行 trajectories 的边界继续覆盖。
4. 继续完成 `execution_complete_`、`last_execution_status_`、`execution_thread_`、`preempt_requested_` 的访问域与锁策略审查；always-join 候选通过 #117 只覆盖已复现的 missed-join 窗口，不代表 TSAN / 全字段无数据竞争。
5. 保留原始崩溃栈、LD_DEBUG DSO unload 顺序及每轮 lifecycle marker；必要时再设计对照组，避免改变测试输入、执行轨迹或控制器预停机状态。
6. 在取得明确授权前，不修改 MoveIt / rclcpp upstream，不对 Stäubli 产品源码或 PR #1 作修复性提交，不连接 CS9、不发送真实运动命令、不宣称 HIL / SAT / 实机通过。

## 7. 独立诊断项

`controller_manager.pal_statistics` 在 ROS Context invalid 后出现 `context cannot be slept with because it's invalid!. Aborting!`，应继续作为 shutdown 诊断记录。现有资料已将该文本与 MoveGroup Waitable / shared_ptr SIGSEGV 区分；不要把它作为本轮 SIGSEGV 根因，也不要用其非致命性掩盖上述失败。

## 8. 证据链接

- Run #118：<https://github.com/rexyll/staubli_driver_ros2_from_org/actions/runs/43684020993>
- Run #119：<https://github.com/rexyll/staubli_driver_ros2_from_org/actions/runs/43684023847>
- A+B 正向对照 Run #107：<https://github.com/rexyll/staubli_driver_ros2_from_org/actions/runs/43677374898>
- always-join barrier regression Run #117：<https://github.com/rexyll/staubli_driver_ros2_from_org/actions/runs/43683012297>
- 上一轮静态所有权审计及 missed-join 溯源：<https://github.com/rexyll/robot_knowledgebasement/blob/main/docs/audits/MoveIt-TEM-teardown-lifecycle-audit-2026-11-15.md>
