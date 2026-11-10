# Stäubli SocketV2 Result 错误分类、异常安全与资源残留 / Quarantine Owner 生命周期契约审查

- 审查节点：§9.3.295 / SERVO-878
- 日期：2026-11-10
- 固定上游基线：ICube-Robotics/staubli_driver_ros2@bd658e2d266e315d2ee35f985fb352ea88306b79
- 前序：SERVO-874 Socket/Subscriber init-cleanup contract；SERVO-875 UDP observability slices；SERVO-876 ABI/Core ownership；SERVO-877 C++17 public type/FactoryResult
- 性质：静态设计审查与失败语义契约；不是已实现代码，也不代表运行时故障注入已执行

## 1. 目标与结论

本节点定义 SocketV2 在 create/connect/start_receive/stop/disconnect/close 失败或抛异常时的统一错误语义，重点保证：原始失败原因不被清理失败覆盖；每个清理步骤尽最大努力继续；资源未真正静止/关闭时不释放最后一个 owner；清理可安全重试；析构不承担可观察的成功清理责任。

核心决策：
1. 将 primary operation failure、cleanup failure、native transport error、C++ exception 与 residual-resource state 分开记录，不能压成单个 bool 或单一错误码。
2. 对一次事务保留不可变的 primary failure；清理失败按步骤追加，永不覆盖 primary failure。若操作本身成功但清理/后置条件失败，则该操作结果失败，primary 记录对应的 postcondition/cleanup failure。
3. 每一步 cleanup 独立执行并捕获异常；一个 cancel/stop/close 失败不得短路剩余安全清理步骤。
4. FAILED_RESIDUAL 必须携带可继续持有 Core 的 opaque cleanup owner/handle；不能只返回 snapshot 后让 façade/Core 析构。
5. retry_cleanup() 只能针对仍由该 handle 持有的同一 Core/generation，幂等、可重入但必须串行化；仅在终态快照证明 handler/callback/worker/native handle 全部归零/关闭后才释放 owner。
6. 析构函数 noexcept 且 best-effort；析构不能报告清理成功，也不能替代显式 stop/disconnect。若残留 owner 存在，必须转交到明确的上层生命周期管理器/quarantine owner，禁止静默丢弃。
7. noexcept 不能为方便而覆盖可能分配内存、构造字符串、调用用户回调或锁/系统调用的路径；公共操作默认不承诺 noexcept，析构/无分配查询等有限边界单独定义。
8. 本轮仅建立设计契约与测试规格；未实现 API、Core、quarantine registry、异常映射或任何上游补丁。

## 2. 证据边界与依赖约束

本节点沿用 SERVO-874/875/876/877 已记录的固定上游事实：legacy Socket 为 bool API；UDP façade 使用 PIMPL；Asio/socket/thread/handler 位于实现侧；Subscriber 在构造阶段启动接收线程并捕获裸 this；RobotDriver connect/disconnect 存在 rollback 与 cleanup 结果被忽略的风险；v2 方向为独立 public API、private Core 和 structured Result。

本轮未重新读取固定上游 commit 的实现文件，也未运行编译或故障注入。以上为前序审计结论的承接，不声称本轮逐行复核。所有具体 Boost.Asio close/cancel 行为、平台错误码和异常发生点必须由后续目标平台测试确认。

## 3. 错误分类：不可互相覆盖的四个维度

### 3.1 Operation / primary failure

建议的错误域（枚举数值需在 public API 冻结前评审；下表是语义名，不是已发布 ABI）：

| 类别 | 语义 | 示例 |
|---|---|---|
| NONE | 操作及后置条件均满足 | connect 后状态达到 CONNECTED/CONFIGURED |
| INVALID_ARGUMENT | 参数/枚举/endpoint 不合法 | 未知 ProtocolType、端口越界 |
| UNSUPPORTED_PROTOCOL | 协议当前未实现 | TCP factory 请求 |
| INVALID_STATE | 状态不允许该操作 | 在错误生命周期阶段启动 |
| ALREADY_IN_PROGRESS | 同一资源上已有相同/冲突操作 | 并发 connect/stop |
| RESOLVE_FAILED | endpoint/name resolution 失败 | DNS/地址解析错误 |
| OPEN_FAILED | native socket open 失败 | socket open error |
| BIND_FAILED | 本地 bind 失败 | 地址占用/权限拒绝 |
| CONNECT_FAILED | 连接/配置阶段失败 | transport connect 失败 |
| CANCEL_FAILED | cancel 请求失败 | Asio cancel error |
| STOP_TIMEOUT | callback/handler/worker 未在期限内静止 | callback 阻塞 |
| JOIN_FAILED | worker join 无法完成或线程状态异常 | join/system error |
| CLOSE_FAILED | native close 未能确认完成 | close error |
| CALLBACK_FAILED | 用户回调抛异常或回调策略拒绝 | exception from callback |
| POSTCONDITION_FAILED | 操作返回但目标状态未满足 | success flag 与 snapshot 不一致 |
| INTERNAL_ERROR | 未分类内部故障 | invariant violation |

