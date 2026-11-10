# Stäubli SocketV2 CleanupReport / ResidualResourceHandle API surface 与 quarantine ownership 实施边界设计

- **节点：** §9.3.296 / SERVO-879
- **日期：** 2026-11-10
- **固定上游基线：** `ICube-Robotics/staubli_driver_ros2@bd658e2d266e315d2ee35f985fb352ea88306b79`
- **性质：** C++17 API / ownership 静态设计稿；不是实现，不构成编译或运行时验证证据。

## 1. 目标与边界

将 SERVO-878 的 primary failure、cleanup failure、native error、exception 与 residual state 分离语义，落实为可评审的 public/private 类型边界、句柄所有权合同、quarantine 生命周期及 retry 状态机。设计目标是：调用方能得到稳定、可复制的诊断值；残留资源不会因 facade/临时结果析构而丢失最后一个 owner；同一 Core 的清理不会并发竞争；插件卸载与 ROS lifecycle shutdown 有明确的上层持有者。

本节点只冻结候选 API 合同和实施门禁。未新增任何头文件、类、Core、manager 或测试；未修改固定上游、未创建/应用 PR；所有验收项均 NOT_RUN。

## 2. Public / private 类型边界

### 2.1 Public headers 候选

- `socket_v2_types.hpp`：固定宽度枚举、错误值 DTO、snapshot DTO、cleanup report DTO、opaque handle 前置声明。
- `residual_resource_handle.hpp`：只暴露 move-only handle、有效性查询和显式 owner transfer 所需操作；不暴露 Core。
- `socket_v2.hpp`：SocketV2 façade 与显式 stop/disconnect 结果。
- `socket_factory_v2.hpp`：C++17 factory result；不使用 C++23 `std::expected`。
- `visibility_control.hpp`：导出宏（若目标包需要共享库符号可见性）。

Public header 不得 include 或暴露 Boost.Asio、`std::thread`、mutex/condition_variable、平台 socket handle、Boost error_category、Core/Impl 定义、线程函数或内部队列类型。PIMPL 析构在 impl 完整的 .cpp 定义。public 枚举固定 `std::uint32_t` underlying type 且显式赋值；新增枚举值须遵循版本/兼容策略。

### 2.2 Private / detail 类型

仅实现侧持有：`SocketCore`、`CoreControlBlock`、`CleanupCoordinator`、`QuarantineManager` 实现、Asio executor/io_context/socket、worker thread、handler/callback bookkeeping、平台 native handle、native error category 映射、异常对象与详细诊断缓冲区。Private 类型不得进入安装头文件或导出符号签名。

### 2.3 ABI 说明

以下草案只承诺同一编译器、标准库、编译选项和包版本下的 source-level C++ API；STL DTO 不等于跨编译器稳定 ABI。若未来承诺长期 binary ABI，应另行采用 opaque C handle / C ABI 或经版本化的 ABI 策略，不能从本草案推断。

## 3. 候选 C++17 public API 草案（伪头文件，未实现）

以下为接口形状示意，省略 include、export macro、错误映射和具体构造函数定义；不得视为可直接合并代码。

