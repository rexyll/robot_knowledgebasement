# Stäubli RobotDriver 事务式 connect rollback guard 最小补丁设计

- 审查节点：§9.3.290 / SERVO-873
- 日期：2026-11-10
- 固定上游基线：ICube-Robotics/staubli_driver_ros2@bd658e2d266e315d2ee35f985fb352ea88306b79
- 性质：实现前设计审查；不包含代码补丁、构建或运行时验证

## 1. 目标与边界

目标是将 RobotDriver::connect 从多处分支手工 disconnect 改成单一连接事务：只有 control socket、diagnostics socket、两个 receive callback、接口 readiness、首帧 state 和 protocol version 全部通过后才 commit；任何失败或异常均触发 best-effort rollback，并留下可追踪的清理结果。

边界：
- 不修改本轮固定上游源码；本文件只定义建议补丁。
- rollback 成功只代表本机资源清理 API 报告成功，不代表机器人已停止或安全状态已验证。
- 不将静态设计、Fake 测试或 loopback 测试等同于 CS9、SIL/HIL、FAT/SAT 或实机验收。
- TODO-EXT-001 仍未授权，不合并 MotionControlAlgorithms 或其他未授权 PR。

## 2. 固定源码事实与补丁落点

| 文件 | Blob SHA | 设计相关事实 |
|---|---|---|
| src/robot_driver.cpp | ede48a314856a455df9d8434f354aaf9fbc47bff | connect 多处分支手工 disconnect；control connect false 直接返回；Subscriber 构造异常未捕获；disconnect 先 reset interface/subscriber 再 stop/disconnect；空析构 |
| include/robot_driver.hpp | 62c87a6741aa082db4599bb2c048aec0fcd7a464 | 双 Socket 和两个 shared_ptr interface/subscriber 成员；当前无 connect/disconnect 互斥 |
| src/real_time_socket_subscriber.cpp | e2cd8fc50b2b13d9e31b2c024e90f9da76107622 | Subscriber 构造调用 init_communication；start_receive_thread false 时 throw runtime_error；callback 捕获裸 this；析构无条件调用 stop_receive_thread |
| src/real_time_socket_interface.cpp | eda0a830cfe0118e07bc3423ad0f455bd50d610c | Interface 继承 Subscriber；基类构造成功后再分配 outgoing buffer |
| include/communication/socket.hpp | 230af198337e5d047b29b2bbf6354a698fb3a390 | connect/start/stop/disconnect 均为 bool；接口没有定义 false 后的 residual-state contract |

## 3. 事务状态模型

每次 connect attempt 使用独立 ConnectAttempt 状态，不用 socket 当前 is_connected() 单独推断曾经建立的资源。

| 状态字段 | 何时置位 | 作用 |
|---|---|---|
| attempt_started | 进入 connect 后立即 | 记录一次连接事务 |
| control_connect_attempted | 调用 C.connect 前 | 即使 connect 返回 false 或抛异常，也执行 C cleanup |
| control_connect_reported_success | C.connect 返回 true 后 | 诊断/审计；不是 cleanup 的唯一条件 |
| control_subscriber_construction_attempted | 创建 CI 前 | 构造抛异常时，区分对象不存在但 socket 可能已部分启动 |
| control_interface_owned | CI 完整构造并赋值后 | rollback 时先 reset，借助析构 stop callback |
| diagnostics_connect_attempted / reported_success | 同 diagnostics | 对 D 独立跟踪 |
| diagnostics_subscriber_construction_attempted / owned | 同 diagnostics subscriber | 处理构造异常与完整对象清理 |
| committed | 所有成功门禁通过后 | true 后 guard 不再 rollback |
| cleanup_report | 每个清理步骤完成后 | 保存步骤结果、异常、残留状态 |

control_subscriber_construction_attempted 不是 start_receive_thread 确实被调用的精确证据，因为 Subscriber 构造在调用 start 前还会检查 socket connected/receiving。推荐的最小 seam 是将 Subscriber 初始化改为显式 factory/result，使 start attempted 成为可观察事件；在没有该 seam 前，只能对构造异常路径采取保守 cleanup，并且必须先证明 driver 对 socket 的独占所有权。

