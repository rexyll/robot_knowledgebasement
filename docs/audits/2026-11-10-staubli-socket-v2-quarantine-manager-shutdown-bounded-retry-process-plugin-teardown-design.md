# Stäubli SocketV2 QuarantineManager shutdown contract、有界重试调度与 process/plugin teardown 资源释放策略设计

- **节点：** §9.3.297 / SERVO-880
- **日期：** 2026-11-10
- **固定上游基线：** `ICube-Robotics/staubli_driver_ros2@bd658e2d266e315d2ee35f985fb352ea88306b79`
- **前置设计：** §9.3.295 / SERVO-878；§9.3.296 / SERVO-879。
- **性质：** 生命周期与调度策略静态设计稿；不是实现，不构成运行时、操作系统或插件卸载验证证据。

## 1. 目标与不可破坏的安全属性

本节点将 QuarantineManager 从“保存 residual owner 的容器”进一步定义为有明确关闭协议、有限调度预算和可审计退出结果的生命周期子系统。需要同时解决 manager 自身的关闭顺序、残留资源的重试策略、进程终止策略，以及 ROS component/plugin 卸载时 callback code 与 Core owner 的耦合问题。

必须保持以下不变量：

1. **不丢失 owner：** 只要 native handle、pending handler、active callback 或 worker 仍可能存活，就不得把 entry 标记为 COMPLETE 或释放最后一个 Core owner。
2. **有界等待不等于安全完成：** deadline 到期只结束本轮等待/重试预算，不得跳过 join、detach worker、伪造 quiescence 或释放 owner。
3. **不无限重试：** 每个 entry、每个 manager shutdown 都有最大尝试次数、最大总时间和全局并发上限；达到预算后进入 EXHAUSTED/RETAINED 状态并输出诊断。
4. **不在 worker 自身线程销毁最后 owner：** manager shutdown 由外部 lifecycle thread 发起；禁止 self-join、detach 和 worker-thread last-owner destruction。
5. **插件代码先静默、再卸载：** 只要 callback/vtable/deleter/handler 仍可能执行 plugin image 中的代码，就不能 unload 对应 shared library。
6. **进程退出必须显式分类：** 只有确认所有资源满足稳定终态才能报告 CLEAN；否则报告 RESIDUAL_RETAINED 或 FORCED_PROCESS_EXIT，不得把操作系统进程结束等同于应用层 graceful cleanup。

## 2. 所有权与组件职责

建议的逻辑关系：

```text
ProcessLifecycleOwner
  ├── TransportLifecycleOwner
  │     ├── QuarantineManager
  │     │     ├── RetryScheduler (bounded, no detached workers)
  │     │     └── ResidualEntry[generation] -> CoreControlBlock
  │     └── ActiveSocketFacade -> CoreControlBlock
  ├── PluginUnloadCoordinator
  └── ShutdownReportSink

ROS ComponentContainer / Node
  └── PluginLease + SubscriberReceiveLease
       └── callback admission / active callback accounting
```

- **ProcessLifecycleOwner：** 应用级唯一关闭协调者；决定 shutdown deadline、各子系统顺序、最终进程退出策略。它持有 TransportLifecycleOwner，不能由单个 RobotDriver facade 代替。
- **TransportLifecycleOwner：** 管理 active facades、QuarantineManager、资源登记和 manager shutdown。其生命周期必须长于所有已登记 Core。
- **QuarantineManager：** 保存 residual Core 强 owner、generation、最近一次失败、retry预算、插件/回调依赖标签和诊断快照；不持有 ROS Node 或 plugin 的强引用，避免反向延长插件对象生命周期。
- **RetryScheduler：** 仅负责有界排程和执行入口；同一 generation 同时最多一个 cleanup transaction。推荐由上层已有 executor/专用受控线程驱动，不为每个 entry 创建独立线程，不 detach。
- **PluginUnloadCoordinator：** 管理 plugin lease 关闭与卸载屏障；不得自行销毁仍被 QuarantineManager 引用的 Core。
- **ShutdownReportSink：** 在 ROS logging、plugin code 或普通 executor 停止前，将 shutdown summary 持久化/输出到进程级日志设施。日志失败不能改变资源状态。

manager 不得反向强持有 Node、Subscriber、plugin object 或 plugin callback target。对 plugin 依赖仅记录稳定 plugin identity/generation 与 lease 状态；真正 callback 对象由 plugin lease owner 管理，直到 callback quiescent。

## 3. QuarantineManager 生命周期状态机

Manager 状态建议：