```cpp
namespace staubli::transport {

enum class SocketErrorCode : std::uint32_t {
  none = 0, invalid_argument = 1, invalid_state = 2,
  unsupported_protocol = 3, operation_in_progress = 4,
  stop_timeout = 5, stale_handle = 6, owner_transfer_failed = 7,
  postcondition_failed = 8, internal_error = 0xFFFF
};

enum class ErrorStage : std::uint32_t {
  none = 0, create = 1, open = 2, resolve = 3, bind = 4,
  connect = 5, cancel = 6, drain = 7, join = 8, close = 9,
  callback = 10, owner_transfer = 11, retry = 12
};

enum class CleanupStep : std::uint32_t {
  close_admission = 1, cancel_pending = 2, drain_handlers = 3,
  drain_callbacks = 4, join_worker = 5, close_native = 6,
  verify_postconditions = 7
};

struct NativeErrorValue {
  std::uint32_t domain_id{0};  // stable project-owned domain id
  std::int64_t value{0};
  bool present{false};
};

struct FailureRecord {
  SocketErrorCode code{SocketErrorCode::none};
  ErrorStage stage{ErrorStage::none};
  NativeErrorValue native_error{};
  // Public diagnostic is best-effort display text; not a machine contract.
  std::string diagnostic;
};

struct CleanupStepResult {
  CleanupStep step{};
  bool attempted{false};
  bool succeeded{false};
  FailureRecord failure{};
  // Snapshot is observational unless explicitly marked quiescent.
};

enum class SnapshotConsistency : std::uint32_t {
  observational = 0, quiescent_barrier = 1
};

struct SocketSnapshot {
  std::uint64_t generation{0};
  SnapshotConsistency consistency{SnapshotConsistency::observational};
  bool admission_open{false};
  std::uint64_t pending_handlers{0};
  std::uint64_t active_callbacks{0};
  bool worker_joinable{false};
  bool native_open{false};
};

class ResidualResourceHandle; // opaque, move-only

struct CleanupReport {
  std::uint64_t operation_id{0};
  std::uint64_t generation{0};
  FailureRecord primary_failure{};
  bool has_primary_failure{false};
  std::vector<CleanupStepResult> steps;
  bool cleanup_complete{false};
  bool residual_resources{false};
  SocketSnapshot final_snapshot{};
  // Residual owner is returned/transferred separately, not copied in DTO.
};

class ResidualResourceHandle {
public:
  ResidualResourceHandle() noexcept;
  ResidualResourceHandle(ResidualResourceHandle&&) noexcept;
  ResidualResourceHandle& operator=(ResidualResourceHandle&&) noexcept;
  ResidualResourceHandle(const ResidualResourceHandle&) = delete;
  ResidualResourceHandle& operator=(const ResidualResourceHandle&) = delete;
  ~ResidualResourceHandle() noexcept;

  bool valid() const noexcept;
  std::uint64_t generation() const noexcept;
  // Explicitly transfer to a lifecycle owner; failure leaves source valid.
  OwnerTransferResult transfer_to(QuarantineOwner& owner);
private:
  class State;
  std::unique_ptr<State> state_;
};

struct CleanupOutcome {
  CleanupReport report;
  ResidualResourceHandle residual; // valid iff residual remains
};

CleanupOutcome retry_cleanup(ResidualResourceHandle& handle,
                             const CleanupDeadline& deadline);

} // namespace staubli::transport
```

注意：`OwnerTransferResult`、`QuarantineOwner`、`CleanupDeadline` 在此为概念类型，仍需在后续节点冻结。为避免 public DTO 复制隐式持有 Core，`CleanupReport` 不内嵌可复制的 owner handle；owner 通过 move-only `CleanupOutcome` / out-parameter 显式传递。真正 API 需进一步解决 `CleanupOutcome` 的移动语义、分配失败和返回路径。

## 4. 复制、移动与生命周期合同

| 类型 | 复制 | 移动 | 生命周期要求 |
|---|---|---|---|
| `NativeErrorValue` | 允许 | 允许 | 只含项目定义的稳定整数域和值 |
| `FailureRecord` | 允许（诊断文本可分配） | 允许 | 不携带 native handle、error_category 引用或 exception_ptr |
| `SocketSnapshot` | 允许 | 允许 | 值快照；必须携带 consistency 与 generation |
| `CleanupReport` | 允许但可能分配；是否保留复制需评估 | 允许 | 纯诊断值，不持有 Core |
| `ResidualResourceHandle` | **禁止** | **允许** | move-only；唯一可转移的外部强 owner token |
| `QuarantineOwner` | 禁止 | 禁止或受控 PIMPL move | 生命周期由明确的 transport/lifecycle owner 管理 |