不得把 would_block、正常 operation_aborted、数据包 drop 与 transport fatal error 混为一类；应根据操作上下文映射到可重试/正常取消/数据丢弃/致命失败的独立结果字段或子码。

### 3.2 Cleanup failure

Cleanup failure 记录某一步的失败，不替换 primary failure。每条记录至少包含 step、attempted、error domain/code、native error、exception_ptr（若有）、snapshot_after、retryable hint 和发生时间/operation id。错误列表必须保序，允许同一步在多次 retry 中产生多条尝试记录。

### 3.3 Native error 与 C++ exception

- Native error：复制稳定的 domain/category name 与整数 value；不得把 Boost error_category 引用、临时 error_code 地址或平台句柄暴露给 public API。
- C++ exception：保留 std::exception_ptr 供同进程调用方诊断/重抛；同时提供不依赖 what() 文本解析的稳定 SocketErrorCode。
- std::system_error：记录 error_code 的 category/value/message；不可只保存 what()。
- std::bad_alloc：不得假设还可以成功分配诊断字符串/扩展 vector；异常路径必须允许无分配的最小错误记录或向外传播原始异常。
- 未知异常：保存 exception_ptr，映射 INTERNAL_ERROR；不可吞掉后伪装成成功。

### 3.4 Residual state

Residual state 是独立于 error code 的事实：native handle open、endpoint bound/configured、receive worker joinable、pending handler count、active callback count、callback admission 状态、Core owner 是否保留、session generation、quarantine 状态。error==NONE 不足以证明资源清理完成；cleanup_complete=true 必须由完整后置条件证明。

## 4. Result 结构与不变量

建议设计形状（伪代码，非实现声明）：

    struct FailureRecord {
      SocketErrorCode code;
      ErrorStage stage;
      NativeError native_error;
      std::exception_ptr exception;
      std::string diagnostic;  // best-effort; may be empty
    };

    struct CleanupStepResult {
      CleanupStep step;
      bool attempted;
      bool succeeded;
      FailureRecord failure;
      SocketSnapshot after;
    };

    struct CleanupReport {
      std::uint64_t operation_id;
      std::uint64_t generation;
      std::optional<FailureRecord> primary_failure;
      std::vector<CleanupStepResult> cleanup_steps;
      bool cleanup_complete;
      bool residual_resources;
      ResidualResourceHandle residual_owner;
      SocketSnapshot final_snapshot;
    };

    struct OperationResult {
      bool success;
      FailureRecord primary;
      CleanupReport cleanup;
      SocketSnapshot after;
    };

不变量：
- success == true 仅当 primary code 为 NONE、所有必需步骤成功、目标 postcondition 满足、无禁止的 residual。
- 若 primary failure 已存在，后续 cleanup failure 只能追加到 cleanup_steps，不得覆盖 primary。
- cleanup_complete == true 当且仅当资源达到目标静止状态；至少要求 callback admission closed、pending handlers=0、active callbacks=0、worker not joinable、native handle closed、Core 不再有待执行操作。
- residual_resources == true 时 residual_owner 必须有效且持有足以安全重试/延迟释放的 Core ownership；若无法提供 owner，API 不得谎报可恢复 residual，应返回不可恢复/owner transfer failure，并将问题提升到调用方生命周期管理器。
- 快照若不是 stop barrier 后的稳定快照，必须标记 OBSERVATIONAL，不能据此释放 owner。
- diagnostic 仅辅助展示，不能作为机器判断条件。

## 5. 异常安全与事务边界

### 5.1 create / factory

- 参数验证应在分配 native resource 前完成。
- 创建 Core/Facade 分阶段登记资源取得状态；每个成功 side effect 先登记，再执行下一步。
- create 失败必须返回明确 primary failure；若构造中已经取得 native handle/worker，则同步回滚。
- 回滚失败时返回 FAILED_RESIDUAL 并转交 residual owner；不能只返回空 socket 和错误码，同时把 Core 丢掉。
- 若构造/分配失败发生在无法建立 owner 的最早阶段，保持原始异常传播或映射到固定、无分配错误路径；不得制造一个需要 heap allocation 才能描述的“安全失败”。
- TCP unsupported / invalid enum 必须在任何资源分配前返回，且不调用 legacy factory。

