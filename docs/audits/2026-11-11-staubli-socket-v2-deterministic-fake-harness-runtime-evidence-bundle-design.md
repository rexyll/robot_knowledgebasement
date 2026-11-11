# Stäubli SocketV2 确定性 Fake Harness 接口与 Runtime Evidence Bundle 设计

> SERVO-898 / §9.3.315  
> 状态：DESIGN_SPECIFIED；Fake Harness 未实现，RACE/EXEC 全部 NOT_RUN。  
> 固定上游审查基线：`ICube-Robotics/staubli_driver_ros2@bd658e2d266e315d2ee35f985fb352ea88306b79`。

## 1. 目标与非目标

本设计为未来 C++17 测试实现定义可注入的时间、并发、executor 与故障控制面，并为每次测试运行定义可验证、可复现的 Runtime Evidence Bundle。目标是让竞态测试不依赖 sleep、调度运气或人工观察，并能从证据包重建关键事件顺序、资源状态与环境身份。

本节点只交付接口规格、JSON Schema、示例模板和静态校验规则；不实现生产 SocketV2/Core，不修改 Stäubli 上游，不运行 Fake/C++/ROS 测试，不把 Python CI 标记为运行时验收。测试执行状态仍为 NOT_RUN。A1.1、`TODO-EXT-001`仍按既有授权门禁处理，不能由本设计自动解锁。

## 2. 设计原则

1. **单一状态机**：Fake backend 与生产 Asio backend 将来必须驱动同一 Core 状态转换逻辑；Fake 不复制一套生命周期算法。
2. **测试专用隔离**：Fake、FaultScript、DeterministicExecutor 只能进入 test-only target/support，不安装、不导出、不链接生产 plugin，不改变 legacy ABI。
3. **无时间睡眠同步**：禁止以 `sleep_for`、轮询或 wall-clock timeout 作为竞态顺序控制；超时只用于测试 watchdog，不能替代明确的 barrier release。
4. **显式因果关系**：所有事件具有单调 sequence、逻辑时间、thread identity、resource generation/revision 和 attempt token。
5. **失败不抹除现场**：primary failure 与 cleanup failure 分开记录；residual/unknown 状态保留唯一 owner，不允许快照把未知状态归类为 clean。
6. **证据不可变**：原始日志、环境清单、事件轨迹、状态快照和诊断工件逐项计算 SHA-256；证据包记录源码 commit 与上游固定基线。
7. **fail closed**：缺少关键字段、hash 不匹配、环境身份不完整、断言未评估或执行状态无证据时，不得标记 RUN_PASS。

## 3. 确定性 Fake Harness 接口

### 3.1 FakeClock

建议接口语义（C++17 抽象签名示意，非已实现 API）：

```cpp
class ITestClock {
public:
  virtual ~ITestClock() = default;
  virtual int64_t now_ns() const noexcept = 0;
  virtual void advance_to(int64_t deadline_ns) = 0;
  virtual void advance_by(int64_t delta_ns) = 0;
  virtual uint64_t tick_count() const noexcept = 0;
};
```

- 默认模式为 `fake_monotonic`；禁止时间倒退，负 delta、溢出和小于当前时间的 deadline 必须拒绝。
- 事件调度使用逻辑纳秒，不依赖宿主 wall clock；真实 steady clock 只用于明确标注的 integration profile。
- 每次推进记录 clock_advance 事件；同一 logical time 的事件仍由全局 sequence 排序。
- watchdog 使用真实单调时钟，watchdog 超时只能导致 FAIL/ABORT，不能推进 FakeClock。

### 3.2 Barrier / Latch

```cpp
struct BarrierSpec { std::string id; uint32_t participants; };
class IDeterministicBarrier {
public:
  virtual ~IDeterministicBarrier() = default;
  virtual void arrive_and_wait(const std::string& id,
                              const std::string& participant) = 0;
  virtual void release(const std::string& id) = 0;
  virtual BarrierSnapshot snapshot(const std::string& id) const = 0;
};
```

