# Stäubli Socket / Subscriber 初始化与清理契约 API 设计

- 审查节点：§9.3.291 / SERVO-874
- 日期：2026-11-10
- 固定上游基线：ICube-Robotics/staubli_driver_ros2@bd658e2d266e315d2ee35f985fb352ea88306b79
- 性质：实现前接口契约设计；不包含上游补丁、构建或运行时验证

## 1. 目标与结论

本节点把 SERVO-873 的 rollback guard 设计进一步收敛为可实现、可测试的 Socket / Subscriber API 契约。核心原则：API 返回值必须描述操作结果，独立 snapshot 必须描述操作后的资源事实；二者不能相互替代。特别是 false、异常、stop 超时或析构返回都不能推导出底层资源已不存在。

本轮只定义接口形状和状态语义，不修改 ICube 上游。所有示例均为设计伪代码，不保证可直接编译。

## 2. 固定源码事实

| 文件 | Blob SHA | 与本设计直接相关的事实 |
|---|---|---|
| communication/socket.hpp | 230af198337e5d047b29b2bbf6354a698fb3a390 | Socket 的 connect/disconnect/start/stop 均返回 bool；无 error code、资源状态快照或 false 后残留契约 |
| communication/udp_socket.hpp | 31eb5e2e9218e17160fc10dfbd72d77be4b3b0e5 | UDP 实现通过 PIMPL 暴露相同 bool API |
| src/communication/udp_socket_impl.hpp | 1309a8f2d59e8295869e178af82a66868bb911ff | connect catch 中 close 后返回 false；disconnect 仅在 is_connected() 为 true 时 close；stop 对 not-receiving 返回 true；stop 调 io_service.stop/join 后才清 receiving；callback 执行用户函数后重投递 |
| real_time_socket_subscriber.hpp | 330839cb25e53fe961541f29f634722bec4a47c4 | Subscriber 构造函数、init_communication 为 protected；没有显式 start/stop 状态或 callback 屏障成员 |
| src/real_time_socket_subscriber.cpp | e2cd8fc50b2b13d9e31b2c024e90f9da76107622 | 构造期间 init 并启动 receive；callback 捕获裸 this；析构无条件 socket_->stop_receive_thread()；构造失败抛 runtime_error |
| real_time_socket_interface.hpp | e4d4650f59d2eb95133f5e948431ebe2073a6667 | Interface 继承 Subscriber，公开发送接口，无显式初始化/停止契约 |
| src/real_time_socket_interface.cpp | eda0a830cfe0118e07bc3423ad0f455bd50d610c | 基类构造完成后再分配发送 buffer；析构不执行额外操作 |
| src/robot_driver.cpp | ede48a314856a455df9d8434f354aaf9fbc47bff | RobotDriver 创建 Subscriber 时即启动线程；connect 多路径清理；析构为空 |

### 2.1 由实现可确认的边界

1. UDP connect 的异常分支会尝试 close open socket，但 close 本身未以 error_code 形式报告，且无法从 Socket API 读取底层 is_open、绑定状态或 native error。
2. UDP disconnect 若 is_connected() 已为 false，会直接返回 all_ok，不检查或关闭可能仍 open 的 socket；若 receiving，先 stop，但 stop 结果失败仍继续 close，最终无论 close 成功与否都把 is_connected_ 置 false。
3. stop_receive_thread 对 receiving=false 返回 true；该结果仅表示当前实现按标志认为线程未运行，不能证明 callback 已 drain 或 thread object 不可 joinable。
4. start_receive_thread 在设置 callback 后检查连接/接收状态；线程创建若抛异常没有结构化结果。接收线程标志在创建 std::thread 前置 true，构造异常时状态可能残留。
5. Subscriber 构造函数启动 callback 后才返回对象；若派生 Interface 后续构造抛异常，基类析构会执行，但当前 Socket stop 语义与并发/异常屏障未形成可证明的 callback-target 生命周期契约。
6. handle_data_received 对 error 非空仍调用用户 callback；本设计不把此节点扩展为接收错误语义审计，但接口应允许将 transport error 记入结果。

## 3. 统一结果与状态模型

### 3.1 基础状态

建议将 Socket 资源状态拆分为两个正交状态机，避免一个 connected bool 混合底层句柄与接收线程：