### 5.2 connect / bind / resolve

每一阶段采用 attempt-before-side-effect 记录：
1. 记录 operation id、generation、目标 endpoint 和当前 snapshot。
2. 记录 open attempted，再执行 open；成功后立即记录 native handle open。
3. bind/resolve 每一步单独记录 attempted 与结果；失败后进入统一 rollback。
4. rollback 继续执行所有适用清理步骤；不得因为 close 失败而清除 open 状态。
5. 最终结果同时呈现 primary connect failure、rollback failures 和 residual snapshot。
6. 对于 UDP，remote endpoint 已解析/配置不等于远端在线或握手成功。

### 5.3 stop / disconnect

推荐 shutdown 顺序（每一步都独立记录、异常隔离）：
1. 关闭 callback admission，阻止新用户回调进入。
2. 请求 cancel pending asynchronous operations。
3. 停止事件循环/接收调度，但不把 io_context.stop 当成 handler 已销毁的证据。
4. 等待 pending handler 与 active callback drain；到 deadline 返回 STOP_TIMEOUT，但继续执行安全且不会破坏 owner 的后续步骤。
5. 若当前线程是 worker/callback 自身，拒绝 self-join，返回专用 INVALID_STATE/SELF_JOIN；不得 detach。
6. 对非当前 worker 执行 join；join 成功后确认 worker not joinable。
7. close native socket；close 失败则保留 open residual 和 native error。
8. 读取 final snapshot；仅当所有目标不变量满足才置 cleanup_complete。
9. 失败则保留 Core owner 并允许后续 retry；不得 reset 最后一个 shared_ptr。

注意：若 callback 仍在执行，close 是否可安全提前执行必须由具体 Core/Asio 设计与测试确定；本契约不允许为追求步骤列表而在 callback 仍可访问 native resource 时销毁其依赖。任何步骤的先后关系必须由明确的资源依赖图决定。

## 6. Quarantine Owner 与资源保留

### 6.1 所有权模型

- Core 只能有一个逻辑 native-resource owner；facade/cleanup handle 可共享该 owner 的控制块，但不能各自独立 close/join。
- ResidualResourceHandle 是 opaque move/shared handle，内部强持有 Core、generation 和 cleanup serialization primitive；不暴露 native handle。
- 失败后由调用方明确接管 handle，或转交给 RobotDriver/节点生命周期管理器的 quarantine owner。
- 不允许仅依赖 Core 自己的 worker capture shared_ptr<Core> 形成 self-cycle；也不允许最后一个 owner 在 worker 线程内析构导致 self-join。
- quarantine owner 必须有容量上限、诊断查询、明确的 shutdown policy 与进程退出策略；不能无限静默积累资源。
- 若进程退出时仍有 quarantine residual，必须通过上层 health/diagnostics 公开未清理状态；不得把析构日志当作清理成功。

### 6.2 retry_cleanup 契约

伪代码：

    CleanupReport retry_cleanup(ResidualResourceHandle& handle,
                                Deadline deadline);

约束：
- handle 为空/已完成：幂等返回 CLEAN。
- generation 不匹配或 owner 已转移：返回 STALE_HANDLE，不碰新 session。
- 同一 Core 上同时只能有一个 cleanup attempt；并发 retry 返回 ALREADY_IN_PROGRESS 或等待明确的串行化策略。
- 每次 retry 先重新采样状态，不重复执行已确认完成且不可重复的破坏性动作；对 cancel/close 等动作要定义幂等 adapter contract。
- 不把上次 timeout 当作本次必然失败；callback 退出后 retry 可继续 join/close。
- 只有稳定终态满足后才清空 handle 并释放 Core owner。
- retry 自身异常也必须写入本次 report；若仍有 residual，handle 保持有效。

### 6.3 禁止行为

- 禁止 detach worker 以“避免阻塞”。
- 禁止 close 失败后强制把 native_open 标志改 false。
- 禁止 timeout 后 reset 最后一个 Core owner。
- 禁止 cleanup 异常覆盖 primary exception。
- 禁止析构中抛异常或通过 terminate 隐式表达清理失败。
- 禁止仅凭 receiving=false 或 connected=false 推断线程/句柄已关闭。
- 禁止旧 session 的 retry handle 操作新 generation 的 Core。
- 禁止全局静态 quarantine registry 在未定义析构顺序/进程退出行为时作为默认逃生口。