| 状态 | 含义 | 允许操作 |
|---|---|---|
| ACCEPTING | 接受新的 residual owner transfer | register、retry、query |
| QUIESCING | 拒绝新的 transfer，停止新 retry admission | drain in-flight manager operations |
| DRAINING | 对现存 entries 按预算执行最终 retry | retry、snapshot、report |
| SEALED_CLEAN | entries 全部满足稳定终态并释放 | 只读最终报告 |
| SEALED_RESIDUAL | deadline/预算耗尽，仍保留 residual owner | 只读报告；不得再接受新 owner |
| PROCESS_EXITING | 上层已决定终止进程 | 只做允许的最后记录；不启动新异步工作 |

转换规则：
- `ACCEPTING -> QUIESCING` 是原子关闭点；从此 transfer/register 必须失败并保留调用方 handle。
- `QUIESCING -> DRAINING` 前，必须等待已进入的 register/transfer/retry 调用完成或被取消；不能在调用者仍持有半提交状态时销毁 manager。
- `DRAINING -> SEALED_CLEAN` 仅在所有 entries 都满足 quiescent barrier 时允许。
- `DRAINING -> SEALED_RESIDUAL` 在 manager deadline 或 retry budget 用尽时允许；entry 强 owner 必须仍然存在，状态与诊断可查询。
- `SEALED_RESIDUAL` 不是“清理成功”，也不允许通过析构把 owner 静默丢弃。ProcessLifecycleOwner 必须决定继续持有到 process exit、进入明确的 forced-exit 路径，或交给仍存活且有能力管理该资源的更高层 owner。
- 重复 shutdown 返回同一最终/进行中状态；不得重复创建 scheduler 或重新打开 admission。

## 4. 有界重试策略

### 4.1 Entry 级预算

每个 residual entry 至少记录：
- `generation`、first_failure_time、last_attempt_time、attempt_count；
- `next_eligible_time`、last_failure_code/stage、last_snapshot；
- `retry_deadline`、`max_attempts`、`max_elapsed`；
- `plugin_dependency_id`（若存在）与 `callback_quiescent`；
- `state`、`owner_location`、`in_flight`。

建议采用指数退避加上限与小幅 jitter；具体初值须经产品部署拓扑与实时性评审后配置，不在此处硬编码。调度器必须遵守：
- 同一 generation 不重叠；不同 Core 可并行但受 `max_concurrent_cleanup` 限制。
- retry 仅处理可重试的 native transient failure；INVALID_STATE、STALE_GENERATION、OWNER_INVARIANT_BROKEN、PLUGIN_CODE_STILL_REFERENCED 等不可重试错误应停止自动重试并升级报告。
- 每次 retry 有单独 attempt deadline；整个 entry 有 wall-independent monotonic elapsed budget。
- 退避期间不得持有 Core 内部锁；scheduler queue 需有容量上限，队列满时保持 entry 在 RETRY_PENDING，不丢弃 owner。
- 进程关闭阶段不再进行无限 backoff；shutdown 使用独立、较短且明确的最终清理预算。
- 达到 max attempts 或 max elapsed 后进入 RETRY_EXHAUSTED；可由人工/上层显式重新授权新预算，但不能自动重置 attempt counter 造成永续重试。

### 4.2 Manager 级预算

Manager 配置建议字段：
- `max_entries`：最大 quarantine entry 数；
- `max_concurrent_cleanup`：最大并行清理数；
- `shutdown_deadline`：manager 最终关闭时间点；
- `per_attempt_timeout`：单次清理等待上限；
- `max_shutdown_attempts_per_entry`：关闭阶段每个 entry 最大尝试数；
- `scheduler_queue_capacity`：最大排队项数；
- `report_flush_deadline`：最终报告写出预算。

entry 数量达到上限时，拒绝新的 owner transfer，调用方保留 handle 并得到明确 CAPACITY_EXCEEDED；禁止覆盖、淘汰或丢弃最老 entry。并发槽位不足时只延迟，不创建额外线程。

### 4.3 Clock 与 deadline

- 所有间隔、退避和超时判断使用 monotonic clock（候选 `std::chrono::steady_clock`）；不得用系统时间调整敏感的 wall clock 计算 elapsed timeout。
- 绝对时间戳可额外记录用于日志，但不参与调度正确性。
- deadline 到期后可停止等待，不得把正在运行的阻塞系统调用强制“取消成功”；未完成 worker 仍由 owner 持有。
- deadline 参数需在 API 中明确是 time_point 还是 duration，不能让调用方混用不同 clock domain。

## 5. Process shutdown 协议

建议的分阶段协议：