| 维度 | 状态 | 语义 |
|---|---|---|
| TransportState | CLOSED | 无已打开底层句柄、无本地绑定资源 |
| TransportState | OPEN_UNBOUND | 句柄已打开但尚未成功 bind/配置完成 |
| TransportState | BOUND | 本地 endpoint 已绑定，remote endpoint 可能未完成 |
| TransportState | READY | endpoint 配置完成，可执行发送/接收 |
| TransportState | CLOSING | 正在取消异步操作并关闭句柄 |
| TransportState | FAILED_RESIDUAL | 操作失败，snapshot 仍观察到句柄/绑定等残留 |
| ReceiveState | NOT_STARTED | 从未启动或已确认完全停止 |
| ReceiveState | STARTING | callback/异步接收已登记，线程启动尚未确认完成 |
| ReceiveState | RUNNING | 接收循环运行中 |
| ReceiveState | STOPPING | 已关闭 callback admission，正在取消/排空/join |
| ReceiveState | STOPPED | 无活动 callback、无待处理 handler、线程已 join |
| ReceiveState | FAILED_RESIDUAL | stop/start 失败且仍有线程、handler 或 callback 残留 |

状态必须来自实现内部可观测事实；不得仅由最近一次 API 返回值推导。

### 3.2 结果结构

以下为建议伪头文件：

    enum class OperationCode {
      OK, INVALID_ARGUMENT, INVALID_STATE, ALREADY_IN_STATE,
      OPEN_FAILED, OPTION_FAILED, BIND_FAILED, RESOLVE_FAILED,
      THREAD_CREATE_FAILED, CANCEL_FAILED, JOIN_FAILED,
      CLOSE_FAILED, CALLBACK_DRAIN_TIMEOUT, CALLBACK_EXCEPTION,
      INTERNAL_ERROR
    };

    struct OperationResult {
      bool success;
      OperationCode code;
      int native_error_value;       // 0 when not applicable
      std::string native_error_text;
      bool operation_attempted;
      std::string detail;
    };

    struct SocketSnapshot {
      TransportState transport_state;
      ReceiveState receive_state;
      bool native_handle_open;
      bool local_endpoint_bound;
      bool remote_endpoint_configured;
      bool receive_thread_joinable;
      size_t pending_handlers;
      size_t active_callbacks;
      uint64_t generation;
    };

    struct SocketOperationResult {
      OperationResult operation;
      SocketSnapshot after;
    };

native_error_value/text 必须来自实际底层错误对象；没有可用 native error 时明确置零/空，不得伪造 errno。SocketSnapshot 是瞬时快照，不承诺读取后状态不再变化；需要稳定终态时必须由 stop/disconnect 屏障建立 happens-before，再采样。

### 3.3 API 结果与 snapshot 的判读

| operation.success | snapshot | 判读 |
|---|---|---|
| true | 目标终态 | 操作成功且观测到目标状态 |
| false | 资源仍存在 | 操作失败并有残留，调用方必须进入 FAILED_RESIDUAL 处置 |
| false | 资源已清零 | 操作报告失败，但资源回收结果已由 snapshot 证实；仍保留失败原因 |
| true | 非目标状态 | 契约违例，返回 INTERNAL_ERROR 并记录残留，不得对外宣称成功 |

## 4. Socket connect / disconnect 契约

建议新增详细 API，同时保留现有 bool API 作为兼容包装：

    SocketOperationResult connect_detailed(const EndpointConfig&);
    SocketOperationResult disconnect_detailed(StopPolicy);
    SocketSnapshot snapshot() const;

### 4.1 connect_detailed

- 调用前需保证前一次生命周期操作已结束；并发 connect/disconnect 必须由同一生命周期 mutex 串行化。
- 在任何可能打开句柄的底层调用前，记录 operation_attempted=true。
- 失败时不得只设置 connected=false；必须执行 best-effort rollback：取消接收、等待 callback/handler、关闭句柄，并采集 snapshot。
- rollback 任一步失败，返回原始 connect failure 作为 primary code，清理失败另存于 cleanup report；snapshot 若显示残留则状态为 FAILED_RESIDUAL。
- 成功必须同时满足 native handle open、local bind 完成、remote endpoint 配置完成；若协议实现的连接语义不同，应以 transport-specific capability 明确声明。

### 4.2 disconnect_detailed

