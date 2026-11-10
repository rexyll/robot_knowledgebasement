# Stäubli SocketV2 Fake Transport Seam、Lifecycle Snapshot 与 Failure-Injection Contract

- **节点：** §9.3.303 / SERVO-886
- **日期：** 2026-11-10
- **固定上游基线：** `ICube-Robotics/staubli_driver_ros2@bd658e2d266e315d2ee35f985fb352ea88306b79`
- **性质：** 测试架构与接口合同静态设计；不代表已实现或已验证。

## 1. 目标与边界

本节点承接 SERVO-885 的 source-to-test coverage gap 和 F01–F16 teardown failure-path matrix，定义最小可验证切片 A 的测试接缝：可替换的 transport backend、只读 lifecycle snapshot、按阶段注入失败的控制接口，以及可确定性调度异步事件的测试执行器。

目标是使连接、接收、停止、join、native close、双通道回滚和资源残留的测试不依赖真实网络故障、不依赖固定端口或 sleep 猜测时序，并且能对失败后的真实状态给出可断言证据。

本节点只定义候选内部接口、语义、隔离规则和验收规格。不得把候选接口写成已存在的上游 API；不得改动 ICube 上游；不得把 fake backend 测试结果等同于真实 OS/Boost.Asio 行为。

## 2. 设计原则与边界

1. **Production seam 最小化：** 只在私有实现层引入依赖注入；默认生产构造路径仍创建真实 Asio backend。
2. **Public API 不暴露测试类型：** FakeTransport、FaultScript、TestExecutor、内部计数器不得进入安装头文件、plugin 导出签名或 ROS 参数。
3. **一个 Core、一个 backend、一个 cleanup coordinator：** facade、subscriber 和测试探针不得各自创建独立资源所有权或独立 close 路径。
4. **snapshot 是观测，不是同步屏障：** 普通 snapshot 不可证明回调已退出；只有通过明确 barrier 建立的 quiescent snapshot 才可用于 CLEAN 判定。
5. **故障注入可定位、可重复：** 每个注入点以 operation/generation/attempt/step 标识；同一脚本在相同调度下产生相同结果。
6. **失败不丢 owner：** 注入 close/join/cancel 失败后，Core 与 native resource token 必须仍由明确 owner 持有。
7. **测试不模拟平台事实：** Fake backend 只验证状态机与合同；fd/socket 复用、Asio close 语义、内核完成事件仍须真实平台测试。
8. **旧接口兼容：** 不给 legacy Socket 增加 virtual，不改变旧 vtable、factory 语义或既有 SocketFactory；V2 seam 独立演进。

## 3. 测试架构候选

建议只在 private/detail 层使用以下依赖关系：

```text
SocketV2 façade
  └── SocketCore
       ├── ITransportBackend
       │    ├── AsioUdpBackend       (production)
       │    └── FakeTransportBackend (test only)
       ├── IExecutionDriver
       │    ├── AsioExecutionDriver  (production)
       │    └── DeterministicDriver  (test only)
       ├── LifecycleState
       ├── CleanupCoordinator
       └── SnapshotCollector
```

- `ITransportBackend` 仅抽象 socket 资源操作，不承载 ROS callback 或业务策略。
- `IExecutionDriver` 负责异步完成事件的排队/推进；生产实现由 Asio 执行，测试实现由测试显式推进。
- `SnapshotCollector` 从 Core 的受控状态计数和 backend 资源状态收集值快照。
- `CleanupCoordinator` 是 cancel/drain/join/close 的唯一串行入口。
- Fake 类型仅编译进测试目标，不安装、不导出、不链接进生产 plugin。

若引入接口虚调用会影响性能或复杂度，可采用私有模板策略或内部函数表；但不得为测试便利修改 legacy public virtual interface。具体实现方式须由后续实现节点依据构建结构决定。

## 4. ITransportBackend 候选合同

建议操作按资源阶段拆分，返回值必须保留阶段、错误域与是否发生副作用：

| 操作 | 语义 | 可注入结果 |
|---|---|---|
| create/open | 建立本地 socket 对象与协议族 | 成功、系统错误、异常、部分创建 |
| set_options | 设置 reuse/buffer/nonblocking 等选项 | 成功、指定选项失败 |
| bind | 绑定本地 endpoint | 成功、地址占用、权限错误、部分失败 |
| local_endpoint | 读取真实绑定端点 | 成功、查询失败 |
| async_receive_start | 登记一次异步接收 | 接受、拒绝、同步抛错 |
| cancel_pending | 请求取消异步操作 | 成功、错误、部分取消、结果未知 |
| close_native | 关闭 native transport | 成功、失败且仍 open、失败但 outcome unknown |
| snapshot_native | 只读 native 状态 | open/closed/unknown、handle identity |