## 4. rollback guard 结构建议

建议在 robot_driver.cpp 内实现私有、不可复制的 ConnectRollbackGuard，或使用等价的局部 scope guard。它只引用 RobotDriver，不拥有 Socket；不在析构中执行可能阻塞且不可观测的复杂逻辑。

伪代码（设计表达，不是可直接编译补丁）：

    ConnectRollbackGuard rollback(*this);
    try {
        rollback.mark_control_connect_attempted();
        if (!control_socket_->connect(...)) {
            return rollback.fail(ConnectFailure::CONTROL_CONNECT);
        }

        rollback.mark_control_subscriber_construction_attempted();
        auto ci = make_control_interface(control_socket_);
        control_interface_ = std::move(ci);
        rollback.mark_control_interface_owned();

        rollback.mark_diagnostics_connect_attempted();
        if (!diagnostics_socket_->connect(...)) {
            return rollback.fail(ConnectFailure::DIAGNOSTICS_CONNECT);
        }

        rollback.mark_diagnostics_subscriber_construction_attempted();
        auto ds = make_diagnostics_subscriber(diagnostics_socket_);
        diagnostics_subscriber_ = std::move(ds);
        rollback.mark_diagnostics_subscriber_owned();

        if (!readiness_and_state_checks()) {
            return rollback.fail(ConnectFailure::READINESS_OR_PROTOCOL);
        }

        rollback.commit();
        return true;
    } catch (...) {
        auto original = std::current_exception();
        rollback.rollback_noexcept(ConnectFailure::EXCEPTION);
        std::rethrow_exception(original);
    }

关键规则：
- 每个 attempted 标记必须在调用可能产生副作用的外部 API 之前写入。
- fail() 必须先显式运行 rollback 并记录结果，再返回 false；不能只依赖局部对象析构。
- guard 析构函数为 noexcept，只作为遗漏显式 fail/异常路径的最后保险；不得抛出异常。
- 异常路径先保存 exception_ptr，执行不抛异常的 rollback，再 rethrow 原始异常；清理异常只写入 cleanup report，不能覆盖原始异常。
- 成功路径只有在所有门禁通过后才调用 commit。
- rollback 不得递归调用 public disconnect()；应抽取内部 cleanup_connection()，避免重复状态判断、日志和错误信息丢失。

## 5. 唯一清理顺序与资源归属

rollback 顺序冻结如下：

1. 阻止新连接/新 callback admission：如果 socket adapter 支持 cancel/close admission，先请求停止接收；不得先销毁 callback target。
2. 销毁已完整构造的 diagnostics subscriber：reset diagnostics_subscriber_，让其 stop barrier 等待 callback 退出。
3. 销毁已完整构造的 control interface：reset control_interface_，同样等待 callback 退出。
4. 处理构造中途抛异常、对象未赋值的路径：对对应 socket 执行 stop；必须由显式 Subscriber factory 精确告知 start 是否已尝试。若尚未实现 factory，则只在 driver 独占 socket、stop 被定义为幂等且安全的前提下进行 best-effort stop。
5. 断开 diagnostics socket：对 diagnostics_connect_attempted 为 true 的 socket 执行 disconnect，即使 connect 返回 false；否则无法清除“返回 false 但底层已部分建立”的残留资源。
6. 断开 control socket：同样对 control_connect_attempted 为 true 的 socket执行 disconnect。
7. reset_data()：清空 state、diagnostic cache 和 last valid sequence。
8. 读取 residual snapshot：采集 is_connected()、is_receiving()、active callback（若 adapter 可提供）及 cleanup result；任何残留都必须标记为 cleanup incomplete。

此顺序将 callback target 销毁放在 socket disconnect 前，避免 callback 捕获裸 this 时发生 use-after-free。对于两个通道，跨 socket 的绝对先后不是实时语义；只要求每个通道自己的 callback drain happens-before 该通道 disconnect。若测试需要全局事件顺序，使用共享 recorder/barrier，不比较两个 Fake 的本地序号。

## 6. bool API、异常和失败原因

### 6.1 最小兼容方案