## 7. noexcept 与异常传播边界

| API/路径 | 建议异常策略 | 原因 |
|---|---|---|
| public create/connect/start/stop/disconnect | 默认不标 noexcept；用 Result 表示预期操作失败，允许分配/内部异常按策略传播或被捕获记录 | string/vector/exception_ptr/lock/system call路径可能抛出 |
| retry_cleanup | 默认不标 noexcept；必须保留 handle，即使记录/诊断失败 | 重试涉及同步、分配与系统操作 |
| snapshot 简单只读 getter | 仅在锁策略与返回类型确实不分配时考虑 noexcept | 返回 string/vector 可能分配 |
| destructor | noexcept；best-effort、不得依赖返回值 | C++析构异常会导致terminate |
| RAII guard destructor | noexcept；只执行不抛的计数/状态恢复；不能做不可控阻塞 join | 栈展开期间二次异常风险 |
| callback trampoline | catch(...) 边界必须明确；保存 exception_ptr/错误计数，RAII 恢复 active count；是否重新抛由 worker contract 决定 | 不得让异常穿越 Asio/线程入口边界 |
| cleanup step wrapper | catch(...) 后追加失败记录；若记录分配失败，保留最小固定码/exception_ptr并继续必要步骤 | 一个清理异常不能短路其他资源回收 |

特别规则：Result 的构造/复制本身可能分配，不能因为函数返回 Result 就自动声明 noexcept。若要保证 noexcept，需证明所有路径无分配、无可抛锁操作、无用户代码调用，并有静态/运行时证据。

## 8. RobotDriver / Subscriber 集成约束

- RobotDriver connect transaction 保留最初 connect failure/exception；control/diagnostics 两路 cleanup 分别记录，任何一路失败不得跳过另一路。
- Subscriber stop 仅能清理自己拥有的 receive lease；不能无条件停止共享 Socket 的全局 receive loop。
- Subscriber callback target 必须在 admission close + active callback drain 后销毁；裸 this 的生命周期风险必须通过两阶段 start/stop、弱引用或显式 owner 关系解决。
- RobotDriver 只有在所有 Subscriber 已 quiescent 后才销毁 callback target，再清理 sockets；如任一 stop timeout，必须接管 quarantine handle。
- 新 connect 必须检查前一 generation 的 residual；默认拒绝覆盖或并发启动新 session，除非显式隔离且证明旧 Core 与新 Core 完全独立。
- CleanupReport 必须由 connect/disconnect 返回或可查询，不能只写日志，不能被下一次 connect 静默覆盖。

## 9. 验收矩阵（均未执行）

| ID | Arrange / Act | 必须断言 | 状态 |
|---|---|---|---|
| ERR-01 | open 成功、bind 失败、rollback close 成功 | primary=BIND_FAILED；cleanup complete；handle closed | NOT_RUN |
| ERR-02 | bind 失败且 rollback close 失败 | primary仍为BIND_FAILED；cleanup含CLOSE_FAILED；residual owner有效 | NOT_RUN |
| ERR-03 | cancel失败但join/close可继续 | cancel错误保留；后续步骤仍执行 | NOT_RUN |
| ERR-04 | stop deadline 到期、callback仍活动 | STOP_TIMEOUT；Core owner保留；禁止detach/reset | NOT_RUN |
| ERR-05 | callback退出后 retry | 同一generation retry成功；最终owner释放 | NOT_RUN |
| ERR-06 | close失败后再次retry | native-open保持真实；close成功后才CLOSED | NOT_RUN |
| ERR-07 | primary exception与cleanup exception同时发生 | primary exception_ptr不变；cleanup exception独立追加 | NOT_RUN |
| ERR-08 | cleanup第一步抛异常 | 其余独立安全步骤仍被尝试 | NOT_RUN |
| ERR-09 | bad_alloc发生于诊断记录构造 | 原始异常/最小错误码保留；不伪造cleanup complete | NOT_RUN |
| ERR-10 | callback抛异常 | active count经RAII归零；异常不逃逸线程入口；worker状态可观察 | NOT_RUN |
| ERR-11 | worker线程内部请求stop | 返回SELF_JOIN/INVALID_STATE；不join自身、不detach | NOT_RUN |
| ERR-12 | 两线程同时retry_cleanup | 仅一个清理事务执行；另一个得到ALREADY_IN_PROGRESS或按合同等待 | NOT_RUN |
| ERR-13 | retry handle generation陈旧 | 返回STALE_HANDLE；不操作新session | NOT_RUN |
| ERR-14 | residual handle被销毁前未清理 | owner转交上层quarantine管理器；不得静默释放最后owner | NOT_RUN |
| ERR-15 | 所有资源清理完成 | callback=0、handler=0、worker not joinable、native closed，cleanup_complete=true | NOT_RUN |
| ERR-16 | 仅receiving=false但thread joinable | 仍需join或报告residual，不可成功 | NOT_RUN |
| ERR-17 | 仅connected=false但native handle open | 仍执行close/retry并保留open状态 | NOT_RUN |
| ERR-18 | cleanup report snapshot为OBSERVATIONAL | 不允许据此释放owner | NOT_RUN |
| ERR-19 | 新connect遇到旧generation residual | 拒绝覆盖或显式隔离；旧handle不触及新Core | NOT_RUN |
| ERR-20 | factory TCP/invalid enum | 资源分配前失败；无legacy fallback、无residual | NOT_RUN |
| ERR-21 | destructor遇到cleanup失败 | 不抛异常；诊断/owner转交按已定义策略处理 | NOT_RUN |
| ERR-22 | 多个Subscriber共享Socket | receive lease规则阻止一个Subscriber误停全局接收 | NOT_RUN |
| ERR-23 | operation success但snapshot不满足postcondition | 返回POSTCONDITION_FAILED，不得success=true | NOT_RUN |
| ERR-24 | repeated stop/disconnect/retry | 幂等且不重复释放/join；最终状态与native资源一致 | NOT_RUN |