约束：
- 不暴露裸 native handle 给上层调用方；测试探针可读取不透明 identity token，但不能自行 close。
- 每个 backend 操作必须明确“失败是否可能已经产生副作用”。不能只返回 bool。
- `close_native` 不得把注入的“错误”自动解释为“句柄仍然打开”；必须支持 `CLOSE_OUTCOME_UNKNOWN`，并要求后续 reconcile。
- cancel 与 close 分开建模；cancel 成功不代表 handler 已完成，close 成功也不代表 callback 已退出。
- Fake backend 的操作日志记录序号、generation、阶段、输入摘要和结果；不得记录敏感网络数据。

## 5. FailureInjection 合同

### 5.1 注入点命名

采用稳定枚举而非自由字符串作为机器接口，建议最小集合：

- CREATE_BEFORE / CREATE_AFTER_PARTIAL
- OPEN_BEFORE / OPEN_AFTER
- OPTION_AT_INDEX
- BIND_BEFORE / BIND_AFTER
- ENDPOINT_QUERY
- RECEIVE_REGISTER_BEFORE / RECEIVE_REGISTER_AFTER
- RECEIVE_COMPLETE_BEFORE_CALLBACK
- CALLBACK_THROW
- CANCEL_BEFORE / CANCEL_PARTIAL / CANCEL_AFTER
- DRAIN_BEFORE / DRAIN_TIMEOUT
- WORKER_WAKE / WORKER_EXIT / JOIN_BEFORE / JOIN_TIMEOUT / SELF_JOIN
- CLOSE_BEFORE / CLOSE_AFTER_EFFECT / CLOSE_OUTCOME_UNKNOWN
- OWNER_TRANSFER_PREPARE / OWNER_TRANSFER_COMMIT
- SNAPSHOT_READ
- ALLOC_REPORT / ALLOC_JOURNAL

### 5.2 FaultRule 字段

每条规则至少包含：
- `rule_id`：测试内唯一 ID。
- `target_generation`：指定 generation；禁止默认命中新 session。
- `operation_id` 与 `attempt_token`：限定事务和尝试。
- `stage`：稳定枚举注入点。
- `trigger_ordinal`：第几次到达时触发。
- `effect`：返回错误、抛异常、延迟完成、部分副作用或结果未知。
- `repeat_policy`：一次、每次、指定次数。
- `completion_gate`：可选 barrier，用于控制完成事件何时释放。

注入规则必须在 operation 开始前冻结；执行中修改脚本须显式创建新 revision。旧 revision 的延迟事件不得写入新 transaction。

### 5.3 注入结果语义

区分以下结果，禁止合并为单一失败：
- `FAILED_NO_EFFECT`：操作失败且证明没有副作用。
- `FAILED_PARTIAL_EFFECT`：已产生部分副作用，必须记录资源变化。
- `OUTCOME_UNKNOWN`：无法证明副作用是否发生，进入 reconcile，不得盲目重试。
- `COMPLETED_WITH_ERROR`：副作用已完成但报告错误；用于验证错误与资源状态分离。
- `BLOCKED_BY_GATE`：等待测试显式释放，不得靠 wall-clock sleep。

## 6. Lifecycle Snapshot 合同

候选快照为只读纯值 DTO：

```cpp
struct LifecycleSnapshot {
  std::uint64_t core_id;
  std::uint64_t generation;
  std::uint64_t revision;
  SnapshotConsistency consistency;
  TransportState transport_state;
  ReceiveState receive_state;
  bool admission_open;
  std::uint64_t pending_operations;
  std::uint64_t pending_handlers;
  std::uint64_t active_callbacks;
  bool worker_started;
  bool worker_joinable;
  NativeResourceState native_state;
  std::uint64_t backend_operation_sequence;
  std::uint64_t cleanup_transaction_id;
};
```

说明：
- `core_id` 是进程内诊断身份，不是可复用 native fd/socket 值。
- `generation` 标识一次资源世代；`revision` 标识该世代状态版本。
- `transport_state`、`receive_state`、`native_state` 必须独立，不能用单一 connected bool 代替。
- `pending_operations`、`pending_handlers`、`active_callbacks` 的增减必须通过 RAII/受控计数完成，所有异常路径都要归还计数。
- `worker_joinable` 只表示 thread object 状态，不证明线程已安全退出；必须与 worker exit 状态和 join 结果共同解释。
- `NativeResourceState` 至少包含 OPEN、CLOSED、UNKNOWN；UNKNOWN 不得折算成 CLOSED。
- 快照读取失败必须返回 snapshot error，不得构造全零快照伪装 CLEAN。