1. **STOP_ADMISSION：** 停止新 command、connect、receive callback、subscriber lease 与新的 owner transfer；向上层返回 SHUTTING_DOWN。
2. **QUIESCE_PLUGINS：** 停止 plugin callback admission；等待 active callback/handler 到零；释放 plugin-owned callback target。若 callback 不能静默，plugin 不得卸载。
3. **STOP_ROS_NODES：** 按明确顺序 deactivate/destroy ROS nodes 与 subscribers；确认 node 不再触发 driver/plugin callback。Node 析构不应负责最后一次无界阻塞 cleanup。
4. **STOP_ACTIVE_TRANSPORTS：** 对正常 facade 执行 stop/cancel/drain/join/close；每个步骤独立记录结果。
5. **TRANSFER_RESIDUALS：** 对仍有 residual 的 facade，将 move-only handle 转交给仍存活的 TransportLifecycleOwner/QuarantineManager；转交失败则源 owner 保持有效并升级 shutdown error。
6. **DRAIN_QUARANTINE：** 在 shutdown 专用预算内按 entry 执行有限 retry；不得等待超过 ProcessLifecycleOwner 的总 deadline。
7. **FLUSH_REPORT：** 记录 clean/residual/exhausted/plugin-blocked entry 数、generation、错误阶段、attempt 次数、最终 snapshot 与采取的退出决策。日志不得记录敏感 payload。
8. **SEAL_MANAGER：** 若全部稳定清理，SEALED_CLEAN；否则 SEALED_RESIDUAL，保留所有仍需管理的 owner 直到 process exit。
9. **EXIT_DECISION：** ProcessLifecycleOwner 根据产品策略选择 CLEAN_EXIT、RESIDUAL_EXIT（带明确告警）或拒绝退出并继续运行；不能将 residual 状态降格为成功。

如果 OS/平台要求在硬性时限内终止进程，强制终止是进程级决策而非资源清理成功。最终报告必须标记 FORCED_PROCESS_EXIT；不宣称应用层线程 join、handler drain 或 native close 已完成。不得在库析构函数中调用 `std::terminate` 作为常规策略，也不得用 `_Exit`/abort 掩盖错误。

## 6. ROS component 与 plugin unload 屏障

### 6.1 Plugin lease

每个 plugin callback registration 应具有可关闭的 PluginLease/CallbackLease：
- admission close 后不再产生新的 plugin callback；
- 已排队 callback 可取消或在 plugin 仍加载时执行完毕；
- active callback 计数必须在 callback trampoline 的 RAII guard 中增减；
- plugin unload gate 等待 pending callback=0、active callback=0、plugin-owned deleter/destructor 不再待执行；
- timeout 时状态为 PLUGIN_UNLOAD_BLOCKED，plugin image 保持加载；不得以 manager 仍持有 Core 为由认为 plugin code 已无引用。

### 6.2 组件销毁顺序

建议顺序：
1. component container 停止向目标 component 分派新 callback；
2. Node lifecycle deactivate/cleanup，停止 timer/subscription/service admission；
3. Subscriber receive lease stop 并等待其 callback quiescence；
4. RobotDriver 分别 stop control 与 diagnostics transport；
5. residual handle 转交给长生命周期 TransportLifecycleOwner；
6. 证明 plugin callback target、custom deleter、vtable dispatch 和线程入口均不再引用插件代码；
7. 才允许 unload plugin shared library；
8. 最后 shutdown container 与 process-level manager。

若 Core 的 worker handler、custom deleter 或虚函数实现来自 plugin image，即使 callback 数为零，也必须证明这些对象析构不再需要执行 plugin 代码。否则必须把这些实现移到常驻 transport library，或推迟 plugin unload。QuarantineManager 不得通过强持有 plugin object 来“解决”卸载问题，因为那会导致卸载永远无法完成。

### 6.3 关键反例

- callback 计数归零但队列仍有待执行 handler：不得 unload。
- handler 已取消但 worker 尚 join：不得 unload。
- worker 已 join但 Core deleter 在 plugin：不得 unload。
- plugin unload 已开始但 residual retry 可能调用 plugin virtual：禁止该 retry，必须先解除代码依赖。
- manager 已 SEALED_RESIDUAL但 plugin code 仍被引用：保持 plugin loaded 或进入明确的 forced process exit，不能强行 dlclose。

## 7. 进程退出时 residual owner 的处置分类