保留现有 bool connect(...) API：
- 正常建立且通过所有门禁：true。
- 任一阶段失败：rollback 后 false。
- 原有构造异常：rollback 后继续传播原始异常（不静默改成 false）。
- cleanup failure 不改变原始 connect failure 的身份，但必须可查询/记录。
- 不允许因为 cleanup failure 而返回 true。

### 6.2 建议的内部类型

    enum class ConnectFailure {
        NONE, EMPTY_IP, CONTROL_SOCKET_MISSING, CONTROL_CONNECT,
        CONTROL_INTERFACE_INIT, DIAGNOSTICS_SOCKET_MISSING,
        DIAGNOSTICS_CONNECT, DIAGNOSTICS_SUBSCRIBER_INIT,
        READINESS, FIRST_STATE_TIMEOUT, PROTOCOL_MISMATCH, EXCEPTION
    };

    enum class CleanupStep {
        STOP_DIAGNOSTICS, STOP_CONTROL, DISCONNECT_DIAGNOSTICS,
        DISCONNECT_CONTROL, RESET_DATA, VERIFY_RESIDUAL
    };

    struct CleanupStepResult {
        CleanupStep step;
        bool attempted;
        bool success;
        std::string detail;
    };

    struct CleanupReport {
        ConnectFailure primary_failure;
        std::vector<CleanupStepResult> steps;
        bool complete;
        bool control_connected_after;
        bool diagnostics_connected_after;
        bool control_receiving_after;
        bool diagnostics_receiving_after;
    };

当前 public bool API 不返回 CleanupReport。可选的非破坏性做法：
- 先以私有成员 last_connect_cleanup_report_ 保存报告，并提供只读诊断 getter；
- 或新增 ConnectResult connect_detailed(...)，由旧 bool overload 包装。
不能仅靠日志作为唯一证据；新增 getter 应说明线程安全、生命周期和报告被下一次 attempt 覆盖的规则。

## 7. Socket 与 Subscriber 契约必须先补齐

当前 Socket bool API 不保证 false 后状态。事务 guard 不能单靠调用方猜测实现内部状态，建议先冻结契约：

| API | 成功契约 | 失败契约（建议） | 幂等性 |
|---|---|---|---|
| connect | connected=true | 资源回到 disconnected/not receiving；若无法保证，调用方必须 disconnect best-effort 且保留 residual | 对 disconnected 重试安全 |
| start_receive_thread | receiving=true，callback 已受生命周期屏障保护 | 不留活动 callback/worker；部分启动也由 adapter 自行收回 | 重复 stop 可安全执行 |
| stop_receive_thread | receiving=false 且 active callback=0 | 即使返回 false，也必须完成取消/排空或给出可观测 residual；不能谎报 drained | 必须幂等 |
| disconnect | disconnected=true 且无 socket-owned receive worker | 返回 false 时给出仍存资源状态；不能留下不可查询的隐式资源 | 必须幂等 |

不要在 RobotDriver rollback 中盲目双重 stop。正常对象路径由 Subscriber 析构负责 stop；只有 Subscriber 构造失败、对象未形成路径才由 guard 直接 stop。要实现这一点，Subscriber factory 应返回显式初始化结果，并确保失败路径自行 stop/join 后才返回错误。

建议将构造改为两阶段：
- 构造只保存 socket 和依赖，不启动 callback；
- start() 显式返回 InitResult；
- 若 start 失败，内部执行 stop/join，再返回失败；
- 成功后析构负责 stop/join。
若为兼容性保留 throwing constructor，则必须在构造函数内部 catch start 失败并清理，再 rethrow。

## 8. 失败/异常矩阵与预期 rollback