### 6.1 一致性等级

- `OBSERVATIONAL`：在锁或原子计数保护下读取的瞬时状态；可能跨字段不一致，不能用于释放 owner。
- `QUIESCENT_BARRIER`：已关闭 admission，并确认 callback/handler drain barrier、worker exit/join barrier、native close/reconcile barrier 均通过；携带对应 barrier epoch。
- 只有 QUIESCENT_BARRIER 且所有终态条件满足，才能报告 cleanup complete。
- 测试探针不得通过直接改写计数制造 quiescence；只能通过真实执行路径推进状态。

## 7. Deterministic execution 与竞态控制

测试执行器提供：
- `post(task)`：登记待执行任务并返回稳定 task id。
- `run_one(task_id)` / `run_next()`：显式推进一个任务。
- `cancel(task_id)`：返回取消是否成功及是否已开始执行。
- `pending_tasks()`：只读队列快照。
- `barrier(name)` / `release(name)`：控制 handler、callback、worker exit 和 cleanup completion 的顺序。
- `advance_monotonic(duration)`：推进 fake steady clock；不得改变系统 wall clock。

测试必须覆盖：
1. stop 与 callback 即将进入并发；
2. callback 已 active 时触发 stop；
3. cancel 已返回但 handler 尚未完成；
4. join 前 worker 尚未退出；
5. close 已生效但返回错误；
6. close outcome unknown 后 native identity 发生复用风险；
7. manager shutdown 与 owner transfer prepare/commit 竞争；
8. 旧 generation completion 晚于新 generation connect；
9. executor 拒绝/取消与 manager shutdown 同时发生；
10. callback 抛异常后 active count 必须恢复。

禁止通过任意 sleep 作为唯一同步条件。若需测量真实超时，单独进入平台集成测试并记录时钟与环境。

## 8. Fake backend 行为模型

FakeTransportBackend 必须实现可检查的状态机，而不是只返回预设 bool：

- 创建资源分配单调递增的 fake identity。
- open/bind/receive/cancel/close 均追加 operation journal。
- cancel 可以只发出请求，handler completion 由 deterministic driver 单独推进。
- close 支持成功关闭、失败仍 open、完成但报错、outcome unknown 四类结果。
- 模拟 handle identity reuse 时必须增加 identity generation，禁止仅用整数比较。
- 注入异常时保持与生产代码相同的调用栈边界；不能在 fake 中吞异常而生产代码会传播。
- Fake 的 snapshot 可用于状态机断言，但不能声称模拟内核 UDP、Boost.Asio 或真实 OS 的全部行为。

## 9. 最小验证切片与测试映射

| 切片 | 目标 | 最小测试 | 进入下一切片的准入 |
|---|---|---|---|
| A1 | private backend seam | production 默认构造与 fake 注入；旧 API/vtable 不变 | C++17编译、链接、header/install检查 |
| A2 | lifecycle snapshot | generation/revision/state/count一致性；snapshot error | 状态不变量与并发读取测试通过 |
| A3 | failure script | 每个阶段可命中且只命中指定事务 | ordinal/revision/generation fencing测试通过 |
| A4 | deterministic driver | barrier推进、取消、fake clock | 无sleep竞态测试可重复 |
| B | callback admission/drain | late callback、callback throw、drain timeout | active callback归零证据可靠 |
| C | worker stop/join | wake/exit/join/self-join注入 | 不detach、不self-join、owner保留 |
| D | close transaction/reconcile | close fail/partial/unknown、双通道独立清理 | native state与connected状态分离 |
| E | ROS/plugin integration | lifecycle与plugin unload gate | callback target/plugin lease屏障验证 |
| F | native/platform validation | 真UDP、native错误、fd/socket复用 | 平台实测证据与sanitizer |

### 9.1 SERVO-885 F01–F16 映射

- F01 create/open失败：A1/A3。
- F02 option/bind部分失败：A3。
- F03 connect回滚close失败：A3/D。
- F04 cancel未完成：A4/B。
- F05 late handler/callback：A4/B。
- F06 callback异常：B。
- F07 drain timeout：A4/B。
- F08 worker wake/exit失败：A4/C。
- F09 join timeout/self-join：C。
- F10 close失败/结果未知：D/F。
- F11 connected标志与native状态不一致：A2/D。
- F12 control/diagnostics部分清理：D。
- F13 owner transfer失败：A3/D。
- F14 stale generation completion：A3/A4。
- F15 ROS lifecycle/plugin unload竞态：E。
- F16 native handle reuse/double close/leak：F。