- disconnect 是幂等操作：CLOSED + STOPPED 再次 disconnect 返回 success=true、code=ALREADY_IN_STATE、operation_attempted=false；但这只适用于 snapshot 确认所有资源关闭。
- 若 connected 标志为 false 但 native_handle_open=true，仍必须尝试关闭；不得沿用当前仅检查 is_connected() 的早退路径。
- stop 接收失败不能阻断后续 close 尝试；但最终 success 必须同时要求线程/handler/callback 已排空且底层句柄已关闭。
- close 失败后不得把状态强制写成 CLOSED；应保留 FAILED_RESIDUAL 和 native error，允许后续 retry。
- 若调用线程本身处于该 socket callback 中，禁止同步 join 自身；返回 INVALID_STATE/SELF_JOIN_FORBIDDEN 并要求由外部生命周期线程完成 stop。

## 5. Receive stop 的幂等与 callback 生命周期屏障

### 5.1 stop 契约

建议接口：

    ReceiveStopResult stop_receive(StopMode mode, Duration timeout);

StopMode 至少区分 DRAIN（拒绝新 callback 并等待已进入 callback 退出）与 CANCEL_PENDING（取消尚未派发的 handler；仍需等待正在执行的 callback 退出）。

成功条件必须全部满足：
- admission_closed=true，线性化点之后不得开始新用户 callback；
- 已登记的 pending handler 已取消或完成，不再可能调用 callback；
- active_callbacks==0；
- receive worker 已退出且 thread object 已 join；
- snapshot 的 ReceiveState 为 STOPPED。

重复 stop：若上述终态已满足，返回 ALREADY_IN_STATE；如果上次 stop 失败且残留仍在，必须重试清理或返回明确失败，不得因 receiving flag=false 而虚报成功。

### 5.2 callback guard

每次派发 callback 前在同一同步域内检查 admission_open 并增加 active_callbacks；callback 返回或抛异常时通过 RAII 减少计数并通知 drain condition variable。stop 的线性化点先关闭 admission，再取消异步操作，最后等待 active_callbacks 归零和 worker join。

不得在 callback 仍可执行时销毁捕获裸 this 的 Subscriber。更稳妥的后续实现可让 callback 捕获 shared callback-state，而不是直接捕获 Subscriber this；但无论选哪种方式，都必须证明对象析构 happens-after callback drain。

### 5.3 并发调用

- 同一 socket 的 start/stop/disconnect 由单一 lifecycle mutex 或等价状态机串行化。
- 两个 stop 并发：第二个调用等待第一个终态，或返回 IN_PROGRESS；不得重复 join 同一 std::thread。
- start 与 stop 并发：按锁顺序线性化；stop 先胜出则 start 拒绝，start 先胜出则 stop 必须停止新启动线程。
- callback 内 self-stop/self-disconnect 不执行阻塞 join；返回专用错误码并将清理责任交还生命周期线程。

## 6. Subscriber 两阶段初始化契约

构造函数只保存依赖、初始化纯内存状态，不启动异步线程；显式 start() 才开始通信。

    enum class SubscriberState { CREATED, STARTING, RUNNING, STOPPING, STOPPED, FAILED_RESIDUAL };

    struct SubscriberInitResult {
      OperationResult operation;
      SubscriberState state_after;
      SocketSnapshot socket_after;
    };

    struct SubscriberStopResult {
      OperationResult operation;
      SubscriberState state_after;
      SocketSnapshot socket_after;
    };

    explicit RealTimeSocketSubscriber(std::shared_ptr<Socket> socket);
    SubscriberInitResult start();
    SubscriberStopResult stop(StopMode, Duration);
    SubscriberSnapshot snapshot() const;
    ~RealTimeSocketSubscriber() noexcept;

### 6.1 start() 语义

1. 仅允许 CREATED 或 STOPPED 状态启动；RUNNING 返回 ALREADY_IN_STATE，FAILED_RESIDUAL 拒绝重启。
2. 验证 socket 非空、transport ready、receive state STOPPED；将状态置为 STARTING。
3. 建立 callback-state/admission barrier，再调用 socket.start_receive_detailed()。
4. 只有底层 receive worker 和首个异步 receive handler 注册成功，状态才变为 RUNNING。
5. 任一步失败，start() 自行调用 stop/drain/close-admission 回滚；返回 primary init failure 和独立 cleanup result。若回滚未清干净，状态必须为 FAILED_RESIDUAL。
6. RealTimeSocketInterface 的派生成员初始化（例如 outgoing buffer）应在 start() 之前完成，避免基类构造期间已启动线程、派生构造随后失败的窗口。