句柄规则：
1. 默认构造为空；空句柄的 retry 是幂等 CLEAN/EMPTY，不触碰资源。
2. move 构造/赋值后源句柄为空；不得通过复制制造多个“独立 owner”。
3. handle 有效不代表资源仍有 residual；retry 成功后转为 empty/completed，重复调用安全。
4. generation 必须与 Core generation 匹配；陈旧 handle 返回 STALE_HANDLE，绝不查找或操作新 session。
5. owner transfer 仅在目标 manager 接受并确认登记后才使源 handle 失效；失败必须保持源 handle 有效。
6. handle 析构不得阻塞执行 join/close；若仍有效，必须依赖预先建立的上层 owner 保证资源继续被管理。若无法保证，API 应要求显式 transfer/resolve 并在调试/诊断中暴露未处置 handle，不能靠析构“自动清理”掩盖错误。

## 5. Core owner 图与 QuarantineManager 职责

建议所有权图（实线表示强所有权；worker callback 只使用弱引用或受控执行租约，不能形成自环）：

```text
TransportLifecycleOwner
  ├── QuarantineManager
  │     └── ResidualEntry[generation] ──strong──> CoreControlBlock
  └── ActiveSocketFacade ──strong──> CoreControlBlock
                                      ├── SocketCore / native resources
                                      ├── CleanupCoordinator
                                      └── Worker lifetime state
Worker / handler ──weak or bounded lease──> CoreControlBlock
```

- 一个 Core 只有一个逻辑清理协调者；facade 与 manager 可共享 control block，但不得各自独立 close/join。
- QuarantineManager 由显式 `TransportLifecycleOwner` 持有，不使用无生命周期约束的静态 global registry。
- manager 负责登记、按 generation 查重、容量上限、诊断快照、串行调度（如未来启用）、shutdown deadline 与未清理资源报告；不负责替调用方决定业务重连。
- manager 不可在 worker 自身线程中析构最后一个 Core owner；shutdown 必须从外部管理线程发起，先停止新任务，再排空/重试，再 join manager worker（若存在）。
- manager 容量耗尽时 owner transfer 必须失败且保留源 handle；不得丢弃 Core 或覆盖旧 entry。
- 不允许 worker capture shared_ptr<Core> 构成永久 self-cycle；不允许 detach；不允许最后一个 owner 在 worker 线程执行析构并 self-join。

## 6. retry_cleanup 状态机与并发规则

候选状态：

| 状态 | 含义 | 允许动作 |
|---|---|---|
| EMPTY | 无句柄/无残留 | 幂等返回 |
| RETRYABLE_RESIDUAL | handle 持有 Core，仍有资源残留 | 发起一次 retry |
| IN_PROGRESS | 同一 generation 正在清理 | 第二调用返回 ALREADY_IN_PROGRESS 或等待明确定义的共享 future |
| COMPLETE | 已通过稳定终态检查 | 清空 owner，重复 retry 返回 CLEAN |
| OWNER_TRANSFERRED | manager 已原子接管 | 原 handle 失效；由 manager 调度/显式 retry |
| STALE | generation 与控制块不匹配 | 返回 STALE_HANDLE，不触碰 Core |
| ABANDONED_ERROR | owner 丢失/控制块不一致 | 不可自动恢复；上报最高级生命周期错误 |

转移规则：
- `RETRYABLE_RESIDUAL -> IN_PROGRESS -> COMPLETE`：只有 admission closed、pending handler=0、active callback=0、worker not joinable、native handle closed，且 snapshot 为 QUIESCENT_BARRIER，才可 COMPLETE。
- `IN_PROGRESS -> RETRYABLE_RESIDUAL`：deadline 到期或任一清理步骤失败；保留同一 Core owner 与 generation。
- `RETRYABLE_RESIDUAL -> OWNER_TRANSFERRED`：manager 原子接管成功后才允许。
- 任意状态检测到 generation 不匹配时进入 STALE；禁止按 id 重新定位其他 generation。
- 同一 Core 的 cancel/drain/join/close 通过单一 coordinator 串行化；重复 stop/retry 不重复销毁资源。
- deadline 只限制等待，不意味着可以跳过 join 或释放 owner；clock 类型与超时语义尚未冻结。禁止用 wall clock 作为单调超时依据，候选使用 steady clock。
- 清理步骤必须基于最新状态采样；对 cancel/close 明确定义幂等 adapter；不能把上次 timeout 直接当作本次失败。

## 7. RobotDriver、ROS lifecycle 与 plugin unload