| 分类 | 资源状态 | 允许动作 | 报告状态 |
|---|---|---|---|
| CLEAN | quiescent barrier 全部通过 | 释放 Core owner | CLEAN_EXIT |
| RETRY_PENDING | 仍有 transient failure，预算未尽 | 有界 retry | SHUTDOWN_IN_PROGRESS |
| RETRY_EXHAUSTED | 预算耗尽，仍有 residual | 保留 owner，停止自动 retry | RESIDUAL_RETAINED |
| PLUGIN_UNLOAD_BLOCKED | plugin code 仍可能执行 | 保持 plugin image 加载 | PLUGIN_BLOCKED |
| OWNER_TRANSFER_FAILED | transfer 未原子成功 | 保留源 handle，禁止 facade 失效 | TRANSFER_FAILED |
| FORCED_PROCESS_EXIT | 上层/OS 决定强制结束 | 不再声称应用层清理完成 | FORCED_EXIT |

“保留 owner 到进程退出”只能由进程级生命周期 owner 执行；不能让局部静态析构顺序或 leaked singleton 偶然承担。进程终止后 OS 回收进程资源不等于 native 协议对端已正确关闭，也不构成设备侧安全状态证明。

## 8. 建议接口与事件记录（设计草案）

候选配置与结果形状（非最终 API）：

```cpp
struct RetryPolicy {
  std::chrono::steady_clock::duration initial_backoff;
  std::chrono::steady_clock::duration max_backoff;
  std::chrono::steady_clock::duration per_attempt_timeout;
  std::chrono::steady_clock::duration max_elapsed;
  std::uint32_t max_attempts;
  std::uint32_t max_concurrent_cleanup;
  std::uint32_t max_entries;
};

enum class ManagerShutdownState : std::uint32_t {
  accepting, quiescing, draining, sealed_clean, sealed_residual
};

enum class ProcessExitDisposition : std::uint32_t {
  clean_exit, residual_exit, plugin_unload_blocked, forced_process_exit
};

struct QuarantineEntrySummary {
  std::uint64_t generation;
  std::uint32_t attempt_count;
  std::uint32_t last_error_code;
  std::uint32_t entry_state;
  bool owner_retained;
  bool plugin_dependency_present;
};

struct ManagerShutdownReport {
  ManagerShutdownState state;
  std::uint32_t clean_entries;
  std::uint32_t residual_entries;
  std::uint32_t exhausted_entries;
  std::uint32_t plugin_blocked_entries;
  std::vector<QuarantineEntrySummary> entries;
  bool report_flushed;
};
```

设计要求：
- `RetryPolicy` 创建后不可在运行中被不受控地修改；配置更新必须有版本号并在 entry 边界生效。
- report 需在 scheduler/ROS/plugin logging shutdown 前 flush；失败时仍保留内存中的最小摘要并返回 REPORT_FLUSH_FAILED。
- entry summary 只包含稳定值，不暴露 Core/native handle/exception_ptr。
- 每次 transfer/retry/complete/exhaust/shutdown 状态变化产生带 generation 的事件；日志序列号单调递增，便于跨线程重建时序。
- shutdown API 不应从 manager worker thread 自身调用；应检测并拒绝 self-shutdown。

## 9. 验收矩阵（全部 NOT_RUN）