### 6.2 stop() 与析构

- stop() 是可显式检查结果的主要生命周期 API；调用方必须处理失败与残留。
- 析构函数 noexcept，只能 best-effort 调用 stop；不得抛异常，也不得把析构成功作为资源已释放的测试证据。
- 析构前必须有调用方责任规则：如果 stop 返回 FAILED_RESIDUAL，所属 RobotDriver 不得直接释放唯一的 transport owner；应保留诊断、按策略隔离/重试或将错误提升给上层生命周期管理。
- Subscriber 不应无条件对共享 Socket 调用 stop，除非契约明确该 Subscriber 独占 receive ownership。建议为 Socket 定义唯一 receive owner 或显式 lease/token，避免多个 Subscriber 共享一个接收线程时互相停止。

## 7. CleanupReport 与 RobotDriver 事务集成

    struct CleanupStepResult {
      CleanupStep step;
      bool attempted;
      OperationResult operation;
      SocketSnapshot snapshot_after;
    };

    struct CleanupReport {
      ConnectFailure primary_failure;
      std::vector<CleanupStepResult> steps;
      bool cleanup_complete;
      bool residual_resources;
      std::exception_ptr primary_exception;
      std::vector<std::exception_ptr> cleanup_exceptions;
      SocketSnapshot control_after;
      SocketSnapshot diagnostics_after;
    };

约束：
- primary connect failure/exception 永远优先；cleanup failure 作为次级证据追加。
- cleanup 每步独立 try/catch，不能因为一个 stop/disconnect 失败而跳过另一通道清理。
- 先关闭 callback admission 并排空两个 Subscriber，再 disconnect 两个 Socket；不可先销毁 callback target。
- 每个 socket 都按 attempted 标记清理，不以 is_connected() 单一状态作为依据。
- 只有两个通道均达到 STOPPED+CLOSED 且无 callback/handler/thread 残留，cleanup_complete 才可为 true。
- CleanupReport 必须可通过受同步保护的 getter 或 ConnectResult 返回；不能只写日志，也不能让下一次 connect 无提示覆盖前次失败证据。

## 8. 兼容性迁移策略

1. 第一阶段新增详细 API 和 snapshot，保留现有纯虚 bool API 会要求 Fake/第三方 Socket 适配器同步实现两套方法；更稳妥的方式是新增独立 v2 interface 或提供非纯虚默认 adapter，但默认 adapter 无法伪造 native snapshot，必须明确 capability=LIMITED。
2. 对现有 bool connect/start/stop/disconnect 包装：仅在详细结果 success 且 snapshot 达到目标状态时返回 true；任何 residual 或 snapshot 不可用的情况 fail closed。
3. 不能静默改变既有虚函数签名，避免破坏 ABI/API；需要主版本升级或明确的 source compatibility 迁移。
4. 先定义 Socket receive ownership；当前 Subscriber 对共享 Socket 调 stop 的副作用需纳入迁移。
5. API 文档必须说明线程安全范围、超时语义、调用线程限制、native error 来源、snapshot 一致性等级和重试规则。

## 9. 验收测试规格