## 10. 实施切片与门禁

1. ERR-0 错误模型：冻结 ErrorStage、FailureRecord、NativeError 和 stable code mapping；补充 C++17 类型布局，不引入 std::expected。
2. ERR-1 cleanup report：实现逐步骤 CleanupStepResult、primary preservation、异常边界与 operation/generation id。
3. ERR-2 Core ownership：实现 ResidualResourceHandle / explicit owner transfer；明确禁止 worker self-cycle 与最后 owner 在线程内析构。
4. ERR-3 retry serialization：实现 retry_cleanup、deadline、generation guard、并发门禁和幂等步骤。
5. ERR-4 Subscriber lease：receive ownership/token、callback admission/drain 与 target destruction 顺序。
6. ERR-5 RobotDriver transaction：connect/disconnect 保留 primary exception，双通道清理并返回 CleanupReport。
7. 每切片先做 compile + deterministic Fake tests，再做 UDP loopback/native error injection、TSan/ASan，最后才进入 ROS 2 Control/SIL/HIL；不得跳级标记通过。

## 11. 未决设计决策与风险

- quarantine owner 放在 RobotDriver、ROS lifecycle node 还是显式 transport manager：需结合插件 unload 与进程退出策略决策。
- deadline 过期后后台重试由调用方驱动还是管理器调度：不得默认隐式后台线程。
- NativeError 的稳定 domain 命名与 Windows/POSIX/Boost映射：需在支持平台列表确定后冻结。
- std::exception_ptr 是否暴露于 public API：可能造成编译器/标准库 ABI 绑定；可保留于进程内诊断层而 public DTO 仅暴露稳定 code/message。
- cleanup_steps vector/string 在内存耗尽时的记录能力：需设计固定容量记录或无分配 fallback。
- Core close 失败是否可重试以及平台语义：必须以目标平台实测为准，不能仅凭 Asio接口推断。
- snapshot 的一致性等级和资源释放门槛必须由测试证据支持。

## 12. 状态、限制与下一节点

- 本轮仅完成错误分类、异常安全、残留 owner 与重试清理的静态设计审查。
- 未实现 FailureRecord、CleanupReport、ResidualResourceHandle、quarantine manager、retry_cleanup、receive lease 或 RobotDriver 适配。
- ERR-01至ERR-24全部 NOT_RUN；未运行 C++ 编译、CMake、gtest、UDP loopback、native error injection、TSan/ASan、ROS 2 Control。
- 未执行 VAL3/CS9、SIL/HIL、FAT/SAT 或实机验证；工程级验收未通过。
- 未修改固定上游、未创建/应用/合并 PR；TODO-EXT-001仍未授权。
- 下一节点：§9.3.296 / SERVO-879：SocketV2 CleanupReport / ResidualResourceHandle API surface 与 quarantine ownership 实施边界设计。重点把本轮语义映射为可编译的 C++17 public/private 类型、句柄复制/移动规则、owner transfer、retry 状态机和 RobotDriver/ROS lifecycle 接入契约；继续只做设计，除非用户另行明确授权。