## 10. 安全性与不变量

任一实现必须保持：
- I1：每个 Core generation 只有一个 cleanup transaction owner。
- I2：snapshot 不拥有资源，不得延长/缩短 Core 生命周期。
- I3：FAILED_RESIDUAL / OUTCOME_UNKNOWN 时资源 owner 不得释放。
- I4：callback active count 只能由 callback entry/exit RAII 更新。
- I5：worker 未 join 不得报告 worker cleanup complete。
- I6：native state UNKNOWN 不得报告 native close success。
- I7：旧 generation/attempt/revision 的完成事件不得修改当前状态。
- I8：Fake backend 不进入生产安装或 plugin 导出依赖。
- I9：注入错误不能改变错误发生阶段之外的状态，除非 FaultRule 明确声明 partial effect。
- I10：日志/报告分配失败不得覆盖 primary failure 或丢失 Core owner。

## 11. 未决设计决策

以下仍需后续实施前冻结：
- 私有 seam 采用纯虚接口、模板策略还是函数表；选择须以不改变 legacy ABI、可测试和最小生产开销为准。
- snapshot 由锁保护的聚合值还是分字段原子计数构成；必须定义一致性等级与 barrier epoch。
- Fake clock/task driver 是否与生产 executor 共用抽象；不得让测试接口渗入 public API。
- native handle identity 的平台无关表示方式；不得把 fd/socket 整数当作永不复用的全局 ID。
- report/journal 内存分配失败时的固定容量 fallback。
- Windows/macOS/Linux 平台测试 runner 与真实 close 故障注入能力。

## 12. 验收矩阵（本节点全部 NOT_RUN）

| ID | 验收项 | 必须断言 | 状态 |
|---|---|---|---|
| SEAM-01 | legacy ABI/API comparison | legacy Socket vtable与factory签名不变 | NOT_RUN |
| SEAM-02 | private production injection | 默认构造仍使用Asio backend | NOT_RUN |
| SEAM-03 | fake backend isolation | fake/test symbols不进入install/export/plugin | NOT_RUN |
| SEAM-04 | C++17 build | private seam与fake test可在目标标准编译 | NOT_RUN |
| SNAP-01 | snapshot DTO | generation/revision/consistency字段齐全 | NOT_RUN |
| SNAP-02 | observational vs quiescent | observational snapshot不能触发CLEAN | NOT_RUN |
| SNAP-03 | counter RAII | callback异常/取消路径计数归零 | NOT_RUN |
| SNAP-04 | snapshot read failure | 失败不伪造全零CLEAN快照 | NOT_RUN |
| FAULT-01 | stage targeting | generation/operation/attempt/ordinal精准命中 | NOT_RUN |
| FAULT-02 | partial effect | 资源副作用与错误结果分离记录 | NOT_RUN |
| FAULT-03 | unknown outcome | close unknown进入reconcile且保留owner | NOT_RUN |
| FAULT-04 | revision fencing | 旧脚本/旧完成事件不能覆盖新revision | NOT_RUN |
| EXEC-01 | deterministic barrier | 竞态可显式暂停/释放，无sleep依赖 | NOT_RUN |
| EXEC-02 | fake monotonic clock | deadline/退避推进不依赖wall clock | NOT_RUN |
| EXEC-03 | cancel semantics | 区分queued、running、completed任务 | NOT_RUN |
| EXEC-04 | repeatability | 固定脚本重复运行产生相同状态与journal | NOT_RUN |
| MAP-01 | F01–F16 traceability | 每类失败均映射切片和测试 | SPECIFIED |
| MAP-02 | production/platform boundary | fake测试不冒充native验证 | SPECIFIED |

## 13. 状态与下一节点

- **已完成：** Fake transport seam、snapshot、failure injection、deterministic execution 的静态合同与切片顺序设计。
- **未完成：** 所有候选接口和fake实现尚未落地；全部SEAM/SNAP/FAULT/EXEC验收项NOT_RUN。
- **未执行：** C++17编译、CMake/gtest、install-space consumer、ABI符号比较、fake backend测试、barrier竞态、fake clock、故障注入、TSan/ASan/UBSan、真实UDP/native错误、ROS lifecycle/plugin、VAL3/CS9、SIL/HIL、FAT/SAT与实机测试。
- **上游边界：** 未修改固定上游；未创建、应用或合并PR；`TODO-EXT-001`仍未授权。
- **下一节点：** §9.3.304 / SERVO-887：Private transport seam implementation strategy selection、legacy ABI guard 与 test-only dependency wiring review（继续设计审查，不擅自修改上游）。