1. RobotDriver 的 connect/disconnect 只消费 CleanupReport；primary failure 独立保留，control/diagnostics 两个通道分别清理。
2. Subscriber 仅持有 receive lease；其 stop 只释放自己的 lease，不得关闭共享 Socket 的全局接收循环。
3. Node 的 on_shutdown / on_deactivate 等 transition 应先关闭新 command/callback admission，再 stop subscribers、排空 callback，再停止 driver sockets，最后把无法清理的 handle 转交给 node 所属的 TransportLifecycleOwner。
4. plugin unload 前必须完成 plugin-owned callback target 与 ROS interface 的 quiescence；任何 plugin code callback 仍可能执行时，不得卸载包含其代码的 shared library。
5. 若 residual Core 的析构/回调仍依赖 plugin 内代码，则不能简单将 owner 转交给进程级 manager 后卸载 plugin；需要将 Core 与 callback target 解耦，或由 plugin unload gate 等待清理完成。这个顺序须通过真实 plugin lifecycle 测试确认。
6. manager 的所有者应明确长于其登记的 facade/Node；若使用 component container，需定义 container shutdown、node destruction、plugin unload 的严格顺序。
7. 本草案不规定 ROS lifecycle transition 必须自动重试；是否后台重试需显式配置与有界调度策略，不能隐式创建线程。

## 8. 异常与内存分配失败边界

- public DTO 不暴露 `std::exception_ptr`，也不暴露 Boost `error_code/category`；进程内 private diagnostic sink 可按需保存 exception_ptr，但其生命周期与ABI不进入 public contract。
- NativeError public value 只使用项目自有 domain id + 整数 code；domain registry 必须版本化。
- `std::string`、`std::vector` 在 bad_alloc 时无法保证完整报告。实施前需选定：固定容量 ring buffer、预分配 report arena，或双通道“最小固定错误码 + best-effort 扩展诊断”。无论选哪种，primary failure 不可因诊断分配失败被覆盖。
- destructor 和 handle move/destructor 必须 noexcept；析构不得做阻塞式 cleanup。
- `retry_cleanup` 不默认 noexcept；如诊断扩展分配失败，仍必须保留 owner，返回最小错误状态或传播原始异常，不能释放 Core。
- callback trampoline 必须 catch(...)，RAII 恢复 active callback 计数；异常记录失败不能使异常穿过线程入口。
- 公开的 CleanupReport 若要复制，需明确复制可能抛异常；可考虑将 report 改为 move-only value 或将大字段拆为固定容量摘要。

## 9. 新增验收矩阵（全部 NOT_RUN）