| ID | Arrange / Act | 必须断言 | 状态 |
|---|---|---|---|
| API-01 | connect 在 open 后 bind 失败 | 返回失败；snapshot 不隐瞒 open residual；rollback 关闭成功才 CLOSED | NOT_RUN |
| API-02 | close 失败 | 返回 CLOSE_FAILED；不得伪造 CLOSED；保留 native error/residual | NOT_RUN |
| API-03 | connected flag=false 但 native handle open | disconnect 仍尝试 close | NOT_RUN |
| API-04 | stop 时 receiving=false 但 thread joinable | 不得直接 ALREADY_IN_STATE；必须 join 或报告 residual | NOT_RUN |
| API-05 | stop 被重复调用 | 第二次幂等且不重复 join | NOT_RUN |
| API-06 | 两线程并发 stop | 无 double join、data race、死锁 | NOT_RUN |
| API-07 | start_receive 创建线程抛异常 | STARTING 回滚，状态准确，无线程残留 | NOT_RUN |
| API-08 | callback 正在执行时 stop | admission 关闭；stop 等待 active callback 归零后才成功 | NOT_RUN |
| API-09 | stop 后尝试派发旧 pending handler | 用户 callback 不得再进入 | NOT_RUN |
| API-10 | callback 内调用 self-stop | 返回专用错误，不 self-join、不死锁 | NOT_RUN |
| API-11 | Subscriber start 部分失败 | start 返回 primary failure 和 cleanup report；残留状态准确 | NOT_RUN |
| API-12 | 派生 Interface buffer 初始化失败 | 线程尚未启动或由 factory 显式回滚，不得 UAF | NOT_RUN |
| API-13 | Subscriber stop 后析构 | 析构不重复停止已关闭的共享接收资源 | NOT_RUN |
| API-14 | callback 抛异常 | active count RAII 归零；异常策略明确且 worker 状态可见 | NOT_RUN |
| API-15 | connect 异常且 cleanup 同时失败 | 原始异常保留；清理异常独立记录 | NOT_RUN |
| API-16 | CleanupReport 多步骤中第一步失败 | 其余通道和步骤仍继续执行 | NOT_RUN |
| API-17 | snapshot 采样与并发状态转换竞争 | snapshot 标明一致性边界，不作稳定终态误判 | NOT_RUN |
| API-18 | RobotDriver 新 connect 与旧 disconnect 并发 | 生命周期串行化，generation 不串会话 | NOT_RUN |

### 9.1 测试分层

- Fake Socket 单元测试：结果状态机、幂等、并发 stop、callback barrier、异常保留。
- UDP adapter 单元/loopback：真实 Asio open/bind/close/cancel/join 和 native error snapshot。
- Subscriber/RobotDriver 集成：两阶段 start、双通道 rollback、析构、旧 session generation。
- ROS 2 Control：硬件生命周期错误传播与插件 unload/reload。
- SIL/HIL、VAL3/CS9、FAT/SAT 和实机：独立系统级验证，不由上述单测替代。

## 10. P0/P1 决策与未决问题

| 优先级 | 决策/问题 | 解除条件 |
|---|---|---|
| P0 | 先实现底层可观测 snapshot，再实现 rollback guard；否则无法证明 false/exception 后 residual 清理结果 | Socket v2 contract 与 UDP adapter 实现评审 |
| P0 | 明确接收线程唯一 owner/lease，禁止多个 Subscriber 无约束地 stop 同一 Socket | 所有权模型与 RobotDriver fixture 验证 |
| P0 | stop 的线性化点、pending handler cancel、active callback drain、worker join 必须作为一个契约 | 确定性 Fake 与 UDP loopback 测试 |
| P1 | 定义 native error 保存与错误码映射，区分 Asio error_code、std::system_error 与普通异常 | 适配器错误映射表 |
| P1 | 明确 timeout 到期后的后台清理/重试责任；超时不能让对象析构越过活动 callback | 生命周期 owner 设计 |
| P1 | 明确 snapshot 一致性：瞬时观察 vs stop barrier 后稳定终态 | API 文档与并发测试 |
| P1 | 明确详细 API 与旧 bool API 的 ABI/source compatibility 方案 | 版本策略批准 |

## 11. 本轮结论与执行边界

- SERVO-874 完成的是接口契约设计，不是代码实现。
- 未实现 SocketOperationResult、SocketSnapshot、Detailed API、CallbackGuard、Subscriber 两阶段初始化、CleanupReport 或 generation。
- API-01 至 API-18 全部 NOT_RUN；没有构建、单元测试、loopback、TSan/ASan 或 ROS 2 Control 集成结果。
- 未执行 SIL/HIL、VAL3/CS9、FAT/SAT 或实机验证；未达到工程级验收。
- 未修改 ICube 上游、未应用任何 PR；TODO-EXT-001 仍未授权，不合并 MotionControlAlgorithms。

## 12. 下一节点

§9.3.292 / SERVO-875：Socket v2 接口兼容迁移与 UDP adapter 状态观测实现切片设计。重点确定旧 bool Socket 的 source/ABI 兼容边界、native handle snapshot 的最小侵入落点、UDP open/bind/resolve/close 的逐步状态记录，以及 stop timeout 后资源 owner 的保留策略。仍先做设计，不修改上游，除非用户另行明确授权。