- barrier 由测试显式创建，participant ID 唯一；未登记 participant、重复到达、重复 release 和参与者数不匹配均产生确定性错误。
- 支持手动 release 与 latch countdown；默认不自动 release。
- 不在持有 Core 内部锁时等待 barrier；barrier callback 不得反向调用 Core 锁域。
- 每个到达/释放写入 trace；快照保留参与者集合、arrived 集合、released 状态。

### 3.3 DeterministicExecutor

接口至少包含 `post(task_id, task)`、`cancel(task_id)`、`run_one()`、`run_until_idle(max_steps)`、`reject_next(n)`、`shutdown(mode)`、`snapshot()`。

- 模式：`deterministic_inline`（显式立即执行）、`deterministic_queued`（默认 FIFO 手动泵送）；生产 executor 只允许作为单独 integration profile。
- 拒绝、取消、完成、重复完成、shutdown 前后提交均需生成事件；任务不得静默丢弃。
- shutdown 语义区分 QUIESCING、STOPPED；已接受任务必须明确完成、取消或保留为未完成项。
- Executor 仅负责调度；资源清理仍由唯一 CleanupCoordinator 执行，不允许 executor 成为第二个资源 owner 或 close 路径。

### 3.4 Fault Injector

- 使用不可变 FaultScript；每条规则具有稳定 fault_id、目标组件/操作、触发条件、触发次数/顺序和结果。
- 覆盖 socket open/bind/async initiation/cancel/close、executor reject/cancel/shutdown、callback throw、worker join、native handle reconciliation、remote session 和 plugin lease 屏障。
- 触发采用显式事件/attempt/generation 匹配；不使用概率故障或随机延迟。若需要随机化探索，seed 必须入环境清单且不得用于确定性 RACE/EXEC 基准。
- 每次注入都记录 configured、matched、fired、outcome；未命中的规则也保留，避免误以为故障已发生。

## 4. Event Trace 规范

每条事件至少包含：`sequence`、`logical_time_ns`、`thread_id`、`component`、`event`、`resource_generation`、`resource_revision`、`attempt_token`。

推荐事件类型：operation_begin/end、admission_close、callback_enter/exit、handler_schedule/start/complete/cancel、barrier_arrive/release、executor_accept/reject/cancel/complete/shutdown、fault_match/fire、owner_prepare/commit、native_close_begin/end/unknown、worker_join_begin/end/fail、remote_session_state、plugin_lease_acquire/release、snapshot_capture、assertion_evaluate。

约束：
- sequence 从 0 单调递增且无重复；logical_time_ns 不倒退。
- 同一 generation 的 revision 只增不减；跨 generation 必须有显式 create/transfer 事件。
- attempt_token 标识一次清理/连接尝试；旧 token 事件不得覆盖新 attempt 状态。
- trace 必须原样保存；展示层排序不得重写原始记录。

## 5. Resource State Snapshot

至少捕获 before、after；失败场景另捕获 failure、reconcile。每项资源包含 resource_id、generation、revision、唯一 owner、lifecycle_state、native_handle_state、active_callbacks、pending_handlers、worker_state、remote_session_state。

- unknown 必须显式表示为 UNKNOWN，不可用 false/zero 推断已清理。
- native handle 的数值句柄只作诊断字段，不作跨进程/跨运行身份；稳定身份由 resource_id + generation 提供。
- worker_state 至少区分 NOT_STARTED、RUNNING、JOINABLE、JOINED、JOIN_FAILED、UNKNOWN。
- remote_session_state 独立于本地 socket state；本地 close 成功不能推断远端 session 已终止。
- residual 状态必须记录唯一强 owner 和后续 reconcile coordinator。

## 6. Environment Manifest 与 Artifact Hash

环境身份必须覆盖仓库 commit、固定上游 commit、OS/架构/kernel、compiler、build type、ROS distro、依赖锁文件 SHA-256 与 OCI image digest。版本缺失时标记 BLOCKED，不得填猜测值。

每个 artifact 记录 role、相对路径、SHA-256、小写十六进制、字节数和 media type。路径必须相对 bundle 根目录，拒绝绝对路径、`..` traversal、符号链接逃逸和重复路径。计算 hash 的对象必须是实际归档字节，不得 hash 格式化后的摘要文本代替原始日志。