| 注入点 | 必须执行的 rollback | 原始结果 | 额外断言 |
|---|---|---|---|
| 空 IP / 缺少 socket | 若本次未开始 socket attempt，不断开未触碰资源；旧会话策略独立 | false | 不误清理别的 session |
| C.connect 返回 false | C disconnect best-effort；D 未触碰 | false | C 残留状态写入 report |
| C.connect 抛异常 | C disconnect best-effort | 原异常传播 | cleanup 不覆盖异常 |
| CI Subscriber start 失败 | 失败 factory 内 stop/join；guard 再确保 C disconnect | 初始化失败结果/原异常 | 不存在未登记 callback |
| CI 后续 buffer 分配抛异常 | 已构造的基类 Subscriber 可能析构；guard 清理 C | bad_alloc 原异常传播 | 验证基类析构路径的 stop 屏障 |
| D.connect 返回 false/抛异常 | reset CI 并 drain C callback；D disconnect best-effort；C disconnect | false/原异常 | 两 socket 均记录 residual |
| DS Subscriber start 失败 | DS factory 内 stop/join；reset CI/drain C；stop D partial start；disconnect D、C | 初始化失败结果/原异常 | 不遗留 C callback |
| readiness 失败 | reset DS、CI；disconnect D、C | false | 清理两侧均尝试 |
| 首帧 timeout | 同上 | false | ManualClock/wait seam；不依赖 wall-clock sleep |
| protocol mismatch | 同上 | false | state snapshot 与 failure reason 固定 |
| 任一步 cleanup 返回 false | 后续 cleanup 仍继续 | 保留 primary failure | report.complete=false，保留每个失败步骤 |
| 任一步 cleanup 抛异常 | 捕获并继续剩余步骤 | 保留 primary failure/原异常 | cleanup 不抛出、不短路 |
| rollback 完成但仍 connected/receiving | 不可声称 cleanup 完成；可重复安全清理一次，之后记录 residual | false/原异常 | 高等级告警，禁止自动重连 |

## 9. 旧会话、并发和重入保护

- connect 入口不能只凭 control_socket_->is_connected() 判断是否有旧 session；还要检查两个 interface/subscriber 指针、两个 socket 的 receiving 状态和上次 cleanup report。
- 对不一致旧状态，先运行统一 cleanup；若 cleanup incomplete，拒绝开始新 session。
- connect 与 disconnect 必须串行化。最小方案是 connection_mutex_ 保护整个连接状态变更；但不能持锁等待 callback，而 callback 不得反向调用 connect/disconnect。若未来 callback 会回调 driver API，则改用状态机 + generation + 分阶段锁，不可在 callback drain 时持有 callback 需要的锁。
- 每个 session 分配递增 generation。callback 在提交数据前验证 generation，阻止旧 session 延迟 callback 覆盖新 session state。
- RobotDriver 析构策略必须单独决策：推荐析构执行 cleanup_connection_noexcept()，但需确保对象销毁前不再有外部线程调用 driver；析构清理失败只记录，不抛出。若产品选择要求显式 disconnect，则析构保持轻量但必须公开记录未 disconnect 的行为并有调用方生命周期测试。
- disconnect() 可复用同一内部 cleanup 实现，但需区分清理当前 session与 rollback 本次 attempt。

## 10. 实施顺序与门禁

| 顺序 | 最小增量 | 验收门禁 |
|---|---|---|
| P0 | 冻结 Socket false/partial-state、stop barrier、disconnect 幂等契约 | Socket contract review |
| P1 | Subscriber 两阶段初始化或 factory；构造失败内部清理 | SUB-INIT-01至06 |
| P2 | CleanupReport、每步 best-effort cleanup、residual snapshot | CLEAN-01至10 |
| P3 | ConnectRollbackGuard 与统一 fail/exception 路径 | RB-GUARD-01至12 |
| P4 | connect/disconnect 串行化与 session generation | CONC-01至08、TSan |
| P5 | ManualClock/wait strategy，首帧即成功退出或明确 deadline policy | WAIT-01至06 |
| P6 | destructor policy 和 integration fixture | LIFE-01至05 |
| P7 | 真实 UDP loopback、ROS 2 Control 集成、SIL/CS9/HIL/FAT/SAT 分层验证 | 每层独立签核 |

任何阶段若 cleanup residual 未清零，不得进入下一次 connect，不得将 driver 报告为 connected，也不得自动恢复运动。

## 11. 测试规格

### GUARD-01：C.connect 返回 false 后 residual cleanup
- Arrange：C.connect 返回 false 但 Fake 保持 connected=true；D 不应被触碰。
- Act：connect。
- Assert：返回 false；C.disconnect 至少一次；D.connect/disconnect 均为 0；CleanupReport 记录 primary failure 和最终 C residual。