| ID | 场景 | 必须断言 | 状态 |
|---|---|---|---|
| QM-SHUT-01 | ACCEPTING期间 transfer | 正确登记唯一 generation owner | NOT_RUN |
| QM-SHUT-02 | QUIESCING并发 transfer | 关闭点后拒绝；源handle仍有效 | NOT_RUN |
| QM-SHUT-03 | in-flight transfer与shutdown竞态 | 无半提交entry、无双重owner丢失 | NOT_RUN |
| QM-SHUT-04 | 重复 shutdown | 幂等返回相同终态/进行中状态 | NOT_RUN |
| QM-SHUT-05 | DRAINING全部完成 | quiescent barrier成立后SEALED_CLEAN | NOT_RUN |
| QM-SHUT-06 | deadline到期仍有residual | SEALED_RESIDUAL且owner保留 | NOT_RUN |
| QM-SHUT-07 | max_entries已满 | 拒绝transfer，不覆盖已有entry | NOT_RUN |
| RETRY-BND-01 | 达到max_attempts | 停止自动retry，进入RETRY_EXHAUSTED | NOT_RUN |
| RETRY-BND-02 | 达到max_elapsed | 停止自动retry，owner仍保留 | NOT_RUN |
| RETRY-BND-03 | 指数退避与jitter | 不早于next_eligible_time且有上限 | NOT_RUN |
| RETRY-BND-04 | scheduler队列满 | entry保留、owner不丢失、不增建线程 | NOT_RUN |
| RETRY-BND-05 | 多entry并发 | 不超过max_concurrent_cleanup | NOT_RUN |
| RETRY-BND-06 | 同generation重复触发 | 只运行一个cleanup transaction | NOT_RUN |
| RETRY-BND-07 | wall clock跳变 | monotonic deadline行为不受影响 | NOT_RUN |
| RETRY-BND-08 | 不可重试错误 | 不自动循环，生成升级事件 | NOT_RUN |
| PROC-SHUT-01 | 完整进程关闭 | admission/ROS/transport/quarantine顺序正确 | NOT_RUN |
| PROC-SHUT-02 | report flush失败 | 最小摘要仍可取回，状态不误报CLEAN | NOT_RUN |
| PROC-SHUT-03 | forced exit决策 | 标记FORCED_PROCESS_EXIT，不伪报cleanup成功 | NOT_RUN |
| PROC-SHUT-04 | shutdown deadline | 总等待不超过上层预算，owner不提前释放 | NOT_RUN |
| PLUGIN-01 | active callback非零 | plugin unload被阻止 | NOT_RUN |
| PLUGIN-02 | pending handler非零 | plugin unload被阻止 | NOT_RUN |
| PLUGIN-03 | worker未join | plugin unload被阻止 | NOT_RUN |
| PLUGIN-04 | custom deleter/vtable来自plugin | 代码依赖未解除前不得unload | NOT_RUN |
| PLUGIN-05 | residual retry依赖plugin virtual | 禁止retry/unload竞态 | NOT_RUN |
| PLUGIN-06 | component container teardown | Node、lease、manager、plugin顺序无悬空引用 | NOT_RUN |
| PLUGIN-07 | unload timeout | 保持plugin loaded并报告PLUGIN_UNLOAD_BLOCKED | NOT_RUN |
| THREAD-EXIT-01 | manager worker请求自身shutdown | 明确拒绝，不self-join | NOT_RUN |
| THREAD-EXIT-02 | 最后owner位于worker线程 | 测试证明此路径不可达 | NOT_RUN |
| THREAD-EXIT-03 | scheduler shutdown | 无detach、无后台线程遗留 | NOT_RUN |

## 10. 未决决策与实施门禁

需在实现前确定：
- RetryPolicy 的默认数值、按部署场景覆盖方式及最大 shutdown budget；
- 可重试 native error 白名单及永久错误分类；
- RetryScheduler 是复用 ROS executor、应用 executor 还是专用受控线程；其停止顺序和实时性影响；
- ProcessLifecycleOwner 的实际承载者及与 signal handler/main 的交互；signal handler 不得直接执行复杂清理或锁操作；
- QuarantineManager 在 SEALED_RESIDUAL 后由谁保持到 process exit，以及应用是否允许 RESIDUAL_EXIT；
- plugin callback/deleter/vtable 的代码归属；是否需要将 transport Core 实现移至常驻共享库；
- report sink 的持久化方式、日志丢失时的最小可观测性；
- shutdown 预算耗尽后由产品策略继续运行、拒绝退出还是强制退出。

实施门禁：
1. 先做纯状态机与虚拟 monotonic clock 单元测试；
2. 再做 manager owner transfer/容量/并发/有界 retry fake tests；
3. 再做线程退出、handler drain、native close fault injection 与 TSan/ASan；
4. 再做 ROS component container 与真实 plugin load/unload integration；
5. 最后才允许进入 ROS 2 Control、SIL/HIL、VAL3/CS9、FAT/SAT 和实机验证。
任何阶段失败都不得把后续阶段标记为完成。

## 11. 状态与下一节点

- **已完成：** QuarantineManager shutdown 状态机、有界重试预算、ProcessLifecycleOwner职责、进程退出分类及 ROS/plugin unload 屏障静态设计。
- **未完成：** RetryScheduler、QuarantineManager、PluginLease、shutdown report sink、状态机及任何实现均未落地。
- **验收状态：** QM-SHUT-01至07、RETRY-BND-01至08、PROC-SHUT-01至04、PLUGIN-01至07、THREAD-EXIT-01至03全部NOT_RUN。
- **未执行：** C++17编译、CMake、gtest、虚拟时钟测试、fault injection、TSan/ASan、ROS component/plugin load/unload、ROS 2 Control、VAL3/CS9、SIL/HIL、FAT/SAT或实机测试。
- **上游边界：** 未修改固定上游、未创建/应用/合并PR；`TODO-EXT-001`仍未授权。
- **下一节点：** §9.3.298 / SERVO-881：SocketV2 QuarantineManager / RetryScheduler concurrency model、lock ordering、executor integration 与 deterministic shutdown race test design。
