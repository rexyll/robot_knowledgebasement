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