### GUARD-02：Subscriber 初始化失败后无 callback 泄漏
- Arrange：C connect 成功；C start 接收注入“部分启动后失败”。
- Act：创建 CI。
- Assert：初始化失败返回/抛出前 callback 已撤销并 join；guard disconnect C；active callback=0。

### GUARD-03：D.connect 失败时先排空 C callback
- Arrange：C CI callback admission 成功并由 gate 阻塞；D.connect 返回 false。
- Act：connect 触发 rollback。
- Assert：C callback gate 释放并退出后才执行 C.disconnect；D.disconnect 也执行（若 D connect attempt 已开始）；没有 UAF。

### GUARD-04：异常优先级
- Arrange：D Subscriber 构造抛原始 runtime_error；C.disconnect 又注入抛异常。
- Act：connect。
- Assert：外部捕获到原始 runtime_error；cleanup exception 写入 report；D/C cleanup 均继续尝试；异常未被 cleanup error 覆盖。

### GUARD-05：每个清理步骤失败不短路
- Arrange：stop D=false、disconnect D=false、stop C=true、disconnect C=false。
- Act：rollback。
- Assert：所有后续步骤仍被尝试；report 中逐步保留 false；complete=false；connect 不成功。

### GUARD-06：构造后、成员赋值前异常
- Arrange：Subscriber 基类启动 callback 成功；Interface 派生类 buffer resize 抛 bad_alloc（通过可控 allocator/factory seam 模拟）。
- Act：创建 Interface。
- Assert：基类子对象析构完成 stop barrier；RobotDriver guard 仍 disconnect C；无 active callback。

### GUARD-07：旧 session 不一致状态
- Arrange：C/D sockets is_connected=false，但 C interface 指针仍存在或 D receiving=true。
- Act：再次 connect。
- Assert：旧状态统一 cleanup；cleanup incomplete 则拒绝新连接；不得覆盖旧 interface 指针或启动第二个 callback。

### GUARD-08：双通道 cleanup happens-before
- Arrange：C、D callback 分别 gate-block；共享 recorder。
- Act：rollback/disconnect。
- Assert：各通道自己的 callback drain happens-before 自己的 disconnect；两个通道均被尝试；不对本地事件序号做跨 Fake 比较。

### GUARD-09：幂等 rollback
- Arrange：第一次 rollback 的 D.disconnect 返回 false 但状态转为 disconnected；C 正常清理。
- Act：同一 attempt 重入 cleanup（仅在实现明确支持时）。
- Assert：不 double-free、不触发已销毁 callback；report 保留第一次失败和最终 residual；重复调用安全。

### GUARD-10：析构 fallback
- Arrange：模拟成功建立 session 后调用析构，不显式 disconnect。
- Act：销毁 driver。
- Assert：若采用推荐析构清理策略，所有 callback drain 后 socket disconnect；cleanup 不抛异常。若选择显式 disconnect 策略，则该行为必须作为明确产品决策并由测试锁定。

GUARD-01至GUARD-10 均为测试规格，当前全部 NOT_RUN。

## 12. 本轮状态与禁止推断

- 完成固定提交源码复核、事务状态模型、rollback guard 结构、清理顺序、错误/异常语义、Socket/Subscriber 契约和测试规格设计。
- 未修改 Stäubli 上游、ros2_control 上游或任何第三方依赖。
- 未创建/应用/合并 PR；未授权 TODO-EXT-001。
- 未实现 guard、CleanupReport、两阶段 Subscriber、FakeSocket、ManualClock、wait strategy、generation 或 mutex。
- 未运行 build、gtest、loopback、TSan/ASan、ROS 2 Control 集成、SIL/HIL、VAL3/CS9、FAT/SAT 或实机测试。
- GUARD-01至GUARD-10、P0至P7 全部 NOT_RUN / NOT_IMPLEMENTED。
- 工程级验收未通过；本报告不构成安全功能或机器人可运行性证明。

**下一节点建议 §9.3.291 / SERVO-874：将 CleanupReport 与 Socket/Subscriber 初始化契约细化为可执行接口定义及返回类型，重点审查 connect false/异常时底层资源状态可观测性、Subscriber 两阶段启动失败回收和 stop 幂等契约；仍只做设计，未经明确授权不修改上游。**