| ID | 验收场景 | 必须断言 | 状态 |
|---|---|---|---|
| API-OWN-01 | 编译 public headers standalone | 无 Asio/thread/native/private Core include 泄漏 | NOT_RUN |
| API-OWN-02 | public API C++17 consumer | 无 std::expected；枚举底层类型/值固定 | NOT_RUN |
| API-OWN-03 | ResidualResourceHandle copy attempt | 编译期不可复制、可移动 | NOT_RUN |
| API-OWN-04 | move handle | 源句柄失效，目标句柄唯一有效 | NOT_RUN |
| API-OWN-05 | transfer manager 成功/失败 | 成功后源失效；失败时源仍有效 | NOT_RUN |
| API-OWN-06 | handle 空/重复 retry | 幂等返回，不触碰 Core | NOT_RUN |
| API-OWN-07 | stale generation | 不访问新 session，不释放新 owner | NOT_RUN |
| API-OWN-08 | handle 析构仍有 residual | 无阻塞析构；owner 已在更高层登记，否则报告 contract violation | NOT_RUN |
| API-OWN-09 | manager 容量达到上限 | transfer 拒绝且源 handle 保持有效 | NOT_RUN |
| API-OWN-10 | worker 持有弱引用退出 | 不形成 Core self-cycle，最后 owner 不在 worker 线程析构 | NOT_RUN |
| RETRY-01 | 两线程同 generation retry | 单一清理事务；另一个按合同等待/返回 IN_PROGRESS | NOT_RUN |
| RETRY-02 | retry 中途 deadline 到期 | 保留 handle/Core；状态回到 RETRYABLE_RESIDUAL | NOT_RUN |
| RETRY-03 | cancel/drain/join/close 部分失败 | primary 保留，失败步骤保序追加，其他安全步骤继续 | NOT_RUN |
| RETRY-04 | callback 退出后重试 | 重新采样后完成剩余步骤，不重复释放 | NOT_RUN |
| RETRY-05 | observational snapshot | 不允许进入 COMPLETE | NOT_RUN |
| RETRY-06 | complete 后重复 retry | 幂等 CLEAN，无 double join/close | NOT_RUN |
| ROS-01 | lifecycle deactivate/shutdown | admission、subscriber、driver、manager 顺序符合契约 | NOT_RUN |
| ROS-02 | node destroy 且存在 residual | owner 转交到更长生命周期 manager | NOT_RUN |
| ROS-03 | plugin unload gate | callback target/插件代码不再被 worker 引用后才卸载 | NOT_RUN |
| ROS-04 | manager shutdown deadline | 未清理 residual 可诊断且 owner 不丢失 | NOT_RUN |
| ROS-05 | component container teardown | node/manager/plugin 顺序无悬空 callback 或 self-join | NOT_RUN |
| ERR-ALLOC-01 | report string/vector 分配失败 | 最小错误码与 Core owner 保留，primary 不覆盖 | NOT_RUN |
| ERR-ALLOC-02 | exception_ptr/private sink 记录失败 | 不让异常逃逸 worker，不误报 cleanup complete | NOT_RUN |

## 10. 未决决策与实施门禁

以下项目必须在实现前明确，不在本节点擅自冻结：
- public API 是否提供任何 exception handle；本草案建议不暴露 exception_ptr，只在 private diagnostic sink 保留。
- `std::string`/`vector` 分配失败时采用固定容量日志、预分配 arena 还是最小错误码 fallback。
- QuarantineManager 的唯一生命周期所有者：RobotDriver、ROS node、component container 还是独立 transport lifecycle owner；本草案推荐显式 TransportLifecycleOwner，但需结合部署拓扑评审。
- plugin unload 时 Core/worker 是否还可能调用 plugin 内 callback；需要确定 callback target 解耦与卸载门禁。
- deadline 的类型、clock 和语义；建议 steady_clock，但尚未形成目标代码合同。
- CleanupReport 的复制语义：保留可复制 DTO 还是改为 move-only。
- handle 析构遇到未转交 residual 时的可诊断强制策略。
- manager 是否允许后台重试，以及容量、退避、最大运行时间和进程退出策略。

实施门禁顺序：先冻结 public/private include closure 与 DTO；再实现 move-only handle/control block；再实现 manager owner transfer；再实现单 Core cleanup coordinator 与 retry state machine；最后接入 Subscriber lease、RobotDriver 与 ROS lifecycle/plugin unload。每一层先做 C++17 compile + deterministic fake tests，再做 UDP loopback/native error injection、TSan/ASan，之后才可进入 ROS 2 Control/SIL/HIL。未通过前不得进入 VAL3/CS9、FAT/SAT 或实机验收。

## 11. 状态与下一节点

- **已完成：** 本节点的静态 API/ownership 边界设计稿与验收矩阵。
- **未完成：** 所有 public/private 类型、handle、manager、retry、ROS lifecycle/plugin unload 均未实现。
- **验收状态：** API-OWN-01至10、RETRY-01至06、ROS-01至05、ERR-ALLOC-01至02全部 NOT_RUN。
- **未执行：** C++17编译、CMake、gtest、install-space consumer、loopback、native error injection、TSan/ASan、ROS 2 Control、plugin unload、VAL3/CS9、SIL/HIL、FAT/SAT、实机测试。
- **上游边界：** 未修改固定上游、未创建/应用/合并PR；`TODO-EXT-001`仍未授权。
- **下一节点：** §9.3.297 / SERVO-880：SocketV2 QuarantineManager shutdown contract、bounded retry scheduling 与 process/plugin teardown 资源释放策略设计。