推荐 bundle layout：
- `bundle.json`：索引与执行状态
- `environment/environment.json`：环境清单
- `trace/events.jsonl`：原始事件轨迹
- `snapshots/resources.json`：状态快照
- `logs/test.log`：测试日志
- `diagnostics/*`：core dump、sanitizer、build/ROS日志（如有）
- `SHA256SUMS`：所有工件的校验和清单

## 7. RUN_PASS / RUN_FAIL / NOT_RUN / BLOCKED 门禁

- `NOT_RUN`：设计或测试尚未执行；允许空 trace/snapshot/artifacts/assertions。示例文件固定为 NOT_RUN。
- `BLOCKED`：执行前置条件不满足，必须提供 blockers；不得写成 RUN_FAIL。
- `RUN_PASS`：必须有完整 environment identity、test_log、environment_manifest、event_trace、state_snapshot 工件；所有必需断言 PASS；SHA-256 全部可验证；无未解释 residual/UNKNOWN；执行来源与 attempt token 一致。
- `RUN_FAIL`：必须有实际执行日志、环境身份和至少一个 FAIL 断言；保留失败现场和所有可获取诊断工件。运行失败不等于测试框架或环境初始化失败，后者应 BLOCKED。
- 任何证据缺失、hash mismatch、sequence gap、generation/revision 回退、重复 attempt identity 或 artifact path escape 均拒绝 RUN_PASS。

## 8. RACE/EXEC 用例映射

| 用例组 | Harness 控制点 | 必须采集的核心证据 |
| --- | --- | --- |
| RACE-01–04 | barrier 双方交错、fake clock、generation/revision fencing | arrive/release trace、before/after snapshot、owner transfer |
| RACE-05–08 | callback admission/drain、callback throw、worker barrier | callback lease trace、active/pending计数、worker join状态 |
| RACE-09–12 | owner prepare/commit、stale token、partial cleanup | attempt token、revision、journal、residual owner |
| RACE-13–16 | executor reject/cancel/shutdown 与 reconcile | executor计数、fallback事件、cleanup coordinator唯一性 |
| EXEC-01–04 | accept/reject/cancel/shutdown 四条执行路径 | task状态转移、shutdown snapshot、未完成任务清单 |

具体断言以 SERVO-897 Catalog 的每项 expected_assertions 为准；本映射不替换测试用例，不宣称已运行。

## 9. 验收矩阵

| ID | 交付/检查项 | 状态 |
| --- | --- | --- |
| FH-API-01 | FakeClock 接口与单调语义 | SPECIFIED |
| FH-API-02 | Barrier/Latch participant 与 release 语义 | SPECIFIED |
| FH-API-03 | DeterministicExecutor task/shutdown 语义 | SPECIFIED |
| FH-API-04 | FaultScript 稳定触发与事件记录 | SPECIFIED |
| EVID-01 | Event Trace 字段与顺序约束 | SPECIFIED |
| EVID-02 | Resource Snapshot 字段与 UNKNOWN/residual 规则 | SPECIFIED |
| EVID-03 | Environment Manifest 与来源身份 | SPECIFIED |
| EVID-04 | SHA-256 artifact manifest / path safety | SPECIFIED |
| EVID-05 | 20项 RACE/EXEC 用例证据映射 | SPECIFIED |
| EVID-06 | JSON Schema 与 NOT_RUN 示例 | ADDED |
| EVID-07 | Schema/policy validator 与负向测试 | NOT_RUN |
| EVID-08 | C++ Fake 实现与运行证据采集器 | NOT_RUN |

## 10. 约束与下一步

- 未修改 Stäubli 上游，未创建/应用/合并上游 PR。
- 未实现 FakeClock、Barrier、Executor、FaultInjector 或 Runtime Evidence Collector。
- 所有 RACE/EXEC 执行状态继续 NOT_RUN；未执行 C++/ROS/TSan/ASan/plugin/HIL。
- `TODO-EXT-001`未授权，A1.1 保持 BLOCKED；§9.3.281–§9.3.294 历史 TaskPlan 同步缺口继续透明保留。
- 下一节点建议：为 Evidence Bundle Schema 增加专用 fail-closed validator、负向测试和 CI；之后再定义 C++ header/API 与最小可执行 Fake target 计划。
